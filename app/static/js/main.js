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

    const duration = 2200;
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
  //
  // A direct child is usually the .reveal itself, but some grids wrap each item
  // (e.g. the FAQ list wraps every entry in an x-show div), which used to leave the
  // .reveal as a grandchild and the cascade silently doing nothing. So: if the child
  // isn't a .reveal, fall back to the first .reveal inside it.
  // Paced to match the 1.1s reveal in style.css. At 80ms the cascade finished
  // before the first card had settled, so the whole grid read as arriving at once.
  const STEP_MS = 140;
  const MAX_DELAY_MS = 840;
  document.querySelectorAll(".stagger").forEach((group) => {
    let i = 0;
    [...group.children].forEach((child) => {
      const target = child.classList.contains("reveal") ? child : child.querySelector(".reveal");
      if (!target) return; // non-animated children (e.g. a lightbox) don't consume a slot
      target.style.setProperty("--reveal-delay", `${Math.min(i * STEP_MS, MAX_DELAY_MS)}ms`);
      i++;
    });
  });

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("in-view");
        observer.unobserve(entry.target);
      }
    });
    // rootMargin pulls the trigger line up from the viewport bottom so an element
    // starts animating just after it enters, rather than while it's still clipped.
  }, { threshold: 0.1, rootMargin: "0px 0px -80px 0px" });
  items.forEach((el) => observer.observe(el));
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
