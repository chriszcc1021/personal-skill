// nav.js — 注入顶部导航
(function () {
  function renderNav(active) {
    const tabs = [
      ['index.html', '首页'],
      ['checkin.html', '打卡'],
      ['ledger.html', '账本'],
      ['onboard.html', '加成员'],
      ['settings.html', '设置'],
    ];
    const html = `
      <nav class="nav">
        <a class="brand" href="index.html">💪 肌肉基金</a>
        ${tabs.map(([h,l]) => `<a class="tab ${active===h?'active':''}" href="${h}">${l}</a>`).join('')}
      </nav>`;
    document.body.insertAdjacentHTML('afterbegin', html);
  }
  window.MFNav = { renderNav };
})();
