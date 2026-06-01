/* Muscle Fund — GSAP 动效层
   原则：不改 state / peeps / 业务逻辑；只在 render 之后追加视觉层
   依赖：GSAP 3.x 全局 gsap */
(function(){
  const MFAnim = {
    _lastFund: null,
    _firstPaint: true,
    _lastMembersHash: '',
    pendingBurst: false,
  };

  // ===== 工具 =====
  function fmt(n){ return Math.round(n).toLocaleString(); }
  function membersHash(showcase){
    return Array.from(showcase.children).map(el=>el.dataset.id||'_').join('|');
  }

  // ===== 金额 count-up + punch =====
  function tweenAmount(toVal, withPunch){
    const numEl = document.getElementById('amount-num');
    const wrapEl = document.getElementById('amount');
    if(!numEl) return;
    const fromVal = MFAnim._lastFund == null ? 0 : MFAnim._lastFund;
    if(fromVal === toVal && !withPunch){
      numEl.textContent = fmt(toVal);
      MFAnim._lastFund = toVal;
      return;
    }
    const obj = { v: fromVal };
    gsap.to(obj, {
      v: toVal,
      duration: MFAnim._firstPaint ? 1.4 : 0.9,
      ease: MFAnim._firstPaint ? 'expo.out' : 'power2.out',
      onUpdate: ()=>{ numEl.textContent = fmt(obj.v); },
    });
    if(withPunch){
      gsap.fromTo(wrapEl,
        { scale: 1 },
        { scale: 1.08, duration: 0.18, ease:'power2.out',
          yoyo:true, repeat:1 });
    } else if(MFAnim._firstPaint){
      gsap.from(wrapEl, {
        scale: 0.4, opacity: 0, duration: 1.1,
        ease: 'elastic.out(1, 0.55)'
      });
    }
    MFAnim._lastFund = toVal;
  }

  // ===== Showcase 入场 + halo 脉冲 =====
  function animateShowcase(){
    const sc = document.getElementById('showcase');
    if(!sc) return;
    const hash = membersHash(sc);
    const isNewLayout = hash !== MFAnim._lastMembersHash;
    MFAnim._lastMembersHash = hash;
    if(isNewLayout){
      gsap.from(sc.children, {
        y: 36, opacity: 0, scale: 0.92,
        duration: 0.7, ease: 'back.out(1.4)',
        stagger: { each: 0.06, from: 'start' },
      });
    }
    // halo 脉冲（已打卡）
    sc.querySelectorAll('.member.checked-today .avatar-wrap').forEach(el=>{
      if(el.dataset.haloed) return;
      el.dataset.haloed = '1';
      gsap.to(el, {
        boxShadow: '0 0 0 8px rgba(255,128,171,0.5)',
        duration: 1.1, ease: 'sine.inOut',
        yoyo: true, repeat: -1,
      });
    });
    // 空闲微晃
    sc.querySelectorAll('.member .avatar-wrap').forEach((el,i)=>{
      if(el.dataset.sway) return;
      el.dataset.sway = '1';
      gsap.to(el, {
        y: '+=4', duration: 2.4 + Math.random()*1.2,
        ease: 'sine.inOut', yoyo: true, repeat: -1,
        delay: i*0.15,
      });
    });
  }

  // ===== 部位按钮交互 =====
  function bindParts(){
    const root = document.getElementById('parts');
    if(!root || root.dataset.animBound) return;
    root.dataset.animBound = '1';
    root.addEventListener('click', e=>{
      const p = e.target.closest('.part');
      if(!p || p.classList.contains('done')) return;
      gsap.fromTo(p,
        { scale: 1 },
        { scale: 1.16, duration: 0.12, ease:'power2.out',
          yoyo:true, repeat:1 });
    }, true);
  }
  function animatePartsIn(){
    const root = document.getElementById('parts');
    if(!root) return;
    if(MFAnim._partsAnimated) return;
    MFAnim._partsAnimated = true;
    gsap.from(root.children, {
      y: 20, opacity: 0, duration: 0.5,
      ease: 'back.out(1.6)',
      stagger: 0.05, delay: 0.25,
    });
  }

  // ===== 打卡爆点 =====
  function burstAtAmount(){
    const wrap = document.getElementById('amount');
    if(!wrap) return;
    const r = wrap.getBoundingClientRect();
    const cx = r.left + r.width/2 + window.scrollX;
    const cy = r.top + r.height/2 + window.scrollY;
    const N = 14;
    for(let i=0;i<N;i++){
      const s = document.createElement('div');
      s.textContent = ['¥','★','✓','💪'][i%4];
      s.style.cssText = `position:absolute;left:${cx}px;top:${cy}px;font-size:${18+Math.random()*12}px;font-weight:900;color:${i%2?'#FFD600':'#FF80AB'};pointer-events:none;z-index:60;text-shadow:1.5px 1.5px 0 #0D3B4F;font-family:'Luckiest Guy',sans-serif`;
      document.body.appendChild(s);
      const ang = (i/N)*Math.PI*2 + Math.random()*0.4;
      const dist = 120 + Math.random()*80;
      gsap.to(s, {
        x: Math.cos(ang)*dist,
        y: Math.sin(ang)*dist - 40,
        rotation: (Math.random()-0.5)*240,
        opacity: 0,
        duration: 0.9 + Math.random()*0.4,
        ease: 'power2.out',
        onComplete: ()=>s.remove(),
      });
    }
  }

  // ===== Hero 入场 =====
  function animateHeroFirst(){
    if(!MFAnim._firstPaint) return;
    const checkin = document.getElementById('checkin-card');
    const cal = document.getElementById('calendar-card');
    if(checkin) gsap.from(checkin, { y: 30, opacity: 0, duration: 0.7, ease:'power3.out', delay: 0.5 });
    if(cal) gsap.from(cal, { y: 30, opacity: 0, duration: 0.7, ease:'power3.out', delay: 0.65 });
  }

  // ===== 日历换月入场 =====
  function animateCalendarRows(){
    const grid = document.getElementById('cal-grid');
    if(!grid) return;
    const rows = grid.querySelectorAll('.cal-row');
    gsap.from(rows, {
      x: 24, opacity: 0, duration: 0.4,
      ease: 'power2.out', stagger: 0.04,
    });
  }

  // ===== 公开 API =====
  MFAnim.afterRender = function(fundTotal){
    if(typeof gsap === 'undefined') return; // GSAP 没加载时静默退化
    tweenAmount(fundTotal, MFAnim.pendingBurst);
    if(MFAnim.pendingBurst){
      burstAtAmount();
      MFAnim.pendingBurst = false;
    }
    animateShowcase();
    bindParts();
    animatePartsIn();
    animateHeroFirst();
    MFAnim._firstPaint = false;
  };
  MFAnim.afterCalendar = animateCalendarRows;

  // 抽屉：用 GSAP 替原 CSS transition，弹回感
  MFAnim.bindDrawer = function(){
    const drawer = document.getElementById('drawer');
    if(!drawer || drawer.dataset.animBound) return;
    drawer.dataset.animBound = '1';
    gsap.set(drawer, { xPercent: 100 });
    new MutationObserver(muts=>{
      muts.forEach(m=>{
        if(m.attributeName!=='class') return;
        const isOpen = drawer.classList.contains('show');
        if(isOpen){
          gsap.fromTo(drawer,
            { xPercent: 100 },
            { xPercent: 0, duration: 0.5, ease: 'back.out(1.3)' });
        } else {
          gsap.to(drawer, { xPercent: 100, duration: 0.3, ease:'power2.in' });
        }
      });
    }).observe(drawer, { attributes: true, attributeFilter:['class'] });
  };

  window.MFAnim = MFAnim;
})();
