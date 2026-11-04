// Runtime do motor "quadro": câmera com paralaxe, atuação por pose-chave, silhuetas contínuas de braço e perna, efeitos e interface.
const D=window.DADOS;
const cl=(x,a=0,b=1)=>Math.min(b,Math.max(a,x)),S=x=>x*x*(3-2*x),E=x=>1-(1-x)**3;
const B=x=>{const c=1.70158,u=x-1;return 1+(c+1)*u*u*u+c*u*u};
const lerp=(a,b,u)=>a+(b-a)*u;
const set=(e,a,v)=>{if(e)e.setAttribute(a,v)};
const f1=n=>n.toFixed(1);

// troca por pose-chave: antecipa, chega passando um pouco e assenta
const A=u=>u<.22?-.07*Math.sin(Math.PI*u/.22):B((u-.22)/.78);
const mix=(a,b,u)=>{
  if(Array.isArray(a)&&Array.isArray(b))return a.map((v,i)=>typeof v==='number'&&typeof b[i]==='number'?lerp(v,b[i],u):(u>.5?b[i]:v));
  if(typeof a==='number'&&typeof b==='number')return lerp(a,b,u);
  return u>.5?b:a;
};
function poseEm(tr,t){
  let i=tr.length-1;while(i>0&&t<tr[i][0])i--;
  const a=tr[i][1],nx=tr[i+1];
  if(!nx)return a;
  const d=Math.min(nx[2]||.34,nx[0]-tr[i][0]),u=cl((t-(nx[0]-d))/d);
  if(u<=0)return a;
  const v=A(u),o={};
  for(const k in a)o[k]=(k==='osc')?(u>.5?nx[1][k]:a[k]):mix(a[k],nx[1][k],v);
  o._u=u;
  return o;
}
function keyf(L,t,ease){ // [[t,v...]...]
  let i=L.length-1;while(i>0&&t<L[i][0])i--;
  const a=L[i],b=L[i+1];if(!b)return a.slice(1);
  const u=(ease||S)(cl((t-a[0])/Math.max(.0001,b[0]-a[0])));
  return a.slice(1).map((v,k)=>lerp(v,b[k+1],u));
}

