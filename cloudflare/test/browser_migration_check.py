"""CPython original-handler browser test; not Python Workers runtime proof."""
import asyncio,json,sys,threading,time
from http.server import HTTPServer,BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
sys.path.insert(0,str(Path(__file__).parent))
from test_renderer_migration import runtime,database,native_provision
ROOT=Path(__file__).resolve().parents[1]/'public'
async def setup():
 d=database();d.con.execute("INSERT INTO users VALUES('browser-A','aaaa',0)");return await native_provision.build_snapshot(d,'browser-A')
tables=asyncio.run(setup());events=[]
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_GET(self):
  global tables
  path=urlsplit(self.path).path
  if path.startswith('/api/'):
   started=time.perf_counter();status,body,headers,tables=runtime.execute('browser-A',tables,self.path);events.append({'path':path,'status':status,'ms':round((time.perf_counter()-started)*1000)})
   if status==200 and headers['Content-Type'].startswith('application/json'):
    value=json.loads(body);value['persistent_mode']=True;body=json.dumps(value).encode()
  else:
   file=ROOT/path.lstrip('/');file=file if file.is_file() else ROOT/'index.html';status=200;body=file.read_bytes();headers={'Content-Type':{'.js':'application/javascript','.css':'text/css','.html':'text/html'}.get(file.suffix,'application/octet-stream')}
  self.send_response(status)
  for k,v in headers.items():self.send_header(k,v)
  self.end_headers();self.wfile.write(body)
server=HTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base='http://127.0.0.1:'+str(server.server_port)
paths={'recommend':'/recommend','start':'/start','reminder':'/recommend/reminder','interest':'/recommend/interest','favourites':'/recommend/favourites','calendar':'/calendar','tickets':'/tickets','rate':'/rate','unrated':'/rate/unrated','notes':'/rate/notes','register':'/register','records':'/records','trace':'/records/trace','chronicle':'/records/chronicle','works':'/records/works','search':'/search','settings':'/settings'}
out=Path('/tmp/taguri-independent/browser');out.mkdir(parents=True,exist_ok=True);failures=[]
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  for width in [1280,390]:
   for name,path in paths.items():
    page=browser.new_page(viewport={'width':width,'height':900},reduced_motion='reduce');errors=[];outside=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    def intercept(route):
     if route.request.url.startswith(base):route.continue_()
     else:outside.append(route.request.url);route.abort()
    page.route('**/*',intercept)
    try:
     page.goto(base+path);page.wait_for_function("document.querySelector('#content h1')",timeout=10000);page.locator('.tg-loading').wait_for(state='detached',timeout=10000)
     assert not errors,errors
     assert page.locator('#content').inner_text().strip()
     assert not outside,outside
     relevant=[e for e in events if e['path']=='/api/screen/'+name];assert relevant and relevant[-1]['status']==200,relevant
     page.screenshot(path=str(out/f'{name}-{width}.png'),full_page=True)
    except Exception as e:failures.append({'name':name,'width':width,'error':str(e)[:400]})
    page.close()
  browser.close()
finally:server.shutdown()
(out/'result.json').write_text(json.dumps({'events':events,'failures':failures},ensure_ascii=False,indent=2));print(json.dumps({'views':34,'failures':failures},ensure_ascii=False));sys.exit(bool(failures))
