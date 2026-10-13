"""Service release guards/export privacy; mock host mounts, real HTTP dispatch."""
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_demo_stability as DS
import serve_cloud as C
APP,R=DS.APP,DS.R

class ServicePrivacy(unittest.TestCase):
    setUpClass=classmethod(DS.service_setup)
    tearDownClass=classmethod(DS.service_teardown)
    request=DS.DemoStabilityTests.request

    def test_export_uses_only_authenticated_owner_ignoring_query(self):
        keys=[]
        for user in (0,1):
            status,result=self.request('/api/add_work',user=user,body={'title':'private-title-'+str(user),'date':'2020-01-01'})
            self.assertEqual(status,200)
            keys.append(result['work_key'])
            self.request('/api/note',user=user,body={'work_key':keys[-1],'note_impression':'private-note-'+str(user)})
            APP._write_setting_json(self.users[user][0],APP.DECLARED_KEY,{'person':['private-person-'+str(user)]})
        with patch.object(APP.RC,'load_declared',side_effect=AssertionError('shared declarations accessed')):
            status,data=self.request('/export.json?user_id='+self.users[1][0],user=0)
        self.assertEqual(status,200)
        payload=json.dumps(data,ensure_ascii=False)
        self.assertIn('private-note-0',payload)
        self.assertNotIn('private-note-1',payload)
        self.assertNotIn('private-person-1',payload)
        self.assertTrue(all(row['user_id']==self.users[0][0] for row in data['works']))
        # Verify actual allowed favourite kind to avoid depending on hardcoded name.
        kind=APP.RC.KINDS[0]
        APP._write_setting_json(self.users[0][0],APP.DECLARED_KEY,{kind:['own favourite']})
        self.assertEqual(APP.export_payload(self.users[0][0])['declared'][kind],['own favourite'])

    def test_export_without_cookie_and_zip_always_denied(self):
        for cookie in ('','tg_session=invalid'):
            self.assertEqual(self.request('/export.json',extra={'Cookie':cookie})[0],403)
        self.assertEqual(self.request('/data.zip')[0],403)
        self.assertEqual(self.request('/data.zip',extra={'Cookie':''})[0],403)

    def test_unscoped_shared_table_excluded(self):
        with R.connect() as con:
            con.execute('DROP TABLE IF EXISTS presented')
            con.execute('CREATE TABLE presented(private_value TEXT)')
            con.execute("INSERT INTO presented VALUES('PRIVATE-SHARED')")
        try:
            payload=APP.export_payload(self.users[0][0])
            self.assertEqual(payload['presented'],[])
            self.assertNotIn('PRIVATE-SHARED',json.dumps(payload))
        finally:
            with R.connect() as con:con.execute('DROP TABLE presented')

    def test_settings_card_counts_are_personal(self):
        uid=self.users[0][0]
        data=APP.export_payload(uid)
        with patch.object(APP,'export_payload',return_value=data) as export:
            card=APP._export_card_html(uid)
        export.assert_called_once_with(uid)
        self.assertNotIn('private-note-1',card)
        self.assertNotIn('/data.zip',card)

    def test_public_same_origin_cookie_secure(self):
        import serve
        handler=object.__new__(serve.Handler)
        handler.server=self.srv
        old=self.srv.cors_origin
        self.srv.cors_origin=''
        try:
            cookie=handler._set_session_cookie('test-secret')
        finally:self.srv.cors_origin=old
        self.assertIn('Secure',str(cookie))
        self.assertIn('HttpOnly',str(cookie))

    def test_health_reports_export_boundary(self):
        status,data=self.request('/api/health')
        self.assertEqual(status,200)
        self.assertEqual(data['export_scope'],'authenticated-user')
        self.assertFalse(data['public_zip'])

class ServiceMount(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{'TAGURI_STATE_DIR':'/var/data/taguri','TAGURI_STATE_MOUNT':'/var/data','TAGURI_EXPOSURE_DB':'/var/data/taguri/recommendation_exposure.db','RENDER':'true','RENDER_SERVICE_ID':'','TAGURI_ALLOW_LOCAL_SERVICE':''})
        self.env.start();self.addCleanup(self.env.stop)
        self.info=patch.object(Path,'read_text',return_value='')
        self.info.start();self.addCleanup(self.info.stop)

    def test_mount_absent_and_container_root_rejected(self):
        with patch('os.path.ismount',return_value=False),self.assertRaises(RuntimeError):C.check_service_storage('service')
        with patch.dict(os.environ,{'TAGURI_STATE_MOUNT':'/'}),patch('os.path.ismount',return_value=True),self.assertRaises(RuntimeError):C.check_service_storage('service')

    def test_actual_mount_and_bindmount_metadata_accepted(self):
        with patch('os.path.ismount',return_value=True):C.check_service_storage('service')
        with patch('os.path.ismount',return_value=False),patch.object(Path,'read_text',return_value='1 2 3:4 / /var/data rw - ext4 /dev/device rw'):
            C.check_service_storage('service')

    def test_tmpfs_mountinfo_and_state_outside_mount_rejected(self):
        with patch('os.path.ismount',return_value=True),patch.object(Path,'read_text',return_value='1 2 3:4 / /var/data rw - tmpfs tmpfs rw'),self.assertRaises(RuntimeError):C.check_service_storage('service')
        with patch.dict(os.environ,{'TAGURI_STATE_DIR':'/tmp/state','TAGURI_EXPOSURE_DB':'/tmp/state/exposure.db'}),patch('os.path.ismount',return_value=True),self.assertRaises(RuntimeError):C.check_service_storage('service')

    def test_exposure_outside_state_rejected(self):
        with patch.dict(os.environ,{'TAGURI_EXPOSURE_DB':'/tmp/exposure.db'}),patch('os.path.ismount',return_value=True),self.assertRaises(RuntimeError):C.check_service_storage('service')

    def test_local_explicit_override_required_and_demo_unaffected(self):
        with patch.dict(os.environ,{'RENDER':'','RENDER_SERVICE_ID':''}):
            with self.assertRaises(RuntimeError):C.check_service_storage('service')
            with patch.dict(os.environ,{'TAGURI_ALLOW_LOCAL_SERVICE':'1'}):C.check_service_storage('service')
        with patch.dict(os.environ,{'TAGURI_STATE_DIR':''}):C.check_service_storage('demo')

if __name__=='__main__':unittest.main()
