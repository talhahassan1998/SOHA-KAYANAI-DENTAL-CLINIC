const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  await p.goto('http://127.0.0.1:5000/', { waitUntil: 'domcontentloaded' });
  await p.evaluate(() => document.documentElement.classList.add('dark'));
  await p.waitForTimeout(1000);
  console.log(JSON.stringify(await p.evaluate(() => {
    const v = document.querySelector('video.hero-implant');
    const w = document.querySelector('.hero-implant-shift');
    const cs = getComputedStyle(v);
    return {
      htmlHasDark: document.documentElement.classList.contains('dark'),
      videoClasses: v.className,
      blend: cs.mixBlendMode,
      filter: cs.filter,
      wrapperBg: getComputedStyle(w).backgroundColor,
      cssHasScreen: [...document.styleSheets].some(s => { try { return [...s.cssRules].some(r => r.cssText.includes('hero-video')); } catch(e){ return false; } }),
    };
  }), null, 2));
  await b.close();
})();
