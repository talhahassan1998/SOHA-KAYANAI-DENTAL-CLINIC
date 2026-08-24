const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  await p.goto('http://127.0.0.1:5000/', { waitUntil: 'domcontentloaded' });
  await p.waitForTimeout(3000);
  const st = await p.evaluate(() => {
    const v = document.querySelector('video.hero-implant');
    if (!v) return 'MISSING';
    return { paused: v.paused, t1: v.currentTime, w: v.videoWidth, h: v.videoHeight, err: v.error && v.error.code };
  });
  console.log('state:', JSON.stringify(st));
  await p.waitForTimeout(1800);
  const t2 = await p.evaluate(() => document.querySelector('video.hero-implant').currentTime);
  console.log('currentTime advanced to:', t2);
  await p.screenshot({ path: process.env.OUT + '/vid-0.png' });
  await b.close();
})();
