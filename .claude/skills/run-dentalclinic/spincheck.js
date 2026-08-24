const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  await p.goto('http://127.0.0.1:5000/', { waitUntil: 'domcontentloaded' });
  await p.waitForTimeout(800);
  const out = process.env.OUT;
  // sample the rotation matrix over time to prove it's actually animating
  for (let i = 0; i < 3; i++) {
    const t = await p.evaluate(() => {
      const el = document.querySelector('.hero-spin');
      return el ? getComputedStyle(el).transform : 'MISSING';
    });
    console.log('transform:', t);
    await p.waitForTimeout(1600);
  }
  await p.screenshot({ path: out + '/spin.png' });
  await b.close();
})();