// ---------- silhueta contínua
function ik(Sh,T,a,b,bend){
  let dx=T[0]-Sh[0],dy=T[1]-Sh[1],d=Math.hypot(dx,dy)||1;
  const mx=(a+b)*.985,mn=Math.abs(a-b)+(a+b)*.3;
  const dd=cl(d,mn,mx);dx*=dd/d;dy*=dd/d;
  const W=[Sh[0]+dx,Sh[1]+dy];
  const ca=cl((a*a+dd*dd-b*b)/(2*a*dd),-1,1),ang=Math.atan2(dy,dx)+bend*Math.acos(ca);
  return [[Sh[0]+a*Math.cos(ang),Sh[1]+a*Math.sin(ang)],W];
}
function linha(P0,P1,P2){
  const r=.42,A0=[lerp(P1[0],P0[0],r),lerp(P1[1],P0[1],r)],C0=[lerp(P1[0],P2[0],r),lerp(P1[1],P2[1],r)],o=[];
  for(let i=0;i<10;i++){const u=(i/10)**1.7;o.push([lerp(P0[0],A0[0],u),lerp(P0[1],A0[1],u)])}
  for(let i=0;i<=8;i++){const u=i/8,v=1-u;o.push([v*v*A0[0]+2*v*u*P1[0]+u*u*C0[0],v*v*A0[1]+2*v*u*P1[1]+u*u*C0[1]])}
  for(let i=1;i<=4;i++){const u=i/4;o.push([lerp(C0[0],P2[0],u),lerp(C0[1],P2[1],u)])}
  return o;
}
function offs(pts,w){ // w: u->meia largura
  const n=pts.length,len=[0];for(let i=1;i<n;i++)len[i]=len[i-1]+Math.hypot(pts[i][0]-pts[i-1][0],pts[i][1]-pts[i-1][1]);
  const T=len[n-1]||1,Lf=[],Rt=[],U=[];
  for(let i=0;i<n;i++){
    const p=pts[Math.max(0,i-1)],q=pts[Math.min(n-1,i+1)],dx=q[0]-p[0],dy=q[1]-p[1],m=Math.hypot(dx,dy)||1,u=len[i]/T,h=w(u);
    U.push(u);Lf.push([pts[i][0]-dy/m*h,pts[i][1]+dx/m*h]);Rt.push([pts[i][0]+dy/m*h,pts[i][1]-dx/m*h]);
  }
  return{Lf,Rt,U};
}
const pathOf=P=>'M'+P.map(p=>f1(p[0])+' '+f1(p[1])).join('L');
const pw=(a,b,c)=>u=>u<.5?lerp(a,b,u*2):lerp(b,c,(u-.5)*2);
function membro(g,S0,M0,W0,wS,frac,wM1,wM2,capFim){
  // pele: inteira; manga: até `frac`, mais larga, sempre uma peça só e com contorno fechado na boca da manga
  const pts=linha(S0,M0,W0);
  const pS=g.pS,lS=g.lS,pM=g.pM,lM=g.lM;
  if(frac<1){
    const o=offs(pts,pw(wS[0]/2,wS[1]/2,wS[2]/2));
    const k0=capFim?o.U.findIndex(u=>u>=frac*.6):0,sL=o.Lf.slice(k0),sR=o.Rt.slice(k0); // a pele só existe da metade da manga para baixo
    set(pS,'d',pathOf(sL)+'L'+[...sR].reverse().map(p=>f1(p[0])+' '+f1(p[1])).join('L')+'z');
    set(lS,'d',pathOf(sL)+pathOf(sR));
    const o2=offs(pts,u=>{const v=u/frac;return lerp(wM1/2,wM2/2,v)*(Math.sqrt(Math.max(0,1-(1-Math.min(1,v/.26))**2)))*(1+.08*Math.sin(Math.min(1,v/.7)*Math.PI))}); // deltoide: calota redonda, sem canto
    const iu=o2.U.findIndex(u=>u>=frac),a=o2.Lf.slice(0,iu+1),b=o2.Rt.slice(0,iu+1);
    set(pM,'d',pathOf(a)+'L'+[...b].reverse().map(p=>f1(p[0])+' '+f1(p[1])).join('L')+'z');
    const ea=a[a.length-1],eb=b[b.length-1],mx=(ea[0]+eb[0])/2,my=(ea[1]+eb[1])/2,c=pts[iu];
    const q=[lerp(mx,mx+(c[0]-pts[iu-1][0]),1.1),lerp(my,my+(c[1]-pts[iu-1][1]),1.1)];
    const boca=`Q${f1(q[0])} ${f1(q[1])} ${f1(eb[0])} ${f1(eb[1])}`,fora=pathOf(a)+boca+'L'+[...b].reverse().map(p=>f1(p[0])+' '+f1(p[1])).join('L');
    if(capFim){const k=Math.max(1,Math.round(a.length*.42));set(lM,'d',pathOf(a.slice(k))+boca+'L'+b.slice(k).reverse().map(p=>f1(p[0])+' '+f1(p[1])).join('L'));set(capFim,'d',fora+'z')} // ombro funde no tronco; da metade da manga para baixo a linha separa o braço do corpo
    else set(lM,'d',fora);
  }else{
    set(pS,'d','');set(lS,'d','');
    const lw=pw(wM1/2,(wM1+wM2)/4,wM2/2),o=offs(pts,capFim?u=>lw(u)*Math.sqrt(Math.max(0,1-(1-Math.min(1,u/.12))**2)):lw);
    const fora=pathOf(o.Lf)+'L'+[...o.Rt].reverse().map(p=>f1(p[0])+' '+f1(p[1])).join('L');
    set(pM,'d',fora+'z');
    const ea=o.Lf[o.Lf.length-1],eb=o.Rt[o.Rt.length-1];
    if(capFim){const k=o.U.findIndex(u=>u>=.2);set(lM,'d',pathOf(o.Lf.slice(k))+'L'+f1(eb[0])+' '+f1(eb[1])+pathOf(o.Rt.slice(k)));set(capFim,'d',fora+'z')}
    else set(lM,'d',pathOf(o.Lf)+'L'+f1(eb[0])+' '+f1(eb[1])+pathOf([...o.Rt]));
  }
}

