// characters.js — 比奇堡风格分层 SVG 角色库
// 每个角色暴露：renderCharacter(charId, growth) -> SVG string
// growth: { arms, chest, back, abs, shoulders, legs }
// 每个角色 SVG 必须有这些 group id：
//   #bg #legs #shorts #torso #chest #abs #arms-left #arms-right #shoulders #head
// 我代码会按部位等级 transform: scale() 那个 group。

(function (global) {

  // ===== 等级 → scale =====
  function levelFor(count){
    if(!count) return 0;
    if(count<5) return 0;
    if(count<10) return 1;
    if(count<20) return 2;
    if(count<30) return 3;
    return 4;
  }
  const SCALES=[1.0,1.2,1.5,1.8,2.2];

  // ===== 角色 1：海绵方块（黄方海绵 + 红短裤） =====
  // 整体 viewBox: 200 × 280
  // 部位 group 各自带 transform-origin 让放大居中
  const SPONGE_BOY = ({arms,chest,back,abs,shoulders,legs})=>{
    const sArms=SCALES[arms], sChest=SCALES[chest], sBack=SCALES[back];
    const sAbs=SCALES[abs], sSh=SCALES[shoulders], sLegs=SCALES[legs];
    // 背肌让躯干变宽
    const torsoScaleX = 1 + (sBack-1)*0.6;
    return `
<svg viewBox="0 0 200 280" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:100%">
  <defs>
    <pattern id="sp-pores" patternUnits="userSpaceOnUse" width="14" height="14">
      <circle cx="3" cy="4" r="1.2" fill="#E0B100" opacity=".6"/>
      <circle cx="9" cy="9" r="1.6" fill="#E0B100" opacity=".5"/>
      <circle cx="12" cy="2" r=".8" fill="#E0B100" opacity=".5"/>
    </pattern>
  </defs>

  <!-- BG bubbles (\u88c5\u9970) -->
  <g id="bg">
    <circle cx="20" cy="30" r="4" fill="#FFFFFF" opacity=".5"/>
    <circle cx="180" cy="50" r="3" fill="#FFFFFF" opacity=".5"/>
    <circle cx="172" cy="220" r="5" fill="#FFFFFF" opacity=".4"/>
  </g>

  <!-- LEGS (\u8154 + \u978b) -->
  <g id="legs" style="transform-origin:100px 250px;transform:scaleY(${1 + (sLegs-1)*0.3}) scaleX(${1 + (sLegs-1)*0.5})">
    <!-- left -->
    <rect x="78" y="218" width="14" height="32" fill="#FFFFFF" stroke="#0D3B4F" stroke-width="3"/>
    <ellipse cx="82" cy="262" rx="14" ry="8" fill="#1A1A1A" stroke="#0D3B4F" stroke-width="3"/>
    <!-- right -->
    <rect x="108" y="218" width="14" height="32" fill="#FFFFFF" stroke="#0D3B4F" stroke-width="3"/>
    <ellipse cx="118" cy="262" rx="14" ry="8" fill="#1A1A1A" stroke="#0D3B4F" stroke-width="3"/>
  </g>

  <!-- SHORTS (\u7ea2\u77ed\u88e4) -->
  <g id="shorts">
    <path d="M ${72 - (torsoScaleX-1)*8} 200
             L ${128 + (torsoScaleX-1)*8} 200
             L 124 224 L 104 224 L 100 210 L 96 224 L 76 224 Z"
          fill="#C9302C" stroke="#0D3B4F" stroke-width="3"/>
    <path d="M ${72 - (torsoScaleX-1)*8} 206 L ${128 + (torsoScaleX-1)*8} 206" stroke="#0D3B4F" stroke-width="2"/>
  </g>

  <!-- TORSO (\u9ec4\u6d77\u7ef5\u65b9\u5757) -->
  <g id="torso" style="transform-origin:100px 160px;transform:scaleX(${torsoScaleX})">
    <rect x="60" y="100" width="80" height="100" rx="6"
          fill="#FFD600" stroke="#0D3B4F" stroke-width="3.5"/>
    <rect x="60" y="100" width="80" height="100" rx="6" fill="url(#sp-pores)" opacity=".7"/>

    <!-- \u5185\u8863\u9886\u5b50 -->
    <path d="M 76 100 Q 100 115 124 100" fill="none" stroke="#0D3B4F" stroke-width="2.5"/>

    <!-- CHEST \u80f8\u808c -->
    <g id="chest" style="transform-origin:100px 130px;transform:scale(${sChest})">
      <ellipse cx="86" cy="130" rx="10" ry="8"
        fill="#E0B100" stroke="#0D3B4F" stroke-width="${chest>0?2.5:0}" opacity="${chest>0?1:0}"/>
      <ellipse cx="114" cy="130" rx="10" ry="8"
        fill="#E0B100" stroke="#0D3B4F" stroke-width="${chest>0?2.5:0}" opacity="${chest>0?1:0}"/>
    </g>

    <!-- ABS \u8179\u808c -->
    <g id="abs" style="transform-origin:100px 175px;transform:scale(${sAbs})">
      <g opacity="${abs>0?1:0}">
        <rect x="86" y="158" width="12" height="12" rx="2" fill="#E0B100" stroke="#0D3B4F" stroke-width="2"/>
        <rect x="102" y="158" width="12" height="12" rx="2" fill="#E0B100" stroke="#0D3B4F" stroke-width="2"/>
        <rect x="86" y="172" width="12" height="12" rx="2" fill="#E0B100" stroke="#0D3B4F" stroke-width="2"/>
        <rect x="102" y="172" width="12" height="12" rx="2" fill="#E0B100" stroke="#0D3B4F" stroke-width="2"/>
        <rect x="86" y="186" width="12" height="12" rx="2" fill="#E0B100" stroke="#0D3B4F" stroke-width="2"/>
        <rect x="102" y="186" width="12" height="12" rx="2" fill="#E0B100" stroke="#0D3B4F" stroke-width="2"/>
      </g>
    </g>
  </g>

  <!-- ARMS LEFT \u5de6\u81c2 -->
  <g id="arms-left" style="transform-origin:62px 150px;transform:scale(${sArms})">
    <ellipse cx="48" cy="150" rx="14" ry="22" fill="#FFD600" stroke="#0D3B4F" stroke-width="3"/>
    <rect x="40" y="170" width="16" height="35" rx="6" fill="#FFD600" stroke="#0D3B4F" stroke-width="3"/>
    <circle cx="48" cy="208" r="9" fill="#FFD600" stroke="#0D3B4F" stroke-width="3"/>
  </g>

  <!-- ARMS RIGHT \u53f3\u81c2 -->
  <g id="arms-right" style="transform-origin:138px 150px;transform:scale(${sArms})">
    <ellipse cx="152" cy="150" rx="14" ry="22" fill="#FFD600" stroke="#0D3B4F" stroke-width="3"/>
    <rect x="144" y="170" width="16" height="35" rx="6" fill="#FFD600" stroke="#0D3B4F" stroke-width="3"/>
    <circle cx="152" cy="208" r="9" fill="#FFD600" stroke="#0D3B4F" stroke-width="3"/>
  </g>

  <!-- SHOULDERS \u4e09\u89d2\u808c -->
  <g id="shoulders" style="transform-origin:100px 105px;transform:scale(${sSh})">
    <ellipse cx="62" cy="108" rx="12" ry="8"
      fill="#E0B100" stroke="#0D3B4F" stroke-width="${shoulders>0?2.5:0}" opacity="${shoulders>0?1:0}"/>
    <ellipse cx="138" cy="108" rx="12" ry="8"
      fill="#E0B100" stroke="#0D3B4F" stroke-width="${shoulders>0?2.5:0}" opacity="${shoulders>0?1:0}"/>
  </g>

  <!-- HEAD \uff08\u4e0d\u53d8\uff09-->
  <g id="head">
    <!-- \u773c\u775b -->
    <ellipse cx="85" cy="75" rx="9" ry="10" fill="#FFFFFF" stroke="#0D3B4F" stroke-width="2.5"/>
    <ellipse cx="115" cy="75" rx="9" ry="10" fill="#FFFFFF" stroke="#0D3B4F" stroke-width="2.5"/>
    <circle cx="85" cy="76" r="3" fill="#0D3B4F"/>
    <circle cx="115" cy="76" r="3" fill="#0D3B4F"/>
    <circle cx="86" cy="74" r="1.2" fill="#FFFFFF"/>
    <circle cx="116" cy="74" r="1.2" fill="#FFFFFF"/>
    <!-- \u775b\u6bdb -->
    <path d="M 76 64 L 94 70" stroke="#0D3B4F" stroke-width="2.5" fill="none"/>
    <path d="M 106 70 L 124 64" stroke="#0D3B4F" stroke-width="2.5" fill="none"/>
    <!-- \u5634 + \u95e8\u7259 -->
    <path d="M 80 88 Q 100 100 120 88" stroke="#0D3B4F" stroke-width="2.5" fill="#FFFFFF"/>
    <rect x="92" y="88" width="6" height="9" fill="#FFFFFF" stroke="#0D3B4F" stroke-width="1.8"/>
    <rect x="102" y="88" width="6" height="9" fill="#FFFFFF" stroke="#0D3B4F" stroke-width="1.8"/>
    <!-- \u817a\u7ea2 -->
    <circle cx="74" cy="82" r="4" fill="#FF7043" opacity=".5"/>
    <circle cx="126" cy="82" r="4" fill="#FF7043" opacity=".5"/>
  </g>
</svg>`;
  };

  // 字符 ID → 渲染函数
  const REGISTRY = {
    sponge_boy: { name: '\u6d77\u7ef5\u65b9\u5757', emoji: '\ud83e\uddfd', render: SPONGE_BOY },
  };

  function renderCharacter(charId, growth) {
    const def = REGISTRY[charId] || REGISTRY.sponge_boy;
    const g = Object.assign({arms:0,chest:0,back:0,abs:0,shoulders:0,legs:0}, growth || {});
    const lv = { arms:levelFor(g.arms), chest:levelFor(g.chest), back:levelFor(g.back),
                 abs:levelFor(g.abs), shoulders:levelFor(g.shoulders), legs:levelFor(g.legs) };
    return def.render(lv);
  }

  function listCharacters(){
    return Object.entries(REGISTRY).map(([id,v])=>({id,name:v.name,emoji:v.emoji}));
  }

  global.Characters = { renderCharacter, listCharacters, levelFor, REGISTRY };
})(window);
