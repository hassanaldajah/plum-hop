// Level verifier v3 (rolling ball, jump on press): finds a deathless run that collects every gem and reaches the goal (Go-Explore style search with save states).
// Gems hanging over the same gap are searched as one group (they must be taken in a single flight).
// usage: node verify2.js <index.html> [w<world>|world-level ...]
const fs=require('fs');
const html=fs.readFileSync(process.argv[2],'utf8');
const code=html.match(/<script>([\s\S]*)<\/script>/)[1];
const noop=()=>{};const warns=[];
const ctx=new Proxy({},{get:(t,k)=>k==='createLinearGradient'||k==='createRadialGradient'?()=>({addColorStop:noop}):noop,set:()=>true});
const el={addEventListener:noop,classList:{add:noop,remove:noop},getContext:()=>ctx,clientWidth:640,getBoundingClientRect:()=>({left:0,top:0,width:640,height:480})};
const g={document:{getElementById:()=>el,addEventListener:noop,hidden:false},window:{},addEventListener:noop,requestAnimationFrame:noop,localStorage:{getItem:()=>null,setItem:noop},console:{log:console.log,warn:m=>warns.push(m)}};
const api=new Function(...Object.keys(g),code+`;return {WORLDS,NEED,startLevel,step,inp,go,draw,
 S:()=>({state,ball,L,got,falls,T}),
 snap:()=>({b:{...ball},T,jbuf,got,falls,landY,inW,sp:{...L.spawn},mv:L.movs.map(o=>({...o})),cr:L.crs.map(o=>({...o})),gt:L.gts.map(o=>({...o})),en:L.ens.map(o=>({...o})),sw:L.sws.map(o=>o.on),cp:L.cps.map(o=>o.on),sk:L.sps.map(o=>o.k),gm:L.gems.map(o=>o.got),ic:(L.ics||[]).map(o=>({...o}))}),
 load:s=>{Object.assign(ball,s.b);T=s.T;jbuf=s.jbuf;got=s.got;falls=s.falls;landY=s.landY;inW=s.inW;L.spawn={...s.sp};L.movs.forEach((o,i)=>Object.assign(o,s.mv[i]));L.crs.forEach((o,i)=>Object.assign(o,s.cr[i]));L.gts.forEach((o,i)=>Object.assign(o,s.gt[i]));L.ens.forEach((o,i)=>Object.assign(o,s.en[i]));L.sws.forEach((o,i)=>o.on=s.sw[i]);L.cps.forEach((o,i)=>o.on=s.cp[i]);L.sps.forEach((o,i)=>o.k=s.sk[i]);L.gems.forEach((o,i)=>o.got=s.gm[i]);(L.ics||[]).forEach((o,i)=>Object.assign(o,s.ic[i]));state='play';parts.length=0;}
};`)(...Object.values(g));

