// test.js — 跑 state.js / peeps.js 的核心逻辑
const fs = require('fs');
const path = require('path');

// fake window + localStorage
const store = {};
global.localStorage = {
  getItem: (k) => store[k] || null,
  setItem: (k, v) => { store[k] = v; },
  removeItem: (k) => { delete store[k]; },
};
global.window = global;
global.document = { createElement: () => ({ click: ()=>{} }) };
global.Blob = function() {}; global.URL = { createObjectURL: ()=>'', revokeObjectURL: ()=>{} };

eval(fs.readFileSync(path.join(__dirname, 'peeps.js'), 'utf8'));
eval(fs.readFileSync(path.join(__dirname, 'state.js'), 'utf8'));

function assert(cond, msg) {
  if (!cond) { console.error('❌', msg); process.exit(1); }
  console.log('✅', msg);
}

// 1. 加 3 个成员
const m1 = MF.addMember({ name: '张三', avatar:{ gender:'male', hair:'buzz' }});
const m2 = MF.addMember({ name: '李四', avatar:{ gender:'male', hair:'medium' }});
const m3 = MF.addMember({ name: '王五', avatar:{ gender:'female', hair:'ponytail' }});
let s = MF.getState();
assert(s.members.length === 3, '加 3 成员');

// 2. 模拟手臂打卡 30 次
for (let i = 0; i < 30; i++) {
  // 直接改 state，模拟历史
  s = MF.getState();
  const m = s.members.find(x => x.id === m1.id);
  m.growth.arms = (m.growth.arms||0) + 1;
  MF.saveState(s);
}
s = MF.getState();
const lvl = Peeps.levelFor(s.members.find(x=>x.id===m1.id).growth.arms);
assert(lvl === 4, `手臂 30 次 → level 4，实际 ${lvl}`);

// 3. SVG 渲染含 arms 鼓包
const svg = Peeps.renderAvatar(m1.avatar, { arms: 30 });
assert(svg.includes('<ellipse'), 'svg 含 ellipse 鼓包');
assert(svg.length > 1000, 'svg 不为空');

// 4. 模拟"上周缺勤 3 天" → settleOverdue
// 把成员 createdAt 改到 14 天前，lastSettleDate 也改到 14 天前
const past = new Date(); past.setDate(past.getDate() - 14);
const pastIso = past.toISOString().slice(0,10);
s = MF.getState();
for (const m of s.members) { m.createdAt = pastIso; m.lastSettleDate = pastIso; m.debt = 0; }
s.fundTotal = 0;
MF.saveState(s);
MF.settleOverdue();
s = MF.getState();
console.log('结算后 fundTotal =', s.fundTotal, '罚款 =', s.settings.fineAmount);
assert(s.fundTotal > 0, 'settleOverdue 产生欠款');
// 14 天里大约 10 个工作日（去掉昨天前），3 个人 → fundTotal 应该 > 0 且是 fineAmount 的整数倍
assert(s.fundTotal % s.settings.fineAmount === 0, 'fundTotal 是 fineAmount 整数倍');

// 5. checkin 测试
s = MF.getState();
const r = MF.checkin(m2.id, ['chest', 'abs']);
assert(r.ok, '打卡成功');
s = MF.getState();
const m2new = s.members.find(x => x.id === m2.id);
assert(m2new.growth.chest === 1 && m2new.growth.abs === 1, '生长+1');
const r2 = MF.checkin(m2.id, ['legs']);
assert(!r2.ok, '同一天不能重复打');

// 6. levelFor 边界
assert(Peeps.levelFor(0) === 0, 'level(0)=0');
assert(Peeps.levelFor(4) === 0, 'level(4)=0');
assert(Peeps.levelFor(5) === 1, 'level(5)=1');
assert(Peeps.levelFor(10) === 2, 'level(10)=2');
assert(Peeps.levelFor(20) === 3, 'level(20)=3');
assert(Peeps.levelFor(30) === 4, 'level(30)=4');

console.log('\n🎉 全部通过');
