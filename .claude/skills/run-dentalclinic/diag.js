const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  await p.goto('http://127.0.0.1:5000/', { waitUntil: 'domcontentloaded' });
  await p.waitForTimeout(1500);
  const info = await p.evaluate(() => {
    const el = document.querySelector('.hero-implant-shift');
    if (!el) return 'NO ELEMENT';
    const track = el.parentElement;
    const clippers = [];
    for (let n = el.parentElement; n && n !== document.documentElement; n = n.parentElement) {
      const cs = getComputedStyle(n);
      if (cs.overflow !== 'visible' || cs.overflowX !== 'visible' || cs.overflowY !== 'visible')
        clippers.push(`${n.tagName}.${n.className}`.slice(0,90) + ` -> ${cs.overflow}/${cs.overflowX}/${cs.overflowY}`);
    }
    const cs = getComputedStyle(el);
    return {
      position: cs.position, top: cs.top,
      trackH: track.getBoundingClientRect().height.toFixed(0),
      elH: el.getBoundingClientRect().height.toFixed(0),
      clippers,
      htmlOverflow: getComputedStyle(document.documentElement).overflow,
      bodyOverflow: getComputedStyle(document.body).overflow,
    };
  });
  console.log(JSON.stringify(info, null, 2));
  await b.close();
})();
