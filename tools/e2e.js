// Real-browser end-to-end check (system Edge via playwright-core): desktop keyboard, phone touch (portrait + landscape), layout, CSP, draw cost.
// usage: node e2e.js <url>
const {chromium,devices}=require('C:/Users/plati/null-signal/node_modules/playwright-core');
const URL=process.argv[2],OUT=require('os').tmpdir().replace(/\\/g,'/')+'/plumhop_';
const results=[];const ok=(name,pass,info)=>{results.push({name,pass:!!pass,info});console.log((pass?'PASS ':'FAIL ')+name+(info!==undefined?'  ['+info+']':''));};
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function open(browser,opts){
 const ctx=await browser.newContext(opts);const page=await ctx.newPage();const errs=[];
 page.on('console',m=>{if(m.type()==='error')errs.push('console: '+m.text());});page.on('pageerror',e=>errs.push('pageerror: '+e.message));
 await page.addInitScript(()=>{window.__csp=[];document.addEventListener('securitypolicyviolation',e=>window.__csp.push(e.violatedDirective+' -> '+e.blockedURI));});
 await page.goto(URL);await sleep(700);return {ctx,page,errs};
}
const toPage=async(page,lx,ly)=>{const r=await page.evaluate(()=>{const b=document.getElementById('cv').getBoundingClientRect();return{x:b.left,y:b.top,w:b.width,h:b.height};});return{x:r.x+lx*r.w/320,y:r.y+ly*r.h/240};};
const layout=page=>page.evaluate(()=>{const q=id=>{const b=document.getElementById(id).getBoundingClientRect();return{l:Math.round(b.left),t:Math.round(b.top),r:Math.round(b.right),b:Math.round(b.bottom)};};return{iw:innerWidth,ih:innerHeight,sw:document.documentElement.scrollWidth,cv:q('cv'),bl:q('bl'),br:q('br'),bj:q('bj'),coarse:matchMedia('(pointer:coarse)').matches,dpr:devicePixelRatio,cw:document.getElementById('cv').width};});
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 /* ---------- desktop: keyboard ---------- */
 {const {ctx,page,errs}=await open(browser,{viewport:{width:1280,height:800}});
  ok('desktop: title screen up',await page.evaluate(()=>state)==='title');
  await page.keyboard.press('Enter');await sleep(300);
  ok('desktop: Enter starts level 1',await page.evaluate(()=>state==='play'&&L.d.n)==='First Hops');
  const x0=await page.evaluate(()=>ball.x);
  await page.keyboard.down('ArrowRight');await sleep(1200);
  await page.keyboard.down('Space');await sleep(1500);
  const mid=await page.evaluate(()=>({x:ball.x,land:landY,minY:ball.y,sy:scrollY,inp:{...inp}}));
  await page.keyboard.up('Space');await page.keyboard.up('ArrowRight');
  ok('desktop: right arrow moves the ball',mid.x-x0>120,Math.round(mid.x-x0)+'px');
  ok('desktop: arrows/space do not scroll the page',mid.sy===0,'scrollY '+mid.sy);
  // high bounce: sample the peak height for a while with jump held
  await sleep(1200);const y0=await page.evaluate(()=>ball.y);await page.keyboard.down('Space');const peak=await page.evaluate(y0=>new Promise(res=>{let m=1e9,n=0;const f=()=>{m=Math.min(m,ball.y);if(++n<150)requestAnimationFrame(f);else res(Math.round(y0-m));};f();}),y0);await page.keyboard.up('Space');
  ok('desktop: held jump gives the big jump (~125px)',peak>105&&peak<140,peak+'px');
  await sleep(1200);const small=await page.evaluate(()=>new Promise(res=>{let m=1e9,M=-1e9,n=0;const f=()=>{m=Math.min(m,ball.y);M=Math.max(M,ball.y);if(++n<120)requestAnimationFrame(f);else res(Math.round(M-m));};f();}));
  ok('desktop: with no input the ball rests on the ground (no auto-bounce)',small<=2,small+'px');
  await page.keyboard.press('KeyP');await sleep(150);ok('desktop: P pauses',await page.evaluate(()=>state)==='pause');
  await page.keyboard.press('Escape');await sleep(150);ok('desktop: Esc resumes',await page.evaluate(()=>state)==='play');
  // save sanitising: hostile localStorage content must not break the game or reach the save object
  await page.evaluate(()=>{go('title');try{localStorage.setItem('plumhop_v1',JSON.stringify({mute:'yes',lv:{'0-0':{s:99,g:'<img src=x onerror=alert(1)>',t:-5},'__proto__':{s:3},'9-9x':{s:3},'1-1':'x'}}));}catch(e){}});
  await page.reload();await sleep(600);
  const sv=await page.evaluate(()=>({save,st:state,polluted:({}).s}));
  ok('security: hostile save data is sanitised',sv.st==='title'&&sv.save.mute===false&&sv.save.cur===null&&JSON.stringify(sv.save.lv)==='{"0-0":{"s":3,"g":0,"t":0}}'&&sv.polluted===undefined,JSON.stringify(sv.save));
  await page.evaluate(()=>{try{localStorage.removeItem('plumhop_v1');}catch(e){}});
  const csp=await page.evaluate(()=>window.__csp);
  ok('security: no CSP violations on desktop',csp.length===0,csp.join(' | '));
  const real=errs.filter(e=>!/fonts\.(googleapis|gstatic)|ERR_INTERNET|ERR_NAME|net::/i.test(e));
  ok('desktop: no script errors',real.length===0,real.join(' | ')||('ignored network msgs: '+(errs.length-real.length)));
  // every level builds and draws in a real canvas without throwing
  const drawAll=await page.evaluate(()=>{const bad=[];WORLDS.forEach((w,wi)=>w.levels.forEach((d,li)=>{try{startLevel(wi,li);for(let x=20;x<L.w;x+=150){ball.x=x;ball.y=Math.min(L.gy(x),L.h)-30;landY=ball.y;camUp(0,true);draw();}if(L.gems.length!==30)bad.push(d.n+' gems '+L.gems.length);}catch(e){bad.push(d.n+': '+e.message);}}));go('title');return bad;});
  ok('desktop: all 20 levels build + draw across their full width',drawAll.length===0,drawAll.join(' | '));
  await ctx.close();}
 /* ---------- phones ---------- */
 const phones=[['iPhone 13 portrait',{...devices['iPhone 13']}],['small phone 320x568',{viewport:{width:320,height:568},deviceScaleFactor:2,isMobile:true,hasTouch:true,userAgent:devices['iPhone 13'].userAgent}],['Android 360x740',{...devices['Pixel 5'],viewport:{width:360,height:740}}],['iPhone 13 landscape',{...devices['iPhone 13 landscape']}]];
 for(const [name,opts] of phones){
  const {ctx,page,errs}=await open(browser,opts);const land=/landscape/.test(name);
  const lay=await layout(page);
  ok(name+': touch device detected',lay.coarse,'dpr '+lay.dpr+', canvas '+lay.cw+'px');
  ok(name+': no horizontal overflow',lay.sw<=lay.iw,lay.sw+' <= '+lay.iw);
  ok(name+': canvas inside the screen',lay.cv.l>=0&&lay.cv.r<=lay.iw&&lay.cv.t>=0&&lay.cv.b<=lay.ih,JSON.stringify(lay.cv)+' in '+lay.iw+'x'+lay.ih);
  ok(name+': all three buttons on the first screen',[lay.bl,lay.br,lay.bj].every(b=>b.l>=0&&b.r<=lay.iw&&b.b<=lay.ih&&b.t>=0),JSON.stringify([lay.bl,lay.br,lay.bj]));
  const over=(a,b)=>a.l<b.r&&b.l<a.r&&a.t<b.b&&b.t<a.b;
  ok(name+': buttons do not cover the canvas',![lay.bl,lay.br,lay.bj].some(b=>over(b,lay.cv)));
  ok(name+': buttons are thumb sized (>=60px)',[lay.bl,lay.br,lay.bj].every(b=>b.r-b.l>=60&&b.b-b.t>=60),[lay.bl,lay.br,lay.bj].map(b=>(b.r-b.l)+'x'+(b.b-b.t)).join(' '));
  await page.screenshot({path:OUT+'e2e_'+name.replace(/\W+/g,'_')+'_title.png'});
  // tap "Play" on the canvas, then real multi-touch: hold RIGHT, add JUMP
  const cdp=await ctx.newCDPSession(page);const play=await toPage(page,160,140);
  await page.touchscreen.tap(play.x,play.y);await sleep(300);
  ok(name+': tapping Play starts the game',await page.evaluate(()=>state)==='play');
  const c=b=>({x:(b.l+b.r)/2,y:(b.t+b.b)/2}),R_=c(lay.br),J_=c(lay.bj),x0=await page.evaluate(()=>ball.x);
  await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:R_.x,y:R_.y,id:1}]});await sleep(500);
  await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:R_.x,y:R_.y,id:1},{x:J_.x,y:J_.y,id:2}]});await sleep(150);
  const held=await page.evaluate(()=>({...inp}));
  const peak=await page.evaluate(()=>new Promise(res=>{let m=1e9,n=0;const f=()=>{m=Math.min(m,ball.y);if(++n<110)requestAnimationFrame(f);else res(Math.round(landY-m));};f();}));
  await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[{x:R_.x,y:R_.y,id:1}]});await sleep(80);
  const afterJ=await page.evaluate(()=>({...inp}));
  await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});await sleep(80);
  const rel=await page.evaluate(()=>({...inp,x:ball.x,sy:scrollY}));
  ok(name+': two fingers at once (right + jump)',held.r===1&&held.j===1&&held.l===0,JSON.stringify(held));
  ok(name+': lifting one finger keeps the other',afterJ.r+afterJ.j===1,JSON.stringify(afterJ));
  ok(name+': releasing stops input, ball travelled',rel.r===0&&rel.j===0&&rel.x-x0>100,Math.round(rel.x-x0)+'px');
  ok(name+': big jump from touch jump',peak>100,peak+'px');
  // pause circle on the canvas
  const pz=await toPage(page,305,14);await page.touchscreen.tap(pz.x,pz.y);await sleep(200);
  ok(name+': pause button on canvas',await page.evaluate(()=>state)==='pause');
  await page.evaluate(()=>{startLevel(3,0);ball.x=500;ball.y=160;landY=160;camUp(0,true);});await sleep(400);
  await page.screenshot({path:OUT+'e2e_'+name.replace(/\W+/g,'_')+'_play.png'});
  const csp=await page.evaluate(()=>window.__csp);ok(name+': no CSP violations',csp.length===0,csp.join(' | '));
  const real=errs.filter(e=>!/fonts\.(googleapis|gstatic)|ERR_INTERNET|ERR_NAME|net::/i.test(e));ok(name+': no script errors',real.length===0,real.join(' | '));
  if(name==='iPhone 13 portrait'){
   // draw cost at phone resolution with the CPU slowed 4x (headless = software canvas, so this is a pessimistic bound)
   await cdp.send('Emulation.setCPUThrottlingRate',{rate:4});
   const cost=await page.evaluate(()=>{const out={};[[0,3,700],[1,1,900],[2,2,1250],[3,4,1500]].forEach(([wi,li,x])=>{startLevel(wi,li);ball.x=x;ball.y=L.gy(x)>1e8?100:L.gy(x)-30;landY=ball.y;camUp(0,true);let t=performance.now();for(let i=0;i<120;i++){gt+=1/60;draw();}const dr=(performance.now()-t)/120;t=performance.now();for(let i=0;i<2400;i++){step();if(state!=='play')break;}out[WORLDS[wi].name]={drawMs:+dr.toFixed(2),stepMsPerFrame:+((performance.now()-t)/1200).toFixed(3)};});go('title');return out;});
   await cdp.send('Emulation.setCPUThrottlingRate',{rate:1});
   const worst=Math.max(...Object.values(cost).map(v=>v.drawMs+v.stepMsPerFrame));
   ok('perf: frame work at 4x CPU slowdown fits 16.6ms',worst<16.6,JSON.stringify(cost));
  }
  await ctx.close();
 }
 await browser.close();
 const bad=results.filter(r=>!r.pass);console.log('\n'+(bad.length?('FAILED: '+bad.length+' of '+results.length):('ALL '+results.length+' CHECKS PASS')));process.exit(bad.length?1:0);
})().catch(e=>{console.log('E2E CRASH',e);process.exit(2);});