// ---------- preparação
const planos=D.planos.map((P,i)=>{
  const el=document.getElementById('p'+i);
  const q={el,w0:el.querySelector('.w0'),w1:el.querySelector('.w1'),wS:el.querySelector('.wS'),wB:el.querySelector('.wB'),d:P};
  q.vida=[...el.querySelectorAll('[data-vida]')].map(e=>({e,v:e.getAttribute('data-vida').split(':')}));
  q.atores=(P.atores||[]).map((a,k)=>{
    const g=el.querySelector('.ator'+k),gs=el.querySelector('.topo'+k);
    const m={};
    for(const s of ['N','F']){
      const b=g.querySelector('.b'+s);
      m[s]={b,u:g.querySelector('.u'+s),pS:b.querySelector('.pS'),lS:b.querySelector('.lS'),pM:b.querySelector('.pM'),lM:b.querySelector('.lM'),h:b.querySelector('.m'+s),
        M:[...b.querySelector('.m'+s).querySelectorAll('[data-m]')],P:[...b.querySelector('.m'+s).querySelectorAll('[data-p]')],slot:g.querySelector('.b'+s+'slot'),onde:'c'};
      const l=g.querySelector('.l'+s);
      m['L'+s]={pS:l.querySelector('.pS'),lS:l.querySelector('.lS'),pM:l.querySelector('.pM'),lM:l.querySelector('.lM'),f:l.querySelector('.f'+s)};
    }
    return {a,g,gs,m,tP:g.querySelector('.tP'),tS:g.querySelector('.tS'),tor:g.querySelector('.tor'),cab:g.querySelector('.cab'),So:g.querySelector('.cSo'),Bo:g.querySelector('.cBo'),Pu:g.querySelector('.cPu'),Pi:g.querySelector('.cPi'),La:g.querySelector('.cLa'),
      Li:[...g.querySelectorAll('.cLi')],sombra:g.querySelector('.sombra'),ex:'',c:D.chars[a.nome],seed:k*1.7+i*.37,
      tr:a.poses,mov:a.mov};
  });
  q.riscos=Object.entries(P.riscos||{}).map(([k,v])=>({e:el.querySelector('[data-risco="'+k+'"]'),v}));
  q.riscos.forEach(r=>set(r.e,'stroke-dasharray','1 1'));
  q.obj=(P.objetos||[]).map(o=>({e:el.querySelector('[data-obj="'+o.id+'"]'),o}));
  q.gatos=[...el.querySelectorAll('.gato')].map(e=>({e,sent:e.querySelector('.gs'),corr:e.querySelector('.gc'),g:{cab:e.querySelector('.gcab'),rabo:e.querySelector('.rabo'),pis:e.querySelector('.gpisca')}}));
  q.fx=(P.efeitos||[]).map((f,k)=>({f,e:el.querySelector('.fx'+k),its:[...el.querySelectorAll('.fx'+k+'>*')]}));
  return q;
});

function vive(q,t){
  for(const{e,v}of q.vida){
    const k=v[0],a=+v[1],h=+v[2],p=+(v[3]||0);
    const o=e.getAttribute('data-base')||'';
    if(k==='x')set(e,'transform',`${o} translate(${f1(Math.sin(t*h+p)*a)} 0)`);
    else if(k==='y')set(e,'transform',`${o} translate(0 ${f1(Math.sin(t*h+p)*a)})`);
    else if(k==='rot')set(e,'transform',`${o} rotate(${(Math.sin(t*h+p)*a).toFixed(2)} ${v[4]||0} ${v[5]||0})`);
    else if(k==='anda'){const w=+v[3],s=((t*a+p)%w+w)%w;set(e,'transform',`${o} translate(${f1(s)} 0)`)}
    else if(k==='sobe'){const w=+v[3],s=((t*a+p)%w+w)%w;set(e,'transform',`${o} translate(0 ${f1(s)})`)}
    else if(k==='cai'){const w=+v[3],s=((t*a+(+v[4]||0))%w+w)%w;set(e,'transform',`${o} translate(0 ${f1(s)})`)}
    else if(k==='gira')set(e,'transform',`${o} rotate(${f1(t*a)})`);
    else if(k==='brilho')set(e,'opacity',(a+(h-a)*(.5+.5*Math.sin(t*p+(+v[4]||0)))).toFixed(3));
    else if(k==='pisca'){const on=Math.sin(t*h+p)+Math.sin(t*h*2.3+p)>a;set(e,'opacity',on?1:+(v[4]||0))}
  }
}

