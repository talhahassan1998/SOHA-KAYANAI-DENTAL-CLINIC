const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1440, height: 640 } });
  await p.goto('http://127.0.0.1:5000/', { waitUntil: 'domcontentloaded' });
  await p.waitForTimeout(600);
  const src = await p.evaluate(() => document.querySelector('video.hero-implant').src);
  // isolated harness: same clip, charcoal ground, four candidate treatments
  const opts = [
    ['none',            ''],
    ['screen',          'mix-blend-mode:screen'],
    ['invert+screen',   'filter:invert(1);mix-blend-mode:screen'],
    ['lighten',         'mix-blend-mode:lighten'],
  ];
  const cells = opts.map(([n,s]) =>
    `<div style="flex:1"><div style="color:#8FCFD6;font:12px sans-serif;padding:4px">${n}</div>
     <video src="${src}" autoplay loop muted playsinline style="width:100%;${s}"></video></div>`).join('');
  await p.setContent(`<body style="margin:0;background:#0F1416"><div style="display:flex">${cells}</div></body>`);
  await p.waitForTimeout(3000);
  await p.screenshot({ path: process.env.OUT + '/blendtest.png' });
  await b.close(); console.log('ok');
})();
