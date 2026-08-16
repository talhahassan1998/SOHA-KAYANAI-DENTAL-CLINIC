// Users who ask their OS to reduce motion get the end state immediately, never the travel.
// The CSS media query handles the visual side; this flag short-circuits the JS-driven
// animations (counters, stagger delays) that CSS alone can't reach.
const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// Back-to-top button visibility
(function backToTop() {
  const btn = document.getElementById("back-to-top");
  if (!btn) return;
  window.addEventListener("scroll", () => {
    if (window.scrollY > 400) {
      btn.classList.remove("opacity-0", "pointer-events-none", "translate-y-4");
    } else {
      btn.classList.add("opacity-0", "pointer-events-none", "translate-y-4");
    }
  });
  btn.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));
})();

// Animated stat counters, triggered when scrolled into view
(function statCounters() {
  const counters = document.querySelectorAll("[data-counter]");
  if (!counters.length) return;

  const animate = (el) => {
    const target = parseInt(el.getAttribute("data-counter"), 10) || 0;

    if (prefersReducedMotion) {
      el.textContent = target.toLocaleString();
      return;
    }

    const duration = 1600;
    const start = performance.now();

    function tick(now) {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      el.textContent = Math.floor(eased * target).toLocaleString();
      if (progress < 1) {
        requestAnimationFrame(tick);
      } else {
        el.textContent = target.toLocaleString();
      }
    }
    requestAnimationFrame(tick);
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        animate(entry.target);
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.4 });

  counters.forEach((el) => observer.observe(el));
})();

// Reveal-on-scroll for elements with .reveal class
(function scrollReveal() {
  const items = document.querySelectorAll(".reveal");
  if (!items.length) return;

  // Reduced motion: show everything up front and skip the observer entirely.
  if (prefersReducedMotion) {
    items.forEach((el) => el.classList.add("in-view"));
    return;
  }

  // Inside a .stagger container, children cascade rather than landing together. The cap
  // stops a long grid (say 12 blog cards) from leaving the last item a second behind.
  const STEP_MS = 140;
  const MAX_DELAY_MS = 700;
  document.querySelectorAll(".stagger").forEach((group) => {
    [...group.children].forEach((child, i) => {
      if (child.classList.contains("reveal")) {
        child.style.setProperty("--reveal-delay", `${Math.min(i * STEP_MS, MAX_DELAY_MS)}ms`);
      }
    });
  });

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("in-view");
        observer.unobserve(entry.target);
      }
    });
    // The bottom inset holds the trigger until the element is properly on screen,
    // so the reveal plays where the user is looking instead of finishing off-view.
  }, { threshold: 0.15, rootMargin: "0px 0px -80px 0px" });
  items.forEach((el) => observer.observe(el));
})();

// Scroll-linked drift for the hero implant. The apparent depth in the reference comes from
// the render moving slower than the page, not from any 3D engine — a single translateY
// offset written to a CSS variable is the whole effect.
(function heroDrift() {
  const el = document.querySelector(".hero-implant-shift");
  if (!el || prefersReducedMotion) return;

  const RATE = 0.18;      // px of drift per px of scroll; past ~0.3 it detaches from the page
  const MAX_PX = 140;     // stop before it collides with the section below
  let ticking = false;

  const update = () => {
    const drift = Math.min(window.scrollY * RATE, MAX_PX);
    el.style.setProperty("--hero-drift", `${drift}px`);
    ticking = false;
  };

  window.addEventListener("scroll", () => {
    // rAF-coalesced: scroll fires far more often than the screen repaints.
    if (!ticking) { ticking = true; requestAnimationFrame(update); }
  }, { passive: true });
  update();
})();

// Lazy-fade images once loaded (progressive enhancement on top of native loading="lazy")
(function lazyFadeImages() {
  document.querySelectorAll("img.lazy-fade").forEach((img) => {
    if (img.complete) {
      img.classList.add("loaded");
    } else {
      img.addEventListener("load", () => img.classList.add("loaded"));
    }
  });
})();