function ator(A0,t,T){
  const{a,g,gs,m,c}=A0;
  const P=poseEm(A0.tr,t);
  const flip=a.vira||1,sc=a.escala||1;
  const[x,y,rs]=A0.mov?keyf(A0.mov,t,a.movLinear?(u=>u):undefined):[a.x,a.y];
  const andando=P.anda;
  const ph=t*(andando||0)*Math.PI*2;
  const bob=andando?Math.abs(Math.sin(ph))*-7:0;
  const tf=`translate(${f1(x)} ${f1(y+bob*sc)}) scale(${(flip*sc).toFixed(3)} ${sc.toFixed(3)})`;
  set(g,'transform',tf);set(gs,'transform',tf);
  if(A0.tS&&A0.sent!==P.sent){A0.sent=P.sent;set(A0.tP,'display',P.sent?'none':'inline');set(A0.tS,'display',P.sent?'inline':'none')}
  const br=Math.sin(t*2.3+A0.seed)*1.5;
  const lean=P.lean+(c.curva||0)+(andando?2.5:0)+Math.sin(t*.8+A0.seed)*.35;
  const hip=[P.q[0],-c.quadril+P.q[1]],rad=lean*Math.PI/180,co=Math.cos(rad),si=Math.sin(rad);
  const R=(v)=>[hip[0]+v[0]*co-v[1]*si,hip[1]+v[0]*si+v[1]*co+br*(v[1]<-60?.5:0)];
  set(A0.tor,'transform',`translate(${f1(hip[0])} ${f1(hip[1]+br*.2)}) rotate(${lean.toFixed(2)}) scale(1 ${(1+br*.0018).toFixed(4)})`);
  const pn=R(c.pesc);
  const hr=P.hr+Math.sin(t*.9+A0.seed*2)*.8;
  set(A0.cab,'transform',`translate(${f1(pn[0]+P.h[0])} ${f1(pn[1]+P.h[1]+4)}) rotate(${hr.toFixed(2)})`);
  // expressão
  if(P.ex!==A0.ex){A0.ex=P.ex;const e=D.expr[P.ex];set(A0.So,'d',e.br);set(A0.Bo,'d',e.boca);set(A0.Bo,'fill',e.bf?'#5a1f28':'none');A0.lid=e.lid}
  const e=D.expr[P.ex];
  const per=2.9+((A0.seed*7)%1.3),bl=((t+A0.seed)%per)<.11;
  set(A0.Pi,'display',bl||P.fecha?'inline':'none');
  const lidv=P.lid==null?e.lid:P.lid,y0=((lidv)*38+0.5);
  for(const l of A0.Li)set(l,'transform',`translate(0 ${f1(y0)})`);
  set(A0.Pu,'transform',`translate(${f1(P.o[0]+Math.sin(t*.7+A0.seed)*.5)} ${f1(P.o[1])})`);
  set(A0.La,'display',P.lagrima?'inline':'none');
  // braços
  for(const s of['N','F']){
    const q=m[s],sh=R(s==='N'?c.ombroN:c.ombroF),rr=c.braco[0]+c.braco[1],t0=P[s];
    let tx=sh[0]+t0[0]*rr,ty=sh[1]+t0[1]*rr;
    const os=P.osc&&P.osc[s];
    if(os){tx+=Math.sin(t*os[2]*6.283+(os[3]||0))*os[0]*rr;ty+=Math.cos(t*os[2]*6.283+(os[3]||0))*os[1]*rr}
    if(andando&&P.balanco!==0){const v=Math.sin(ph+(s==='N'?0:Math.PI))*.26;tx+=v*rr*(s==='F'?-1:1)*(s==='N'?1:-1)*.6;ty-=Math.abs(v)*.06*rr}
    const bend=(t0[3]==null?1:t0[3]);
    const[Mm,W]=ik(sh,[tx,ty],c.braco[0],c.braco[1],bend);
    const[fr,wa,wb]=c.manga,porCima=s==='N'||(P.sobre||'').includes(s)||(P.frenteF&&s==='F');if(!porCima)set(q.u,'d','');
    membro(q,sh,Mm,W,c.wb,fr,wa,wb,porCima?q.u:null);
    const ang=t0[2]==null?Math.atan2(W[1]-Mm[1],W[0]-Mm[0])*180/Math.PI:t0[2];
    set(q.h,'transform',`translate(${f1(W[0])} ${f1(W[1])}) rotate(${ang.toFixed(1)})`);
    const mt=P['m'+s],pt=P['s'+s];
    if(q.mt!==mt){q.mt=mt;q.M.forEach(k=>set(k,'display',k.getAttribute('data-m')===mt?'inline':'none'))}
    if(q.pt!==pt){q.pt=pt;q.P.forEach(k=>set(k,'display',k.getAttribute('data-p')===pt?'inline':'none'))}
    const sob=(P.sobre||'').includes(s),alvo=sob?gs:(P.frenteF&&s==='F'?m.N.slot:q.slot);
    if(q.b.parentNode!==alvo){if(alvo===m.N.slot)alvo.insertBefore(q.b,alvo.firstChild);else alvo.appendChild(q.b)}
    // pernas
    const lq=m['L'+s],hp=[hip[0]+(s==='N'?-c.coxa[0]:c.coxa[0])*.75,hip[1]+6],rp=c.perna[0]+c.perna[1];
    let ax,ay,fa=P['a'+s]||0;
    const v=P['p'+s];
    ax=hp[0]+v[0]*rp;ay=hp[1]+v[1]*rp;
    if(P.ciclo){const an=t*P.ciclo*6.283+(s==='N'?0:Math.PI);ax=P.bb[0]+Math.cos(an)*42;ay=P.bb[1]+Math.sin(an)*42;fa=Math.sin(an)*10}
    if(andando){const si2=Math.sin(ph+(s==='N'?0:Math.PI)),co2=Math.cos(ph+(s==='N'?0:Math.PI));ax=hp[0]+si2*rp*.26;ay=-c.wp[2]*.6+Math.min(0,co2)*22+(hip[1]+c.quadril<0?0:0);fa=-si2*14}
    const[Kn,An]=ik(hp,[ax,ay],c.perna[0],c.perna[1],-1);
    const[sf,w1,w2]=c.short;
    membro(lq,hp,Kn,An,c.wp,sf,w1,w2);
    set(lq.f,'transform',`translate(${f1(An[0]-1)} ${f1(An[1]+6)}) rotate(${fa.toFixed(1)})`);
  }
  if(A0.sombra){set(A0.sombra,'display',P.sombra===0?'none':'inline');set(A0.sombra,'transform',`translate(${f1(hip[0]*.4)} 0)`)}
}

