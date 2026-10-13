"""Gated original-UI Python Workers migration preview; no Render requests."""
from html import escape
import io
import json
import re
import time
from urllib.parse import urlsplit
import zipfile
from workers import Response, WorkerEntrypoint, DurableObject
from legacy_runtime import execute, serve, SCREENS, POSTS
from snapshot_store import ConcurrentWrite, load, save
from cloud_auth import AuthError, handle_auth, resolve_account, read_input

AUTH_GET = {'/auth/start','/recover','/link'}
AUTH_POST = {'/api/recover','/api/logout','/api/link/create','/api/link/redeem','/api/delete_account'}
GET_API = {'/api/suggest','/api/suggest_web','/api/mail_hints','/api/import_status','/export.json','/data.zip'}


def response(value, status=200, headers=None):
    return Response(json.dumps(value,ensure_ascii=False),status=status,headers={'Content-Type':'application/json','Cache-Control':'no-store','X-Content-Type-Options':'nosniff',**(headers or {})})


def auth_html(body, status=200, headers=None):
    return Response(serve.Handler._auth_page(None,body).decode('utf-8'),status=status,headers={'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff',**(headers or {})})


def metadata(body, welcome=None):
    value=json.loads(body)
    value['persistent_mode']=True
    if welcome:
        value['welcome_code']=welcome
    return value


def archive(account,tables):
    # Account snapshot, not the entire old data directory. Tokens/auth DB and
    # other accounts can never be included. Same payload as /export.json.
    payload=json.dumps({'format':'taguri-legacy-account','version':1,'user_id':account,'tables':tables},ensure_ascii=False,indent=2).encode()
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_STORED) as file:
        file.writestr('taguri-export.json',payload)
    return output.getvalue()