function runLevel(wi,li){
 const t0=Date.now();warns.length=0;
 api.go('title');api.startLevel(wi,li);api.draw();
 const L=api.S().L,d=L.d;let seed=(wi*31+li)*7919+17;const rnd=()=>(seed=(seed*16807)%2147483647)/2147483647;
 let cur=api.snap(),steps=0,tunnel=0;
 const surf=(p,x)=>{for(let i=0;i<p.length-1;i++){const a=p[i],c=p[i+1];if(c[0]>a[0]&&x>=a[0]&&x<=c[0])return a[1]+(c[1]-a[1])*(x-a[0])/(c[0]-a[0]);}return 1e9;};
 const inside=b=>{for(const p of L.polys){if(b.x<=p[0][0]+1||b.x>=p[p.length-1][0]-1)continue;const y=surf(p,b.x);if(b.y>y+2&&b.y<p.by-2)return true;}for(const p of L.plats)if(b.x>p.x+2&&b.x<p.x+p.w-2&&b.y>p.y+2&&b.y<p.y+p.h-2)return true;return false;};
 const buried=L.gems.map((q,i)=>inside({x:q.x,y:q.y})?i:-1).filter(i=>i>=0);
 const viable=s=>{for(let a=0;a<40;a++){api.load(s);let ok=true;for(let i=0;i<420;i++){if(i%30===0){const q=rnd();api.inp.r=q<.4?1:0;api.inp.l=q>.7?1:0;api.inp.j=rnd()<.5?1:0;}api.step();steps++;const st=api.S();if(st.state!=='play')return true;if(st.falls>s.falls){ok=false;break;}}if(ok)return true;}return false;};
 const explore=(ids,maxIter,isGoal)=>{
  const tgt=has=>{if(isGoal)return[L.goal.x,L.goal.y-20,1];let rem=0,t=null;for(const i of ids)if(!has(i)){rem++;if(!t)t=L.gems[i];}return t?[t.x,t.y,rem]:[0,0,0];};
  const dist=s=>{const t=tgt(i=>s.gm[i]);return (t[2]-1)*1000+Math.hypot(s.b.x-t[0],s.b.y-t[1]);};
  const done=()=>isGoal?api.S().state==='results':ids.every(i=>L.gems[i].got);
  const cells=new Map();
  const add=s=>{const dd=dist(s),key=Math.floor(s.b.x/8)+','+Math.floor(s.b.y/8)+','+s.sw.map(v=>v?1:0).join('')+(s.b.vy>0?'d':'u')+(isGoal?'':ids.filter(i=>s.gm[i]).length);const c=cells.get(key);if(!c){cells.set(key,{s,d:dd,v:0,k:0});return true;}if(dd<c.d-.5){c.s=s;c.d=dd;}return false;};
  add(cur);let arr=[...cells.values()],dirty=false;
  for(let it=0;it<maxIter;it++){
   if(dirty){arr=[...cells.values()];dirty=false;}
   let best=1e9;for(const c of arr)if(c.d<best)best=c.d;const base=Math.floor(best/1000)*1000;
   let tot=0;const w=new Float64Array(arr.length);for(let i=0;i<arr.length;i++){const c=arr[i],x=1/(Math.pow(1+(c.d-base)/40,2)*Math.sqrt(1+c.v)*Math.pow(1+c.k,1.5));w[i]=x;tot+=x;}
   let r=rnd()*tot,ci=0;while(ci<arr.length-1&&(r-=w[ci])>0)ci++;
   const c=arr[ci];c.v++;api.load(c.s);const f0=c.s.falls;
   const nMac=1+(rnd()*3|0);let dead=false;
   for(let m=0;m<nMac&&!dead;m++){
    const q=rnd(),t=tgt(i=>L.gems[i].got),toward=t[0]>=api.S().ball.x?'r':'l',away=toward==='r'?'l':'r';api.inp.r=0;api.inp.l=0;
    if(q<.6)api.inp[toward]=1;else if(q<.82)api.inp[away]=1;
    const len=8+(rnd()*52|0),jm=rnd(),t0=rnd()*len|0,hd=6+(rnd()*60|0);let rel=false;
    api.inp.j=jm<.38?0:jm<.62?1:jm<.82?0:1;
    for(let i=0;i<len;i++){
     if(jm>=.62&&jm<.82)api.inp.j=i>=t0&&i<t0+hd?1:0;
     else if(jm>=.82){const bl=api.S().ball;if(bl.gnd>0&&api.inp.j&&!rel){api.inp.j=0;rel=true;}else{api.inp.j=1;rel=false;}}
     api.step();steps++;const s=api.S();
     if(done()){const sn=api.snap();if(isGoal||viable(sn))return sn;dead=true;break;}
     if(s.state!=='play'||s.falls>f0){dead=true;break;}}
    if(!dead){if(inside(api.S().ball))tunnel++;if(add(api.snap()))dirty=true;}
   }
   if(dead)c.k++;
  }
  return null;
 };
 const order=L.gems.map((q,i)=>i).sort((a,b)=>L.gems[a].x-L.gems[b].x||L.gems[b].y-L.gems[a].y);
 const overGap=i=>L.gy(L.gems[i].x)>1e8;
 const groups=[];for(const i of order){const gr=groups[groups.length-1];if(gr&&overGap(i)&&overGap(gr[gr.length-1])&&L.gems[i].x-L.gems[gr[gr.length-1]].x<=45)gr.push(i);else groups.push([i]);}
 const name=gr=>gr.map(i=>i+'@'+Math.round(L.gems[i].x)+','+Math.round(L.gems[i].y)).join('+');
 let failed=[];const hist=[],backtracked=[];
 for(const gr of groups){
  const ids=gr.filter(i=>!cur.gm[i]);if(!ids.length)continue;
  const before=cur;let r=explore(ids,3500*ids.length),used=ids,start=before;
  // the committed state may already be past a point of no return: step back and search the previous gems together with this one
  for(let back=1;!r&&back<=3&&hist.length>=back;back++){
   const h=hist[hist.length-back];used=hist.slice(hist.length-back).reduce((a,q)=>a.concat(q.ids),[]).concat(ids);start=h.before;cur=start;r=explore(used,15000);
   if(r){hist.length-=back;backtracked.push(name(used));}
  }
  if(r){hist.push({before:start,ids:used});cur=r;}else{cur=before;failed.push(gr);}
 }
 const failed2=[];
 for(const gr of failed){const ids=gr.filter(i=>!cur.gm[i]);if(!ids.length)continue;const r=explore(ids,20000*ids.length);if(r)cur=r;else failed2.push(gr);}
 const win=explore(null,25000,true);
 const S=api.S();
 return {lv:(wi+1)+'-'+(li+1),name:d.n,gems:L.gems.length,won:!!win,got:win?S.got:cur.got,deaths:win?S.falls:cur.falls,T:Math.round(win?S.T:cur.T),unreached:failed2.map(name),retried:failed.map(name),backtracked,buried,tunnel,warns:warns.slice(),msteps:+(steps/1e6).toFixed(1),sec:+((Date.now()-t0)/1000).toFixed(1)};
}
const args=process.argv.slice(3);const list=[];
api.WORLDS.forEach((w,wi)=>w.levels.forEach((d,li)=>{if(!args.length||args.includes(wi+'-'+li)||args.includes('w'+wi))list.push([wi,li]);}));
let bad=0;
for(const [wi,li] of list){const r=runLevel(wi,li);const ok=r.won&&r.got===api.NEED&&r.gems===api.NEED&&!r.unreached.length&&!r.buried.length&&!r.tunnel&&!r.warns.length;if(!ok)bad++;console.log((ok?'PASS ':'FAIL ')+JSON.stringify(r));}
console.log(bad?('FAILED LEVELS: '+bad):'ALL PASS');
