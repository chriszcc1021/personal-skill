// peeps.js — SVG 角色渲染（从 base.html 抽出，加 6 部位生长）
// renderAvatar(config, growth) -> SVG 字符串
// config = {gender, hair, glasses, nose, mouth, shorts}
// growth = {arms, chest, back, abs, shoulders, legs}  每项是打卡次数

(function (global) {
  const HAIR = {
    bald:   ``,
    buzz:   `<path d="M70 50 Q100 26 130 50" />
             <path d="M74 48 L74 44 M82 44 L82 40 M90 42 L90 38 M100 40 L100 36
                      M110 42 L110 38 M118 44 L118 40 M126 48 L126 44" stroke-width="1.6"/>`,
    medium: `<path d="M68 56 Q70 28 100 28 Q130 28 132 56 Q126 44 116 44
                      Q110 34 100 36 Q90 34 84 44 Q74 44 68 56 Z" fill="#1a1a1a"/>`,
    long:   `<path d="M66 70 Q60 30 100 26 Q140 30 134 70 L130 66 Q132 44 100 38
                      Q68 44 70 66 Z" fill="#1a1a1a"/>`,
    short_f:  `<path d="M66 60 Q66 28 100 28 Q134 28 134 60 Q128 50 118 48
                        Q108 38 100 40 Q92 38 82 48 Q72 50 66 60 Z" fill="#1a1a1a"/>
               <path d="M72 60 Q70 74 78 78" fill="#1a1a1a"/>
               <path d="M128 60 Q130 74 122 78" fill="#1a1a1a"/>`,
    ponytail: `<path d="M68 56 Q70 26 100 26 Q130 26 132 56 Q120 44 100 44
                        Q80 44 68 56 Z" fill="#1a1a1a"/>
               <path d="M130 50 Q150 70 142 100 Q138 80 128 70" fill="#1a1a1a"/>`,
    twin_braid:`<path d="M68 56 Q70 26 100 26 Q130 26 132 56 Q118 46 100 46
                        Q82 46 68 56 Z" fill="#1a1a1a"/>
               <path d="M66 72 Q56 92 60 112 Q72 100 70 80 Z" fill="#1a1a1a"/>
               <path d="M134 72 Q144 92 140 112 Q128 100 130 80 Z" fill="#1a1a1a"/>
               <circle cx="60" cy="112" r="3" fill="#1a1a1a" stroke="none"/>
               <circle cx="140" cy="112" r="3" fill="#1a1a1a" stroke="none"/>`,
    long_curl: `<path d="M62 60 Q60 24 100 24 Q140 24 138 60
                        Q142 100 132 130 Q126 110 130 84
                        Q118 50 100 46 Q82 50 70 84
                        Q74 110 68 130 Q58 100 62 60 Z" fill="#1a1a1a"/>`,
  };
  const GLASSES = {
    none: ``,
    round:  `<circle cx="88" cy="62" r="7" /><circle cx="112" cy="62" r="7" /><path d="M95 62 L105 62" />`,
    square: `<rect x="80" y="55" width="16" height="14" rx="2" /><rect x="104" y="55" width="16" height="14" rx="2" /><path d="M96 62 L104 62" />`,
    shades: `<rect x="80" y="55" width="16" height="12" rx="2" fill="#1a1a1a"/><rect x="104" y="55" width="16" height="12" rx="2" fill="#1a1a1a"/><path d="M96 61 L104 61" />`,
  };
  const NOSE = {
    small_round: `<circle cx="100" cy="72" r="2.4" />`,
    triangle:    `<path d="M100 64 L94 76 L106 76 Z" />`,
    big:         `<path d="M96 64 Q92 76 100 78 Q108 76 104 64" />
                  <circle cx="97" cy="76" r="1.2" fill="#1a1a1a" stroke="none"/>
                  <circle cx="103" cy="76" r="1.2" fill="#1a1a1a" stroke="none"/>`,
  };
  const MOUTH = {
    smile:       `<path d="M90 84 Q100 92 110 84" />`,
    laugh_teeth: `<path d="M88 82 Q100 96 112 82 Z" fill="#fff"/>
                  <path d="M92 86 L108 86" />
                  <path d="M96 82 L96 90 M100 82 L100 90 M104 82 L104 90" stroke-width="1.4"/>`,
    pursed:      `<path d="M94 86 L106 86" />`,
    tongue:      `<path d="M90 82 Q100 92 110 82" />
                  <path d="M96 88 Q100 96 104 88 Z" fill="#e76f51"/>`,
  };
  const SHORTS = {
    classic:  `<path d="M68 198 L132 198 L130 230 L102 230 L100 210 L98 230 L70 230 Z" fill="#2b6cb0"/>
               <path d="M68 204 L132 204" />`,
    tight:    `<path d="M70 198 L130 198 L128 244 L102 244 L100 210 L98 244 L72 244 Z" fill="#1a1a1a"/>`,
    fifth:    `<path d="M68 198 L132 198 L132 250 L102 250 L100 210 L98 250 L68 250 Z" fill="#777"/>
               <path d="M68 206 L132 206" />`,
    beach:    `<path d="M66 198 L134 198 L132 234 L102 234 L100 210 L98 234 L68 234 Z" fill="#ffd166"/>
               <path d="M72 210 q4 6 8 0 M86 218 q4 6 8 0 M104 212 q4 6 8 0 M118 220 q4 6 8 0" stroke="#e76f51"/>`,
  };
  const HAIR_MALE = [['bald','光头'], ['buzz','寸头'], ['medium','中长'], ['long','长发']];
  const HAIR_FEMALE = [['short_f','短发'], ['ponytail','马尾'], ['twin_braid','双麻花'], ['long_curl','长卷']];
  const OPTS = {
    gender:  [['male','男'], ['female','女']],
    glasses: [['none','无眼镜'], ['round','圆框'], ['square','方框'], ['shades','墨镜']],
    nose:    [['small_round','小圆鼻'], ['triangle','三角鼻'], ['big','大鼻']],
    mouth:   [['smile','微笑'], ['laugh_teeth','大笑露牙'], ['pursed','抿嘴'], ['tongue','吐舌']],
    shorts:  [['classic','经典运动短裤'], ['tight','紧身裤'], ['fifth','五分裤'], ['beach','沙滩花裤']],
  };
  const PART_LABEL = {
    arms: '手臂 💪', chest: '胸肌 🫁', back: '后背 🦴', abs: '腹肌 🧱', shoulders: '肩膀 🪨', legs: '腿 🦵',
  };

  // 单部位生长等级：0..4
  function levelFor(count) {
    if (!count) return 0;
    if (count < 5)  return 0;
    if (count < 10) return 1;
    if (count < 20) return 2;
    if (count < 30) return 3;
    return 4;
  }
  // 等级对应 scale 因子（用来放大鼓包椭圆 / 描边 / 躯干宽度）
  const SCALES = [1.0, 1.2, 1.5, 1.8, 2.2];

  function renderAvatar(config, growth) {
    const c = Object.assign({ gender:'male', hair:'buzz', glasses:'none',
                              nose:'small_round', mouth:'smile', shorts:'classic' }, config || {});
    const g = Object.assign({ arms:0, chest:0, back:0, abs:0, shoulders:0, legs:0 }, growth || {});
    const Larms = levelFor(g.arms), Lchest = levelFor(g.chest), Lback = levelFor(g.back);
    const Labs = levelFor(g.abs), Lshoulders = levelFor(g.shoulders), Llegs = levelFor(g.legs);

    // 躯干宽度：back 让躯干变宽（向两边各扩 dx）
    const backDx = (SCALES[Lback] - 1) * 18; // 0..21.6
    const leftX = 70 - backDx, rightX = 130 + backDx;
    const torsoTopLeft = `${leftX} 120`, torsoTopRight = `${rightX} 120`;
    const torsoBotLeft = `${leftX} 198`, torsoBotRight = `${rightX} 198`;
    const torsoPath = `M${leftX} 120 Q${leftX} 100 100 100 Q${rightX/1+0} 100 ${rightX} 120 L${rightX} 198 L${leftX} 198 Z`;

    // arms：双臂描边 + bicep 鼓包椭圆
    const armSW = 2.4 + Larms * 1.6; // 2.4..8.8
    const bicepRX = 6 + Larms * 4;    // 6..22
    const bicepRY = 10 + Larms * 4;
    const armsBlobs = Larms > 0 ? `
      <ellipse cx="${leftX - 8}" cy="150" rx="${bicepRX}" ry="${bicepRY}" fill="#f4c79a"/>
      <ellipse cx="${rightX + 8}" cy="150" rx="${bicepRX}" ry="${bicepRY}" fill="#f4c79a"/>` : '';
    const armsForearmBlob = Larms >= 2 ? `
      <ellipse cx="${leftX - 12}" cy="180" rx="${5 + Larms*2}" ry="${8 + Larms*2}" fill="#f4c79a"/>
      <ellipse cx="${rightX + 12}" cy="180" rx="${5 + Larms*2}" ry="${8 + Larms*2}" fill="#f4c79a"/>` : '';

    // chest：pec 椭圆，跟随 back 宽度
    const pecRX = 10 + Lchest * 5;
    const pecRY = 8 + Lchest * 4;
    const pecLX = (leftX + 100)/2;
    const pecRX2 = (rightX + 100)/2;
    const chestBlobs = Lchest > 0 ? `
      <ellipse cx="${pecLX}" cy="135" rx="${pecRX}" ry="${pecRY}" fill="#f4c79a" stroke-width="${1.6 + Lchest*0.4}"/>
      <ellipse cx="${pecRX2}" cy="135" rx="${pecRX}" ry="${pecRY}" fill="#f4c79a" stroke-width="${1.6 + Lchest*0.4}"/>` : '';

    // shoulders：三角肌
    const shRX = 6 + Lshoulders * 5;
    const shRY = 6 + Lshoulders * 3;
    const shoulderBlobs = Lshoulders > 0 ? `
      <ellipse cx="${leftX + 2}" cy="122" rx="${shRX}" ry="${shRY}" fill="#f4c79a"/>
      <ellipse cx="${rightX - 2}" cy="122" rx="${shRX}" ry="${shRY}" fill="#f4c79a"/>` : '';

    // abs：6 块腹肌（覆盖在躯干上）
    let absBlocks = '';
    if (Labs > 0) {
      const absRX = 5 + Labs * 1.8;
      const absRY = 4 + Labs * 1.2;
      const rows = [158, 170, 182];
      for (const y of rows) {
        absBlocks += `<ellipse cx="${100 - 7}" cy="${y}" rx="${absRX}" ry="${absRY}" fill="#f4c79a" stroke-width="${1.4 + Labs*0.3}"/>`;
        absBlocks += `<ellipse cx="${100 + 7}" cy="${y}" rx="${absRX}" ry="${absRY}" fill="#f4c79a" stroke-width="${1.4 + Labs*0.3}"/>`;
      }
    }

    // legs：描边粗 + 大腿椭圆
    const legSW = 2.4 + Llegs * 1.8;
    const thighRX = 5 + Llegs * 4;
    const thighRY = 18 + Llegs * 6;
    const legsBlobs = Llegs > 0 ? `
      <ellipse cx="80" cy="220" rx="${thighRX}" ry="${thighRY}" fill="#f4c79a"/>
      <ellipse cx="120" cy="220" rx="${thighRX}" ry="${thighRY}" fill="#f4c79a"/>` : '';

    const svg = `
<svg viewBox="0 0 200 270" xmlns="http://www.w3.org/2000/svg"
     fill="none" stroke="#1a1a1a" stroke-width="2.4"
     stroke-linecap="round" stroke-linejoin="round" style="width:100%;height:100%">
  <!-- LEGS -->
  <g stroke-width="${legSW}">
    ${legsBlobs}
    <path d="M82 198 L78 250" />
    <path d="M118 198 L122 250" />
    <path d="M70 250 L88 250" />
    <path d="M112 250 L130 250" />
  </g>
  <!-- SHORTS -->
  <g>${SHORTS[c.shorts] || ''}</g>
  <!-- TORSO -->
  <g>
    <path d="${torsoPath}" fill="#f4c79a"/>
    <path d="M${leftX+8} 115 Q100 122 ${rightX-8} 115" />
    <path d="M100 122 L100 150" />
    ${chestBlobs}
    <path d="M${leftX+8} 122 Q90 142 100 150" />
    <path d="M${rightX-8} 122 Q110 142 100 150" />
    <path d="M100 150 L100 188" />
    ${Labs === 0 ? `
      <path d="M88 158 L112 158" />
      <path d="M86 170 L114 170" />
      <path d="M86 182 L114 182" />` : absBlocks}
  </g>
  <!-- ARMS -->
  <g stroke-width="${armSW}">
    <path d="M${leftX} 122 Q${leftX-14} 150 ${leftX-10} 188" fill="#f4c79a"/>
    <path d="M${rightX} 122 Q${rightX+14} 150 ${rightX+10} 188" fill="#f4c79a"/>
    ${armsBlobs}
    ${armsForearmBlob}
    <circle cx="${leftX-12}" cy="192" r="${6 + Larms*1.5}" fill="#f4c79a"/>
    <circle cx="${rightX+12}" cy="192" r="${6 + Larms*1.5}" fill="#f4c79a"/>
  </g>
  <!-- SHOULDERS overlay -->
  <g>${shoulderBlobs}</g>
  <!-- NECK -->
  <path d="M92 90 L92 102 M108 90 L108 102" />
  <!-- HEAD -->
  <g>
    <ellipse cx="100" cy="62" rx="32" ry="34" fill="#f4c79a"/>
    <path d="M68 62 Q62 64 64 72" fill="#f4c79a"/>
    <path d="M132 62 Q138 64 136 72" fill="#f4c79a"/>
    <circle cx="88" cy="62" r="2" fill="#1a1a1a" stroke="none"/>
    <circle cx="112" cy="62" r="2" fill="#1a1a1a" stroke="none"/>
    <path d="M82 54 L94 54" />
    <path d="M106 54 L118 54" />
  </g>
  <g>${NOSE[c.nose] || ''}</g>
  <g>${MOUTH[c.mouth] || ''}</g>
  <g>${HAIR[c.hair] || ''}</g>
  <g>${GLASSES[c.glasses] || ''}</g>
</svg>`;
    return svg;
  }

  global.Peeps = {
    renderAvatar,
    levelFor,
    OPTS,
    HAIR_MALE,
    HAIR_FEMALE,
    PART_LABEL,
    PARTS: ['arms','chest','back','abs','shoulders','legs'],
  };
})(window);
