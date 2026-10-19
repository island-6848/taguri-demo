import {createServer} from 'node:http';
import {readFileSync,existsSync,mkdirSync,writeFileSync} from 'node:fs';
import {resolve,extname} from 'node:path';
import assert from 'node:assert/strict';
import {chromium} from 'playwright';
import {PNG} from 'pngjs';
import pixelmatch from 'pixelmatch';
import {checkRegisterDialog} from './register-dialog-browser.js';
import {checkCompareLayout} from './compare-layout-browser.js';
const repo=resolve('..'), fixtures=JSON.parse(readFileSync('/tmp/taguri-visual-fixtures.json','utf8'));
const server=createServer((req,res)=>{
 const url=new URL(req.url,'http://localhost'),original=url.pathname.startsWith('/taguri-demo/');
 const root=resolve(repo,original?'web':'cloudflare/public');
 const name=original?url.pathname.slice('/taguri-demo/'.length):url.pathname.slice(1);
 let file=resolve(root,name||'index.html');
 if(!file.startsWith(root+'/')||!existsSync(file)||!extname(file))file=resolve(root,'index.html');
 try{const types={'.css':'text/css','.js':'text/javascript','.html':'text/html','.mp4':'video/mp4'};res.setHeader('Content-Type',types[extname(file)]||'application/octet-stream');if(!original)res.setHeader('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'");res.end(readFileSync(file));}catch{res.writeHead(404);res.end();}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const base=`http://127.0.0.1:${server.address().port}`;
const browser=await chromium.launch();mkdirSync('/tmp/taguri-visual',{recursive:true});
const paths={rate:'/rate',unrated:'/rate/unrated',register:'/register',notes:'/rate/notes',works:'/records/works',settings:'/settings'};
try {
 for(const width of [1280,390])for(const [name,path] of Object.entries(paths)) {
  const images=[];
  for(const original of [true,false]) {
   const page=await browser.newPage({viewport:{width,height:900},deviceScaleFactor:1,reducedMotion:'reduce'});
   const errors=[];page.on('pageerror',error=>errors.push(error.message));
   await page.route('**/*',async route=>{
    const url=new URL(route.request().url());
    if(url.pathname.startsWith('/api/screen/')){const screen=url.pathname.split('/').at(-1);return route.fulfill({status:200,contentType:'application/json',headers:{'Access-Control-Allow-Origin':base,'Access-Control-Allow-Credentials':'true'},body:JSON.stringify(fixtures[screen]??fixtures.register)});}
    // Production's config.js says "service" since the 2026-10-14 switch (dec-native-cutover-now): its words
    // ("公演一覧から探す") and the アカウント entry differ from the demo on purpose. Compare the shared shell,
    // CSS and controls under the same edition; the service-only parts are covered by test/cutover.test.js.
    if(!original&&url.pathname==='/config.js')return route.fulfill({status:200,contentType:'text/javascript',body:'window.TAGURI={edition:"demo",api:location.origin,base:"",demoBase:""};'});
    if(url.origin===base)return route.continue();
    return route.abort();
   });
   await page.goto(base+(original?'/taguri-demo':'')+path);await page.waitForFunction(()=>document.querySelector('#content h1'));
   await page.locator('.tg-loading').waitFor({state:'detached'});await page.evaluate(()=>document.fonts.ready);
   await page.screenshot({path:`/tmp/taguri-visual/${name}-${width}-${original?'original':'restored'}.png`,fullPage:true,animations:'disabled'}).then(buffer=>images.push(PNG.sync.read(buffer)));
   assert.deepEqual(errors,[],`${name}/${width}: JavaScript errors`);
   assert.equal(await page.locator('.side .navrow').count(),1);
   assert.ok(await page.locator('#content').innerText());
   await page.close();
  }
  const [a,b]=images;assert.equal(a.width,b.width);assert.equal(a.height,b.height);
  const diff=new PNG({width:a.width,height:a.height});const count=pixelmatch(a.data,b.data,diff.data,a.width,a.height,{threshold:0.1});
  writeFileSync(`/tmp/taguri-visual/${name}-${width}-diff.png`,PNG.sync.write(diff));
  assert.ok(count/(a.width*a.height)<=0.001,`${name}/${width}: ${count} differing pixels`);
  console.log(`${name}/${width}: ${count} differing pixels; original CSS, shell and controls preserved.`);
 }
 await checkRegisterDialog(browser,base);
 await checkCompareLayout(browser,base);
} finally {await browser.close();await new Promise(resolve=>server.close(resolve));}

