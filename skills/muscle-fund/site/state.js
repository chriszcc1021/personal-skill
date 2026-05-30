// state.js — localStorage 状态 + 结算 + 导入导出
(function (global) {
  const KEY = 'mf_state_v1';
  const DEFAULT_STATE = {
    members: [], // {id, name, avatar:{gender,hair,glasses,nose,mouth,shorts}, growth:{arms,chest,back,abs,shoulders,legs}, checkins:{[YYYY-MM-DD]:[parts]}, debt:0, lastSettleDate:null, createdAt}
    settings: { fineAmount: 30, currency: '¥', startDate: null },
    fundTotal: 0,
  };

  function getState() {
    try {
      const raw = localStorage.getItem(KEY);
      if (!raw) return JSON.parse(JSON.stringify(DEFAULT_STATE));
      const s = JSON.parse(raw);
      // 兜底 merge
      s.settings = Object.assign({}, DEFAULT_STATE.settings, s.settings || {});
      s.members = s.members || [];
      s.fundTotal = s.fundTotal || 0;
      return s;
    } catch (e) {
      console.error('getState failed', e);
      return JSON.parse(JSON.stringify(DEFAULT_STATE));
    }
  }
  function saveState(s) { localStorage.setItem(KEY, JSON.stringify(s)); }

  function uid() { return 'm_' + Math.random().toString(36).slice(2, 10); }
  function todayStr() {
    const d = new Date();
    const tz = d.getTimezoneOffset();
    const local = new Date(d.getTime() - tz*60000);
    return local.toISOString().slice(0,10);
  }
  function isoOf(d) {
    const tz = d.getTimezoneOffset();
    const local = new Date(d.getTime() - tz*60000);
    return local.toISOString().slice(0,10);
  }

  function addMember(m) {
    const s = getState();
    const today = todayStr();
    const member = {
      id: uid(),
      name: m.name || '匿名',
      avatar: m.avatar || {},
      growth: { arms:0, chest:0, back:0, abs:0, shoulders:0, legs:0 },
      checkins: {},
      debt: 0,
      lastSettleDate: today, // 加入当天起算
      createdAt: today,
    };
    s.members.push(member);
    if (!s.settings.startDate) s.settings.startDate = today;
    saveState(s);
    return member;
  }

  function removeMember(id) {
    const s = getState();
    s.members = s.members.filter(m => m.id !== id);
    saveState(s);
  }

  function checkin(memberId, parts) {
    const s = getState();
    const m = s.members.find(x => x.id === memberId);
    if (!m) return { ok:false, msg:'成员不存在' };
    const today = todayStr();
    if (m.checkins[today] && m.checkins[today].length) {
      return { ok:false, msg:'今天已经打过卡了' };
    }
    m.checkins[today] = parts.slice();
    for (const p of parts) {
      m.growth[p] = (m.growth[p] || 0) + 1;
    }
    saveState(s);
    return { ok:true };
  }

  // 工作日缺勤结算：从 lastSettleDate 次日到昨天，找工作日缺勤
  function settleOverdue() {
    const s = getState();
    const today = todayStr();
    const yesterday = new Date(); yesterday.setDate(yesterday.getDate() - 1);
    const yIso = isoOf(yesterday);
    for (const m of s.members) {
      let cursor = m.lastSettleDate || m.createdAt;
      // cursor 已结算到这一天，从次日开始检查
      const start = new Date(cursor + 'T00:00:00');
      start.setDate(start.getDate() + 1);
      const end = new Date(yIso + 'T00:00:00');
      let d = new Date(start);
      while (d <= end) {
        const dow = d.getDay(); // 0=Sun,1=Mon..6=Sat
        if (dow >= 1 && dow <= 5) {
          const iso = isoOf(d);
          if (!m.checkins[iso] || m.checkins[iso].length === 0) {
            m.debt += s.settings.fineAmount;
            m.missDays = (m.missDays||0) + 1;
            s.fundTotal += s.settings.fineAmount;
          }
        }
        d.setDate(d.getDate() + 1);
      }
      m.lastSettleDate = yIso;
    }
    saveState(s);
    return s;
  }

  function totalCheckinDays(m) { return Object.keys(m.checkins || {}).length; }
  function currentMonthDebt(m, fineAmount) {
    // 估算：本月工作日 - 本月已打卡日 - 还没到的日子
    const now = new Date();
    const y = now.getFullYear(), mo = now.getMonth();
    const today = now.getDate();
    let missed = 0;
    for (let day = 1; day <= today; day++) {
      const d = new Date(y, mo, day);
      const dow = d.getDay();
      if (dow >= 1 && dow <= 5) {
        const iso = isoOf(d);
        const created = m.createdAt || iso;
        if (iso < created) continue;
        if (!m.checkins[iso] || m.checkins[iso].length === 0) missed++;
      }
    }
    // 今天还没结束，先不算今天
    const todayIso = isoOf(now);
    if (!m.checkins[todayIso] && now.getDay() >= 1 && now.getDay() <= 5) missed -= 1;
    if (missed < 0) missed = 0;
    return missed * fineAmount;
  }

  function exportCSV() {
    const s = getState();
    const lines = ['姓名,累计打卡天数,累计欠款,本月欠款(估算)'];
    for (const m of s.members) {
      const d = totalCheckinDays(m);
      const cur = currentMonthDebt(m, s.settings.fineAmount);
      lines.push(`${m.name},${d},${m.debt},${cur}`);
    }
    const csv = '\uFEFF' + lines.join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'muscle-fund-ledger.csv';
    a.click(); URL.revokeObjectURL(url);
  }

  function exportJSON() {
    const s = getState();
    const blob = new Blob([JSON.stringify(s, null, 2)], { type:'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'muscle-fund-backup.json';
    a.click(); URL.revokeObjectURL(url);
  }

  function importJSON(text) {
    try {
      const s = JSON.parse(text);
      if (!s.members) throw new Error('格式错误：缺 members');
      saveState(s);
      return { ok:true };
    } catch (e) { return { ok:false, msg:String(e) }; }
  }

  const USER_KEY = 'mf_current_user';
  function getCurrentUserId(){ try{return localStorage.getItem(USER_KEY)||null}catch(e){return null} }
  function setCurrentUserId(id){ if(id) localStorage.setItem(USER_KEY,id); else localStorage.removeItem(USER_KEY); }
  function login(name){
    const s=getState();
    const m=s.members.find(x=>x.name===name.trim());
    if(!m) return {ok:false,msg:'名字不在基金成员里，先在设置里加一下'};
    setCurrentUserId(m.id);
    return {ok:true,member:m};
  }
  function logout(){ setCurrentUserId(null); }

  function replaceState(s){ if(!s||!s.members) throw new Error('bad'); saveState(s); }
  const api = {
    getState, saveState, replaceState, addMember, removeMember,
    checkin, settleOverdue, todayStr,
    totalCheckinDays, currentMonthDebt,
    exportCSV, exportJSON, importJSON,
    getCurrentUserId, setCurrentUserId, login, logout,
  };
  global.MF = api;
  global.MFState = api;
})(window);
