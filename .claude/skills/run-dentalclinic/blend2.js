const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1200, height: 500 } });
  await p.goto('http://127.0.0.1:5000/', { waitUntil: 'domcontentloaded' });
  const src = await p.evaluate(() => document.querySelector('video.hero-implant').src);
  // A: video directly on dark bg. B: video inside a transformed wrapper (like sticky).
  await p.setContent(`<body style="margin:0;background:#0F1416;display:flex">
    <div style="flex:1"><div style="color:#8FCFD6;font:12px sans-serif">A: plain parent</div>
      <video src="${src}" autoplay loop muted playsinline style="width:100%;mix-blend-mode:screen"></video></div>
    <div style="flex:1"><div style="color:#8FCFD6;font:12px sans-serif">B: transformed parent</div>
      <div style="transform:translate3d(0,0,0);will-change:transform">
      <video src="${src}" autoplay loop muted playsinline style="width:100%;mix-blend-mode:screen"></video></div></div>
    <div style="flex:1"><div style="color:#8FCFD6;font:12px sans-serif">C: transformed + bg</div>
      <div style="transform:translate3d(0,0,0);will-change:transform;background:#0F1416">
      <video src="${src}" autoplay loop muted playsinline style="width:100%;mix-blend-mode:screen"></video></div></div>
  </body>`);
  await p.waitForTimeout(3000);
  await p.screenshot({ path: process.env.OUT + '/blend2.png' });
  await b.close(); console.log('ok');
})();