function objetos(q,t){
  for(const{e,o}of q.obj){
    if(!e)continue;
    const[x,y,r,sc,op]=keyf(o.chaves,t,o.linear?(u=>u):(o.ease==='B'?B:(o.ease==='E'?E:S)));
    set(e,'transform',`translate(${f1(x)} ${f1(y)}) rotate(${r.toFixed(2)}) scale(${sc.toFixed(3)})`);
    set(e,'opacity',op.toFixed(3));set(e,'display',op<.01?'none':'inline');
  }
}

function riscos(q,t){for(const r of q.riscos){const u=cl((t-r.v[0])/(r.v[1]-r.v[0]));set(r.e,'stroke-dashoffset',(1-u).toFixed(3));set(r.e,'opacity',u>0?1:0)}}
function efeitos(q,t){
  for(const{f,e,its}of q.fx){
    const on=t>=f.de&&t<=f.ate+(f.resto||0);set(e,'display',on?'inline':'none');if(!on)continue;
    const n=its.length,tt=t-f.de,span=f.ate-f.de;
    if(f.tipo==='fumaca'||f.tipo==='vapor'){
      const dur=f.vida||1.8;
      its.forEach((c,i)=>{
        const s=i/n,lt=((tt+s*dur)%dur)/dur,ok=tt+s*dur>=dur*.0&&t<=f.ate+dur;
        const seed=Math.sin(i*12.9898)*43758.5453,rn=seed-Math.floor(seed);
        const px=f.x+(rn-.5)*(f.lx||30)+Math.sin(lt*5+i)*16*lt+(f.vento||0)*lt;
        const py=f.y-lt*(f.sobe||260);const r=(f.r0||16)+lt*(f.r1||60);
        const off=t>f.ate&&lt<(t-f.ate)/dur;
        set(c,'cx',f1(px));set(c,'cy',f1(py));set(c,'r',f1(r));set(c,'opacity',off?0:(Math.sin(lt*Math.PI)*(f.op||.8)).toFixed(3));
      });
    }else if(f.tipo==='moedas'){
      its.forEach((c,i)=>{
        const sd=Math.sin(i*78.233)*43758.5453,rn=sd-Math.floor(sd);
        const t0=i/n*span*.8,lt=(tt-t0)/(f.vida||1.0);
        if(lt<0||lt>1){set(c,'display','none');return}
        set(c,'display','inline');
        const vx=(rn-.5)*(f.lx||700),h=(f.alto||520)*(.7+.3*rn);
        const px=f.x+lt*(((f.alvo?f.alvo[0]:f.x+vx)-f.x)),py=f.y+lt*((f.alvo?f.alvo[1]:f.y+200)-f.y)-Math.sin(lt*Math.PI)*h;
        set(c,'transform',`translate(${f1(px)} ${f1(py)}) scale(${(Math.abs(Math.cos(lt*9+i))*.75+.3).toFixed(3)} 1)`);
      });
    }else if(f.tipo==='pingos'){
      its.forEach((c,i)=>{
        const sd=Math.sin(i*93.7)*43758.5453,rn=sd-Math.floor(sd),pdur=.5+rn*.3,lt=((t+rn*3)%pdur)/pdur;
        const sd2=Math.sin(i*37.1)*1000,rn2=sd2-Math.floor(sd2);
        set(c,'cx',f1(f.x+rn*f.lx));set(c,'cy',f1(f.y+rn2*(f.ly||60)));set(c,'rx',f1(lt*(f.r||18)));set(c,'ry',f1(lt*(f.r||18)*.3));set(c,'opacity',((1-lt)*.75).toFixed(3));
      });
    }else if(f.tipo==='faiscas'){
      its.forEach((c,i)=>{
        const lt=cl(tt/(f.ate-f.de)),ang=i/n*6.283;const r=E(lt)*(f.r||120);
        set(c,'transform',`translate(${f1(f.x+Math.cos(ang)*r)} ${f1(f.y+Math.sin(ang)*r)}) scale(${(1-lt).toFixed(2)})`);
      });
    }
  }
}

