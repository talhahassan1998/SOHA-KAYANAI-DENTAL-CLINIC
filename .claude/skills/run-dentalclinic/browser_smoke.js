// Playwright driver: proves the server-rendered booking flow works in a
// real browser (form fill -> CSRF POST -> redirect to confirmation page)
// and screenshots the home page.
//
// Requires the `playwright` npm package + a chromium browser installed
// once (see SKILL.md "Setup" for the exact commands). Run with the
// server already up (see smoke.sh), e.g.:
//   node .claude/skills/run-dentalclinic/browser_smoke.js
//
// Env vars: BASE (default http://127.0.0.1:5000), OUT (screenshot dir,
// default ./shots next to this file).
const path = require("path");
const fs = require("fs");
const { chromium } = require("playwright");

const BASE = process.env.BASE || "http://127.0.0.1:5000";
const OUT = process.env.OUT || path.join(__dirname, "shots");

// .reveal / [data-counter] elements only animate in when an
// IntersectionObserver (app/static/js/main.js) sees them scroll into
// view — a fullPage screenshot taken without scrolling first captures
// them still at their initial opacity-0 / "0+" state.
async function scrollThrough(page) {
  await page.evaluate(async () => {
    const step = 400;
    for (let y = 0; y < document.body.scrollHeight; y += step) {
      window.scrollTo(0, y);
      await new Promise((r) => setTimeout(r, 120));
    }
    window.scrollTo(0, 0);
  });
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage();

  await page.goto(`${BASE}/`);
  await scrollThrough(page);
  await page.screenshot({ path: path.join(OUT, "01-home.png"), fullPage: true });
  console.log("home title:", await page.title());

  // NOTE: /book-appointment has NO trailing slash (unlike /services/,
  // /doctors/, /blog/, ... which redirect 308 without one) — see Gotchas.
  await page.goto(`${BASE}/book-appointment`);
  await page.waitForSelector("form");
  await page.screenshot({ path: path.join(OUT, "02-book-form.png"), fullPage: true });

  await page.fill("#full_name", "PW Smoke Patient");
  await page.fill("#email", "pwsmoke@example.com");
  await page.fill("#phone", "03001112222");
  await page.selectOption("#service", { index: 1 });
  const date = new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10);
  await page.fill("#preferred_date", date);
  await page.selectOption("#preferred_time", { index: 1 });

  await page.click("button[type=submit]");
  await page.waitForLoadState("networkidle");
  await page.screenshot({ path: path.join(OUT, "03-book-result.png"), fullPage: true });
  console.log("after submit url:", page.url());
  console.log("after submit title:", await page.title());

  const bodyText = await page.textContent("body");
  const ok = /thank you|confirm|received/i.test(bodyText) && page.url().includes("/confirmation/");
  console.log(ok ? "PASS: booking flow reached confirmation page" : "FAIL: did not reach confirmation page");

  await browser.close();
  process.exit(ok ? 0 : 1);
})();
