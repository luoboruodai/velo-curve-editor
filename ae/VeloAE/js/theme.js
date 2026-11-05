(function () {
  'use strict';

  const root = document.documentElement;

  function setToken(name, value) {
    if (root.style.getPropertyValue(name) !== value) root.style.setProperty(name, value);
  }

  function mixColor(background, accent, amount) {
    function rgb(hex) { return [1, 3, 5].map((offset) => parseInt(hex.slice(offset, offset + 2), 16)); }
    const a = rgb(background), b = rgb(accent);
    return `rgb(${a.map((value, index) => Math.round(value + (b[index] - value) * amount)).join(',')})`;
  }

  function apply(settings) {
    setToken('--btn-active-bg', settings.themeColor);
    setToken('--accent-soft', `${settings.themeColor}80`);
    setToken('--btn-active-hover-bg', mixColor(settings.themeColor, '#000000', 0.1));
    setToken('--curve-color', settings.themeColor);
    setToken('--panel-bg', settings.themeBackground);
  }

  window.VeloTheme = { apply };
}());
