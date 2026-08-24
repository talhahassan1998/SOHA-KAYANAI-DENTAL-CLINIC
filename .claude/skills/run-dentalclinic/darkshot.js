const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  await p.goto('http://127.0.0.1:5000/', { waitUntil: 'domcontentloaded' });
  await p.waitForTimeout(800);
  await p.evaluate(() => {
    localStorage.setItem('theme', 'dark');
    document.documentElement.classList.add('dark');
  });
  await p.waitForTimeout(1200);
  const out = process.env.OUT;
  await p.screenshot({ path: out + '/dark-0.png' });
  await p.evaluate(() => window.scrollTo(0, 1100));
  await p.waitForTimeout(800);
  await p.screenshot({ path: out + '/dark-1100.png' });
  await b.close(); console.log('ok');
})();
