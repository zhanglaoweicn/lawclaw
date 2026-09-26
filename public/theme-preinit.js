(function () {
  try {
    var t = localStorage.getItem('lawclaw_theme');
    if (!t) {
      // 无显式偏好：跟随系统 prefers-color-scheme
      t = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    document.documentElement.setAttribute('data-theme', t === 'dark' ? 'dark' : 'light');
  } catch (e) { /* localStorage 不可达也不致命 */ }
})();
    
