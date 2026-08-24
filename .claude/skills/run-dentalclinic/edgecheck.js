const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  await p.goto('http://127.0.0.1:5000/', { waitUntil: 'domcontentloaded' });
  await p.waitForTimeout(2500);
  // sample pixels straight down through the video's bottom edge to detect a hard seam
  const box = await p.evaluate(() => {
    const r = document.querySelector('video.hero-implant').getBoundingClientRect();
    return { x: Math.round(r.x + r.width/2), top: Math.round(r.y), bottom: Math.round(r.bottom) };
  });
  console.log('video box:', JSON.stringify(box));
  await p.screenshot({ path: process.env.OUT + '/edge.png' });
  await b.close();
})();
