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

  // Vertical scrolling alone is NOT enough. The observer in
  // app/static/js/main.js uses threshold 0.1, and many .reveal cards live inside
  // horizontal scroll-snap carousels (.snap-start) — anything parked off to the
  // right never intersects, never gets .in-view, and stays at opacity:0. A
  // fullPage screenshot then shows empty sections below the hero (68 of 70
  // elements, measured). Add the class directly, exactly as the observer would.
  // [data-counter] spans have their own observer (threshold 0.4) that counts up
  // from "0" over 2.2s, so the stats band screenshots as "0+ / 0-Star" unless it
  // has both fired AND finished. Write the final values straight in.
  await page.evaluate(() => {
    document.querySelectorAll(".reveal").forEach((el) => el.classList.add("in-view"));
    document.querySelectorAll("[data-counter]").forEach((el) => {
      const target = parseFloat(el.dataset.counter);
      if (!Number.isNaN(target)) el.textContent = target.toLocaleString();
    });
  });
  await page.waitForTimeout(1200); // let the opacity/transform transitions finish
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

  // The form is a two-step Alpine.js flow (appointmentScheduler in
  // app/templates/partials/appointment_form.html): a <fieldset :disabled="!selectedDate">
  // gates every detail field until a date is picked on the calendar, and
  // preferred_date/preferred_time are sr-only inputs bound via x-model — so
  // they must be driven by clicking the widgets, not by fill()/selectOption().

  // Step 1: click the first enabled day in the calendar grid (past days and
  // Sundays render as :disabled). Availability for that date is then fetched.
  const day = page.locator(".grid.grid-cols-7 button:not([disabled]):not(.invisible)").first();
  await day.click();
  await page.waitForFunction(
    () => document.querySelector("#preferred_date")?.value,
    null,
    { timeout: 10000 },
  );

  // Step 2: fields are enabled now. Time slots are buttons; disabled ones are
  // past/closed/already-booked, so take the first that's still selectable.
  await page.fill("#full_name", "PW Smoke Patient");
  await page.fill("#email", "pwsmoke@example.com");
  await page.fill("#phone", "03001112222");
  await page.selectOption("#service", { index: 1 });

  // Gender is required and is also a button group bound to a hidden input.
  await page.getByRole("button", { name: "Female", exact: true }).click();

  const slot = page.locator("button:not([disabled])", { hasText: /^\d{1,2}:\d{2} (am|pm)$/i }).first();
  await slot.click();
  await page.waitForFunction(
    () => document.querySelector("#preferred_time")?.value,
    null,
    { timeout: 10000 },
  );

  await page.screenshot({ path: path.join(OUT, "02b-book-filled.png"), fullPage: true });

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