class OriginalRenderer(DurableObject):
    async def fetch(self,request):
        started=time.monotonic()
        route='unknown'
        status=503
        try:
            url=urlsplit(request.url)
            path=url.path
            if path.startswith('/api/screen/'):
                route='screen'
            elif path in AUTH_GET:
                route='auth_page'
            elif path in AUTH_POST:
                route=path[5:]
            elif path in {'/export.json','/data.zip'}:
                route='export'
            elif path.startswith('/api/') and path[5:] in POSTS:
                route=path[5:]
            else:
                route='static'
            result=await self.dispatch(request,url)
            status=result.status
            return result
        except AuthError as error:
            status=error.status
            if (request.headers.get('Content-Type') or '').startswith('application/x-www-form-urlencoded'):
                return auth_html('<p class=warn>'+escape(error.message)+'</p><p><a href="/recover">戻る</a></p>',error.status)
            return response({'ok':False,'error':error.message},error.status)
        except ConcurrentWrite:
            status=409
            return response({'ok':False,'error':'別の操作で変更されました。画面を読み直してください。'},409)
        except Exception:
            status=503
            # No original traceback/message escapes into response or platform log.
            return response({'ok':False,'error':'処理できませんでした。保存済み記録は保持されています。'},503)
        finally:
            if route!='static' or status>=500:
                print(json.dumps({'event':'taguri.operation','route':route,'method':request.method if request.method in {'GET','POST','HEAD'} else 'OTHER','status':status,'duration_ms':round((time.monotonic()-started)*1000),'backend':'d1'},separators=(',',':')))

    async def dispatch(self,request,url):
        path=url.path
        if path.startswith('/migration-api/'):
            return response({'ok':False,'error':'記録の保存先を統合しました。元の画面を開いて操作してください。','next':'/'},409)
        if path=='/migration-data' or path.startswith('/migration-data/'):
            return Response('',status=302,headers={'Location':'/','Cache-Control':'no-store'})
        origin=f'{url.scheme}://{url.netloc}'
        if path.startswith('/img/'):
            if request.method!='GET':
                return response({'ok':False,'error':'GETが必要です。'},405)
            name=path[5:]
            if not re.fullmatch(r'[A-Za-z0-9_-]+\.(?:png|jpg|jpeg|webp)',name,re.I):
                return response({'ok':False,'error':'画像が見つかりませんでした。'},404)
            try:
                from public_snapshot import POSTER_NAMES
            except ImportError:
                POSTER_NAMES=()
            if name not in POSTER_NAMES:
                return response({'ok':False,'error':'画像が見つかりませんでした。'},404)
            return await self.env.ASSETS.fetch(request)
        protected=path.startswith('/api/') or path in AUTH_GET or path in {'/export.json','/data.zip'}
        if not protected:
            if request.method not in {'GET','HEAD'}:
                return response({'ok':False,'error':'対応していない操作です。'},405)
            return await self.env.ASSETS.fetch(request)
        if request.method not in {'GET','POST'}:
            return response({'ok':False,'error':'対応していない操作です。'},405)
        if request.method=='POST' and request.headers.get('Origin')!=origin:
            return response({'ok':False,'error':'同じサイトから操作してください。'},403)
        if getattr(self.env,'MIGRATION_READY','false')!='true' or not serve.RR.SRC.exists():
            return response({'ok':False,'error':'完全移行の検証中です。保存済みの記録は保持されています。'},503)
        auth=await handle_auth(request,self.env)
        if auth is not None:
            status,value,headers=auth
            if (request.headers.get('Content-Type') or '').startswith('application/x-www-form-urlencoded'):
                return auth_html('<h1>'+('戻れました' if path=='/api/recover' else '追加できました')+'</h1><p><a href="/auth/start">続ける</a></p>',status,headers)
            return response(value,status,headers)
        if path=='/recover':
            return auth_html("<h1>復旧コードで戻る</h1><form method=post action=/api/recover><input name=code placeholder='xxxx-xxxx-...' style='width:100%;font-size:1.1em;padding:.5em'><button type=submit style='margin-top:1em'>戻る</button></form>")
        if path=='/link':
            return auth_html("<h1>この端末を追加</h1><p>すでに使っている端末で発行した連携コードを入力してください。</p><form method=post action=/api/link/redeem><input name=code placeholder='6桁のコード' style='width:100%;font-size:1.1em;padding:.5em'><button type=submit style='margin-top:1em'>追加</button></form>")
        allowed_get=path in GET_API or path=='/auth/start' or path.startswith('/api/screen/') and path.rsplit('/',1)[-1] in SCREENS
        allowed_post=path.startswith('/api/') and path[5:] in POSTS
        if not ((request.method=='GET' and allowed_get) or (request.method=='POST' and allowed_post)):
            return response({'ok':False,'error':'見つかりませんでした。'},404)
        account=await resolve_account(request,self.env)
        uid=account['user_id']
        extra={'Set-Cookie':account['set_cookie']} if account.get('set_cookie') else {}
        if path=='/auth/start':
            code=account.get('welcome_code')
            if code:
                body='<h1 class=warn>この復旧コードは今だけ表示されます</h1><p>端末を失ったとき、これが無いと記録には二度と戻れません。安全な場所に控えてください。</p><code>'+escape(code)+'</code><p>控えたら、このページを閉じて構いません。</p><hr><h2>まず、好きな劇団・俳優を登録してみませんか</h2><p><a href="/recommend/favourites">好きな劇団・俳優を登録する</a></p>'
            else:
                body='<h1>この端末は認識されています</h1><p>利用者ID: <code>'+escape(uid[:12])+'…</code></p><p><a href="/link">この端末を追加（別の端末で使う）</a></p>'
            return auth_html(body,headers=extra)
        revision,tables=await load(self.env.DB,uid)
        if path=='/data.zip':
            return Response(archive(uid,tables),status=200,headers={'Content-Type':'application/zip','Content-Disposition':'attachment; filename="taguri-data.zip"','Cache-Control':'no-store',**extra})
        payload=b''
        if request.method=='POST':
            payload=json.dumps(await read_input(request),ensure_ascii=False).encode()
            if len(payload)>8192:
                return response({'ok':False,'error':'入力が長すぎます。'},413,extra)
        status,body,headers,updated=execute(uid,tables,path+('?' + url.query if url.query else ''),request.method,payload,origin)
        if status<400 and updated!=tables:
            await save(self.env.DB,uid,revision,updated,tables)
        headers.update(extra)
        if headers.get('Content-Type','').startswith('application/json') and path!='/export.json':
            value=metadata(body,account.get('welcome_code'))
            if path=='/api/screen/settings' and status==200:
                value['body_html'] += '<details class="card"><h2>アカウントの削除</h2><p class="lead">このアカウントの記録と復旧コードを削除します。削除後は元に戻せません。</p><div class="account-delete"><button type="button" data-account-delete>アカウントを削除する</button><span class="said" role="status"></span></div></details>'
            return response(value,status,headers)
        return Response(body.decode('utf-8'),status=status,headers=headers)


class Default(WorkerEntrypoint):
    async def fetch(self,request):
        try:
            path=urlsplit(request.url).path
            compute=(path.startswith(('/api/','/auth/','/img/','/migration-api/','/migration-data/')) or path in {'/recover','/link','/export.json','/data.zip','/migration-data'})
            if not compute:
                if request.method not in {'GET','HEAD'}:
                    return response({'ok':False,'error':'対応していない操作です。'},405)
                return await self.env.ASSETS.fetch(request)
            # SQLite-backed DO class is available on Workers Free. The DO stores
            # no private DB: all account persistence remains in D1. Keeping the
            # original renderer here uses the DO's default 30-second CPU budget
            # instead of increasing paid Worker limits or rewriting the design.
            renderer=self.env.ORIGINAL_RENDERER.getByName('original-renderer-v1')
            return await renderer.fetch(request)
        except Exception:
            print('{"event":"taguri.operation","route":"dispatch","status":503,"backend":"durable-object"}')
            return response({'ok':False,'error':'処理できませんでした。保存済み記録は保持されています。'},503)
