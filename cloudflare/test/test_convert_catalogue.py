import importlib.util
import json
import unittest
from pathlib import Path

SCRIPT=Path(__file__).resolve().parents[1]/'scripts'/'convert_catalogue.py'
spec=importlib.util.spec_from_file_location('convert_catalogue',SCRIPT)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CatalogueTest(unittest.TestCase):
    def test_dates_and_public_fields_without_owner_reasons(self):
        row=module.public_candidate({'stage_id':'1','title':'舞台','period':'2026/11/1〜2026/11/9', 'group':'劇団','fields':{'出演':'俳優'}, 'why_b':['private'],'_notes':'private','a':['owner'], 'url':'javascript:alert(1)'})
        self.assertEqual(row[2],'2026-11-01')
        self.assertEqual(row[4],'')
        data=json.loads(row[5])
        self.assertEqual(data['end_date'],'2026-11-09')
        self.assertNotIn('why_b',data)
        self.assertNotIn('_notes',data)
        self.assertNotIn('a',data)

    def test_missing_and_impossible_dates_fail(self):
        for value in [{'stage_id':'1','title':'舞台'},{'stage_id':'1','title':'舞台','date':'2026-02-30'}]:
            with self.assertRaises(ValueError):
                module.public_candidate(value)


if __name__=='__main__':
    unittest.main()
