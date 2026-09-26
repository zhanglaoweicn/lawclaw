(function (w) {
  var $ = function (id) { return document.getElementById(id); };
  var fillEl, percentEl, statusEl, microEl, appEl;
  function ref() {
    fillEl = fillEl || $('sm-fill');
    percentEl = percentEl || $('sm-percent');
    statusEl = statusEl || $('sm-status');
    microEl = microEl || $('splash-micro');
    appEl = appEl || $('app');
  }
  // progress(0..100, '当前阶段文字') — 与 useAppBootstrap state.progress/statusText 对齐
  w.__lawclawSplashProgress = function (p, text) {
    ref(); if (!fillEl) return;
    var v = Math.max(0, Math.min(100, Math.round(p || 0)));
    fillEl.style.width = v + '%';
    if (percentEl) {
      percentEl.textContent = (v < 10 ? '0' : '') + v + '%';
    }
    if (statusEl && typeof text === 'string' && text && statusEl.textContent !== text) {
      statusEl.textContent = text;
      // 换文字触发淡入重放（key 机制模拟：重写 animation）
      statusEl.style.animation = 'none';
      // eslint-disable-next-line no-unused-expressions
      statusEl.offsetHeight;  /* force reflow */
      statusEl.style.animation = '';
    }
    var bar = $('sm-progress');
    if (bar) bar.setAttribute('aria-valuenow', String(v));
  };
  // enterMain() → 淡出微 Splash + 解锁 #app 可见性
  w.__hideLawClawSplash = function () {
    ref();
    if (appEl) appEl.classList.add('is-ready');
    if (microEl) {
      microEl.classList.add('is-hidden');
      microEl.setAttribute('aria-hidden', 'true');
      // 淡出完成（420ms）后从 DOM 彻底移除，释放资源
      setTimeout(function () {
        if (microEl && microEl.parentNode) microEl.parentNode.removeChild(microEl);
        var cssTag = $('critical-splash-css');
        if (cssTag && cssTag.parentNode) cssTag.parentNode.removeChild(cssTag);
        var bridgeTag = $('splash-bridge');
        if (bridgeTag && bridgeTag.parentNode) bridgeTag.parentNode.removeChild(bridgeTag);
        var preinitTag = $('theme-preinit');
        if (preinitTag && preinitTag.parentNode) { /* preinit 保留（体积很小，仅读 theme） */ }
        delete w.__lawclawSplashProgress;
        delete w.__hideLawClawSplash;
      }, 520);
    }
  };
})(window);
    
