const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  await p.goto('http://127.0.0.1:5000/', { waitUntil: 'domcontentloaded' });
  await p.waitForTimeout(1500);
  // scroll through to trigger reveal/counters
  await p.evaluate(async () => {
    for (let y = 0; y < document.body.scrollHeight; y += 400) {
      window.scrollTo(0, y); await new Promise(r => setTimeout(r, 120));
    }
    window.scrollTo(0, 0);
  });
  await p.waitForTimeout(1200);
  const out = process.env.OUT;
  for (const y of [0, 1100, 2400]) {
    await p.evaluate(v => window.scrollTo(0, v), y);
    await p.waitForTimeout(700);
    await p.screenshot({ path: `${out}/color-${y}.png` });
  }
  await b.close(); console.log('ok');
})();
