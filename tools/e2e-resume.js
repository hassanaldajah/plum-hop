// Real-browser check that in-level progress survives closing the page. usage: node tools/e2e-resume.js <url>
const {chromium,devices}=require('C:/Users/plati/null-signal/node_modules/playwright-core');
const sleep=ms=>new Promise(r=>setTimeout(r,ms));let bad=0;const ok=(n,p,i)=>{if(!p)bad++;console.log((p?'PASS ':'FAIL ')+n+(i!==undefined?'  ['+i+']':''));};
(async()=>{
 const b=await chromium.launch({channel:'msedge',headless:true});const ctx=await b.newContext({...devices['iPhone 13']});const page=await ctx.newPage();const errs=[];page.on('pageerror',e=>errs.push(e.message));
 await page.goto(process.argv[2]);await sleep(500);
 await page.evaluate(()=>{try{localStorage.removeItem('plumhop_v1');}catch(e){}});await page.reload();await sleep(500);
 ok('fresh visit shows Play',await page.evaluate(()=>btns[0].l())==='Play');
 // play level 1-1 with real physics: hold right + jump until a checkpoint is reached
 const st=await page.evaluate(()=>{startLevel(0,0,true);inp.r=1;inp.j=1;let n=0;while(L.spi<0&&n++<120*90)step();inp.r=0;inp.j=0;for(let i=0;i<60;i++)step();return {spi:L.spi,got,T:Math.round(T),falls,x:Math.round(ball.x)};});
 ok('reached a checkpoint with gems in level 1-1',st.spi>=0&&st.got>0,JSON.stringify(st));
 await page.reload();await sleep(500);
 ok('after closing and reopening: title offers Continue',await page.evaluate(()=>btns[0].l())==='Continue');
 const cv=await page.evaluate(()=>{const r=document.getElementById('cv').getBoundingClientRect();return {x:r.left+160*r.width/320,y:r.top+140*r.height/240};});
 await page.touchscreen.tap(cv.x,cv.y);await sleep(300);
 const re=await page.evaluate(()=>({state,lv:L.d.n,spi:L.spi,got,T:Math.round(T),falls,x:Math.round(ball.x),cpx:L.cps[L.spi]&&L.cps[L.spi].x,flags:L.gems.filter(g=>g.got).length}));
 ok('Continue resumes same level, checkpoint, gems, time and falls',re.state==='play'&&re.lv==='First Hops'&&re.spi===st.spi&&re.got>=st.got&&re.flags===re.got&&re.falls>=st.falls&&re.T>=st.T-1&&Math.abs(re.x-re.cpx)<40,JSON.stringify(re));
 await page.evaluate(()=>{go('pause');btns[1].f();});
 ok('Restart starts clean and forgets the old run',await page.evaluate(()=>got===0&&T<1&&save.cur===null));
 await page.evaluate(()=>{ball.x=L.goal.x;ball.y=L.goal.y-20;step();});
 ok('finishing a level clears the in-progress save and records the result',await page.evaluate(()=>state==='results'&&save.cur===null&&save.lv['0-0'].s>=1));
 await page.evaluate(()=>{try{localStorage.setItem('plumhop_v1',JSON.stringify({lv:{},cur:{w:0,l:0,sp:'x',cp:'<b>',gm:'111',sw:'',en:'',t:5,f:1}}));}catch(e){}});await page.reload();await sleep(400);
 ok('tampered in-progress save is rejected',await page.evaluate(()=>save.cur===null&&state==='title'));
 await page.evaluate(()=>{try{localStorage.removeItem('plumhop_v1');}catch(e){}});
 ok('no script errors',errs.length===0,errs.join('|'));await b.close();console.log(bad?'FAILED '+bad:'RESUME CHECKS PASS');process.exit(bad?1:0);
})().catch(e=>{console.log('CRASH',e);process.exit(2);});