function gatos(q,t){
  for(const G of q.gatos){
    const cf=q.d.gato;if(!cf)continue;
    const c0=keyf(cf.mov,t);
    set(G.e,'transform',`translate(${f1(c0[0])} ${f1(c0[1])}) scale(${(c0[2]*(cf.vira||1)).toFixed(3)} ${c0[2].toFixed(3)})`);
    const corre=cf.corre!=null&&t>=cf.corre;
    set(G.sent,'display',corre?'none':'inline');set(G.corr,'display',corre?'inline':'none');
    set(G.g.rabo,'transform',`rotate(${f1(Math.sin(t*3.2)*8)} 54 108)`);
    set(G.g.cab,'transform',`rotate(${f1(Math.sin(t*.9)*5)} 2 0)`);
    set(G.g.pis,'display',(t%3.1)<.12?'inline':'none');
  }
}

// ---------- interface
const ui={};
['hDias','hVal','hBar','hPct','leg','legT','item','itemN','itemT','itemS','itemI','selo','seloT','seloR','inv','fade'].forEach(i=>ui[i]=document.getElementById(i));
const brl=v=>D.valorFmt==='num'?String(Math.round(v))+(D.valorSuf||''):'R$ '+v.toFixed(2).replace('.',',').replace(/\B(?=(\d{3})+(?!\d))/g,'.');
function hud(t){
  const H=D.hud;
  let i=H.dias.length-1;while(i>0&&t<H.dias[i][0])i--;
  const dia=H.dias[i][1],dt=t-H.dias[i][0];
  ui.hDias.textContent=dia;
  set(ui.hDias,'transform',dt<.3&&i>0?`translate(0 ${f1(-4+3.9*0)}) scale(${(1+.3*(1-dt/.3)).toFixed(3)})`:'');
  const v=keyf(H.valor,t,u=>E(u))[0];
  ui.hVal.textContent=brl(v);
  const mv=t>=(D.metaDe||0),pct=mv?cl(v/D.meta):0,hm=document.getElementById('hMeta');hm.textContent=mv?hm.getAttribute('data-t'):'META ???';
  set(ui.hBar,'width',f1(pct*H.barW));set(ui.hBar,'fill',pct>=.999?'#3fd17a':(H.cor?H.cor:'#ffd23f'));
  ui.hPct.textContent=mv?Math.floor(pct*100+.0001)+'%':'';
  // inventário
  let w=D.itensInv;
  [...ui.inv.children].forEach(c=>{
    const k=w[c.getAttribute('data-i')],on=t>=k.de&&t<(k.ate==null?1e9:k.ate);
    set(c,'display',on?'inline':'none');
    if(on){const n=w.filter(z=>t>=z.de&&t<(z.ate==null?1e9:z.ate)&&z.ord<=k.ord).length;set(c,'transform',`translate(${704-52-(n-1)*58} 108) scale(${(1+.3*Math.max(0,1-(t-k.de)/.3)).toFixed(3)})`);
      const xe=c.querySelector('.x');set(xe,'display',k.ate!=null&&!k.troca&&t>k.ate-1.2?'inline':'none')}
  });
}
function legenda(t){
  const w=D.legendas.find(q=>t>=q[0]&&t<q[1]),T=ui.legT;
  if(!w){if(T.textContent)T.textContent='';return}
  const id=w[0];
  if(ui._lg!==id){ui._lg=id;T.textContent='';
    for(const[p,cor]of w[2]){const s=document.createElementNS('http://www.w3.org/2000/svg','tspan');s.textContent=p+' ';s.setAttribute('fill',cor);T.appendChild(s)}
    T.setAttribute('font-size',64);T.setAttribute('y',0);
    const L0=T.getComputedTextLength();ui._lk=Math.min(1,630/L0);
  }
  const a=cl((t-w[0])/.1),z=(.9+.1*B(a))*ui._lk;
  set(ui.leg,'transform',`translate(360 ${w[3]}) scale(${z.toFixed(3)})`);
}
function toasts(t){
  const k=D.toasts.find(q=>t>=q.de&&t<q.ate);
  if(!k){set(ui.item,'display','none')}else{
    set(ui.item,'display','inline');
    if(ui._ti!==k.de){ui._ti=k.de;ui.itemT.textContent=k.titulo;ui.itemN.textContent=k.nome;set(ui.itemT,'fill',k.cor||'#ffd23f');
      [...ui.itemI.children].forEach(c=>set(c,'display',c.getAttribute('data-i')===k.icone?'inline':'none'));
      const w=ui.itemN.getComputedTextLength(),z=Math.min(1,(k.max||350)/w);set(ui.itemN,'font-size',(22*z).toFixed(1));
      set(ui.itemS,'width',f1(Math.max(240,78+Math.min(w,k.max||350)+16)));
    }
    const u=E(cl((t-k.de)/.26));set(ui.item,'transform',`translate(${f1(16-340*(1-u))} ${D.toastY||108})`);
  }
  const s=D.selos.find(q=>t>=q.de&&t<q.ate);
  if(!s){set(ui.selo,'display','none')}else{
    set(ui.selo,'display','inline');
    if(ui._se!==s.de){ui._se=s.de;ui.seloT.textContent=s.contador?s.contador[1]+s.contador[3]:s.texto;set(ui.seloT,'font-size',s.fonte||30);set(ui.seloR,'fill',s.cor||'#b4231c');
      const w=Math.max(120,ui.seloT.getComputedTextLength()+48);const f=s.fonte||30,h=f*1.5;set(ui.seloT,'y',(f*.36).toFixed(1));[...ui.selo.querySelectorAll('rect')].forEach((r,i)=>{set(r,'x',-w/2+(i?6:0));set(r,'width',w-(i?12:0));set(r,'y',-h/2+(i?6:0));set(r,'height',h-(i?12:0))})}
    if(s.contador){const[a,b,dr,suf]=s.contador;ui.seloT.textContent=Math.round(a+(b-a)*E(cl((t-s.de)/dr)))+suf}
    const u=cl((t-s.de)/.16);set(ui.selo,'transform',`translate(${s.x} ${s.y}) rotate(${s.rot||-7}) scale(${(u<1?2.1-1.1*B(u):1).toFixed(3)})`);
  }
}

