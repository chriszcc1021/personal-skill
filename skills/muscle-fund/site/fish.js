// fish.js — 6 鱼角色覆盖 peeps.js 的 renderAvatar
// 不动 state.js，只是把 avatar 渲染从 SVG 换成 PNG
(function(global){
  const FISH_IDS = ['limp','dopey','cool','dazed','working','flat'];
  const FISH_LABEL = {
    limp:'瘫瘫鱼', dopey:'呆呆鱼', cool:'酷酷鱼',
    dazed:'慒慒鱼', working:'打工鱼', flat:'躺平鱼',
  };

  // 按名字稳定分配 fishId（hash）
  function pickFishId(name){
    if(!name) return 'limp';
    let h=0;
    for(let i=0;i<name.length;i++){ h=(h*31 + name.charCodeAt(i)) & 0xffffffff; }
    return FISH_IDS[Math.abs(h) % FISH_IDS.length];
  }

  // 取 fishId：avatar.fishId 优先，否则按 name hash
  function resolveFishId(avatar, name){
    if(avatar && avatar.fishId && FISH_IDS.includes(avatar.fishId)) return avatar.fishId;
    return pickFishId(name||'');
  }

  // 等级 0-9 (10 档) · 1 个月 22 个工作日满级
  // 只看打卡天数，不看部位
  function levelFor10(member){
    if(!member || !member.checkins) return 0;
    const days = Object.keys(member.checkins).filter(k=>(member.checkins[k]||[]).length>0).length;
    if(days<=0)  return 0;
    if(days<3)   return 1;
    if(days<5)   return 2;
    if(days<8)   return 3;
    if(days<11)  return 4;
    if(days<14)  return 5;
    if(days<17)  return 6;
    if(days<20)  return 7;
    if(days<22)  return 8;
    return 9;
  }

  // 等级 → 整体 scale + 鼓肌效果
  function levelFor(count){
    if(!count) return 0;
    if(count<5) return 0;
    if(count<10) return 1;
    if(count<20) return 2;
    if(count<30) return 3;
    return 4;
  }
  const SCALE = [1.0, 1.05, 1.12, 1.2, 1.3];

  // 查有没有 10 档目录（仅 limp 有）
  const HAS_LEVELS = { limp: true, cool: true, working: true, dazed: true, dopey: true, flat: true };

  // 渲染：img + filter 模拟变粗（saturate + brightness）
  function renderFish(fishId, growth, member){
    growth = growth || {};
    if(HAS_LEVELS[fishId]){
      const lv = levelFor10(member);
      return `<img src="assets/fish-levels/${fishId}/lv${lv}.png" alt="${FISH_LABEL[fishId]} lv${lv}" style="width:100%;height:100%;object-fit:contain;transition:opacity .4s ease;" draggable="false">`;
    }
    // 旧逻辑（其他鱼还只有一张）
    const totalLv = Math.max(
      levelFor(growth.arms),
      levelFor(growth.chest),
      levelFor(growth.abs),
      levelFor(growth.back),
      levelFor(growth.legs),
      levelFor(growth.shoulders),
    );
    const s = SCALE[totalLv] || 1;
    const sat = 1 + totalLv*0.1;
    return `<img src="assets/fish/${fishId}.png" alt="${FISH_LABEL[fishId]}" style="width:100%;height:100%;object-fit:contain;transform:scale(${s});filter:saturate(${sat});transition:transform .5s ease,filter .5s ease;" draggable="false">`;
  }

  // 兼容 Peeps API：renderAvatar(avatar, growth, member)
  function renderAvatar(avatar, growth, member){
    let fishId, name;
    if(typeof avatar === 'object' && avatar){
      fishId = avatar.fishId;
      name = avatar.name;
    }
    if(!fishId) fishId = resolveFishId(avatar, name);
    return renderFish(fishId, growth, member);
  }

  global.Fish = { FISH_IDS, FISH_LABEL, pickFishId, resolveFishId, renderFish, levelFor };

  // 覆盖 Peeps.renderAvatar（peeps.js 必须先加载）
  // 由于加载顺序在 peeps.js 之后，等 DOMContentLoaded 时它已经在了
  function patch(){
    if(global.Peeps){
      const origRender = global.Peeps.renderAvatar;
      global.Peeps.renderAvatar = function(avatar, growth, member){
        return renderAvatar(avatar, growth, member);
      };
    }
  }
  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded', patch);
  } else {
    patch();
  }
  // 立即 patch 一次以防同步代码先调用
  patch();
})(window);
