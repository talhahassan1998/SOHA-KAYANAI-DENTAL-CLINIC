const { chromium } = require('playwright');
(async () => {
  const url = process.env.URL || 'http://127.0.0.1:5000/';
  const out = process.env.SHOT || '/tmp/shots2/hero.png';
  const full = process.env.FULL === '1';
  const dark = process.env.DARK === '1';
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  if (dark) { await p.addInitScript(() => localStorage.setItem('darkMode','true')); }
  await p.goto(url, { waitUntil: 'networkidle' });
  if (full) { for (let y=0;y<12000;y+=400){ await p.mouse.wheel(0,400); await p.waitForTimeout(45);} await p.evaluate(()=>window.scrollTo(0,0)); await p.waitForTimeout(600); }
  await p.waitForTimeout(1000);
  await p.screenshot({ path: out, fullPage: full });
  await b.close();
  console.log('shot ->', out);
})();
