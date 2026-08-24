const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  await p.goto('http://127.0.0.1:5000/', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await p.waitForTimeout(2500);
  const out = process.env.OUT;
  for (const y of [0, 350, 700]) {
    await p.evaluate((v) => window.scrollTo(0, v), y);
    await p.waitForTimeout(900);
    await p.screenshot({ path: `${out}/v2-${y}.png` });
  }
  await b.close(); console.log('ok');
})();