function dialogo(t){
  const d=(D.dialogos||[]).find(q=>t>=q.de&&t<q.ate),G=document.getElementById('dlg');
  if(!d){set(G,'display','none');return}
  set(G,'display','inline');const u=E(cl((t-d.de)/.2));set(G,'transform',`translate(0 ${f1(d.y+60*(1-u))})`);set(G,'opacity',u.toFixed(2));
  if(ui._dl!==d.de){ui._dl=d.de;document.getElementById('dlgN').textContent=d.nome;[...document.getElementById('dlgR').children].forEach(c=>set(c,'display',c.getAttribute('data-r')===d.retrato?'inline':'none'))}
  let n=Math.floor((t-d.de)*(d.vel||26));d.linhas.forEach((l,i)=>{document.getElementById('dlgT'+i).textContent=l.slice(0,Math.max(0,n));n-=l.length})
}
let atual=-1;
window.frame=T=>{
  let i=planos.findIndex(p=>T>=p.d.t0&&T<p.d.t1);if(i<0)i=planos.length-1;
  if(i!==atual){if(atual>=0)set(planos[atual].el,'display','none');set(planos[i].el,'display','inline');atual=i}
  const q=planos[i],P=q.d,t=T-P.t0,ts=T-P.cena0;
  const c0=P.cam[0],[cx0,cy0,z0]=[c0[1],c0[2],c0[3]],[cx,cy,z]=keyf(P.cam,t);
  let sx=0,sy=0;
  for(const s of(P.tremor||[])){if(t>=s[0]&&t<s[1]){const k=1-(t-s[0])/(s[1]-s[0]);sx+=Math.sin(t*61)*s[2]*k;sy+=Math.cos(t*47)*s[2]*.7*k}}
  const lay=(e,k)=>{if(!e)return;const zz=z0*(1+(z/z0-1)*k),xx=cx0+(cx-cx0)*k,yy=cy0+(cy-cy0)*k;set(e,'transform',`translate(${f1(360-xx*zz+sx)} ${f1(640-yy*zz+sy)}) scale(${zz.toFixed(4)})`)};
  lay(q.w0,.86);lay(q.wS,.55);lay(q.w1,1);
  if(q.wB){const k=1.5,dz=1+(z/z0-1)*k;set(q.wB,'transform',`translate(${f1(360+(cx0-cx)*z*k-360*dz+sx*1.3)} ${f1(640+(cy0-cy)*z*k-640*dz+sy*1.3)}) scale(${dz.toFixed(4)})`)}
  vive(q,T);objetos(q,t);riscos(q,t);q.atores.forEach(a=>ator(a,t,T));gatos(q,t);efeitos(q,t);
  hud(T);legenda(T);toasts(T);dialogo(T);
  let fd=0;for(const f of D.fades){if(T>=f[0]&&T<f[1]){const u=(T-f[0])/(f[1]-f[0]);fd=f[2]+(f[3]-f[2])*u}}
  set(ui.fade,'opacity',fd.toFixed(3));set(ui.fade,'display',fd>.001?'inline':'none');
  set(document.getElementById('hudG'),'display',P.semHud?'none':'inline');
};
