// Visual verification for the 3D/depth redesign.
// Captures each page in light + dark at desktop/tablet/mobile, and asserts the
// transform-layer convention (see style.css) is not violated anywhere.
//
//   node .claude/skills/run-dentalclinic/redesign_shots.js
//   BASE=http://127.0.0.1:5000 OUT=./shots node ... redesign_shots.js

const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");

const BASE = process.env.BASE || "http://127.0.0.1:5000";
const OUT = process.env.OUT || path.join(__dirname, "shots-redesign");

const PAGES = [
  ["home", "/"],
  ["services", "/services/"],
  ["service-detail", "/services/dental-implants"],
  ["doctors", "/doctors/"],
  ["doctor-detail", "/doctors/soha-kayani"],
  ["gallery", "/gallery/"],
  ["blog", "/blog/"],
  ["blog-detail", "/blog/childs-first-dental-visit"],
  ["about", "/about"],
  ["contact", "/contact"],
  ["faqs", "/faqs"],
  ["testimonials", "/testimonials/"],
  ["book", "/book-appointment"],
  ["404", "/this-page-does-not-exist"],
];

const VIEWPORTS = {
  desktop: { width: 1440, height: 900 },
  tablet: { width: 834, height: 1112 },
  mobile: { width: 390, height: 844 },
};

// Scroll the whole page so IntersectionObserver reveals fire and counters run;
// a naive screenshot catches every below-the-fold section still at opacity 0.
//
// Pacing matters: the reveal transition is 1.1s with up to 840ms of stagger delay
// (style.css / main.js). Scrolling faster than that outruns the observer and a
// fullPage capture then shows half the page blank — which looks exactly like a
// CSS bug but is purely a screenshot artifact. Step slowly, then wait for every
// .reveal to actually carry .in-view before shooting.
async function scrollThrough(page) {
  await page.evaluate(async () => {
    await new Promise((resolve) => {
      let y = 0;
      const step = () => {
        window.scrollTo(0, y);
        y += 600;
        if (y < document.body.scrollHeight) setTimeout(step, 260);
        else setTimeout(resolve, 600);
      };
      step();
    });
  });

  // Belt and braces: wait until nothing is left un-revealed (cap at ~8s).
  await page
    .waitForFunction(
      () => [...document.querySelectorAll(".reveal")].every((el) => el.classList.contains("in-view")),
      null,
      { timeout: 8000 }
    )
    .catch(() => {});

  await page.evaluate(() => window.scrollTo(0, 0));
  // Let the final transitions settle before the shutter.
  await page.waitForTimeout(900);
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  let failures = 0;
  let shots = 0;

  for (const [theme, isDark] of [["light", false], ["dark", true]]) {
    for (const [vpName, viewport] of Object.entries(VIEWPORTS)) {
      // Only capture every page at desktop; tablet/mobile get the dense ones,
      // which is where a responsive break would actually show up.
      const pages = vpName === "desktop" ? PAGES : PAGES.filter(([n]) =>
        ["home", "services", "book", "contact", "gallery"].includes(n));

      const ctx = await browser.newContext({
        viewport,
        deviceScaleFactor: 1,
        colorScheme: isDark ? "dark" : "light",
      });
      // The app reads its own localStorage key, not the OS preference.
      await ctx.addInitScript((dark) => {
        try { localStorage.setItem("darkMode", dark ? "true" : "false"); } catch (e) {}
      }, isDark);

      const page = await ctx.newPage();
      const consoleErrors = [];
      page.on("console", (m) => { if (m.type() === "error") consoleErrors.push(m.text()); });

      for (const [name, urlPath] of pages) {
        const url = BASE + urlPath;
        try {
          const resp = await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });
          const status = resp ? resp.status() : 0;
          const expected = name === "404" ? 404 : 200;
          if (status !== expected) {
            console.log(`FAIL: ${urlPath} -> ${status} (expected ${expected})`);
            failures++;
          }
          await scrollThrough(page);
          const file = path.join(OUT, `${theme}-${vpName}-${name}.png`);
          await page.screenshot({ path: file, fullPage: vpName === "desktop" });
          shots++;
        } catch (err) {
          console.log(`FAIL: ${urlPath} (${theme}/${vpName}) -> ${err.message}`);
          failures++;
        }
      }

      // Transform-layer check. `transform` is one property per element: if .tilt
      // ever lands on the same node as .reveal or a hover-lift, the later rule
      // silently replaces the earlier and an effect just stops working, with no
      // error anywhere. This is the check that catches that.
      if (vpName === "desktop" && !isDark) {
        await page.goto(BASE + "/", { waitUntil: "networkidle" });
        const collisions = await page.$$eval(".tilt", (els) =>
          els.filter((el) =>
            el.classList.contains("reveal") ||
            el.classList.contains("hover-lift") ||
            el.classList.contains("hover-zoom")
          ).length);
        if (collisions === 0) {
          console.log("PASS: no transform-layer collisions on /");
        } else {
          console.log(`FAIL: ${collisions} .tilt elements also own another transform`);
          failures++;
        }

        // backdrop-filter budget: each real blur layer forces a per-frame readback
        // of everything behind it. Tier 2 (.glass-card) is free; only tier 1 counts.
        const blurLayers = await page.$$eval("*", (els) =>
          els.filter((el) => {
            const bf = getComputedStyle(el).backdropFilter;
            return bf && bf !== "none";
          }).length);
        console.log(`INFO: ${blurLayers} backdrop-filter layers on / (budget: <= 4)`);
        if (blurLayers > 4) {
          console.log("FAIL: backdrop-filter budget exceeded");
          failures++;
        }
      }

      if (consoleErrors.length) {
        console.log(`WARN: ${consoleErrors.length} console error(s) in ${theme}/${vpName}:`);
        consoleErrors.slice(0, 3).forEach((e) => console.log("   " + e.slice(0, 160)));
      }
      await ctx.close();
    }
  }

  await browser.close();
  console.log(`\n${shots} screenshots -> ${OUT}`);
  console.log(failures === 0 ? "All checks passed." : `${failures} failure(s).`);
  process.exit(failures === 0 ? 0 : 1);
})();
