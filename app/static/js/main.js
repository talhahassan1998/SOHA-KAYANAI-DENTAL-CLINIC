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

  // A container can opt out of the shared pace with data-stagger-step (and
  // optionally data-stagger-max) when its items must land strictly one after
  // another rather than overlapping. The process strip needs this: each step
  // builds ring -> icon -> caption over ~1.4s, so at the default 140ms the four
  // steps ran on top of each other instead of in sequence. Raising the shared
  // STEP_MS instead would have slowed every card grid on the site.
  document.querySelectorAll(".stagger").forEach((group) => {
    const step = Number(group.dataset.staggerStep) || STEP_MS;
    // An explicit per-container pace defaults to uncapped — the cap exists to keep
    // long grids tight, which is the opposite of what a deliberate sequence wants.
    const max = group.dataset.staggerMax !== undefined
      ? Number(group.dataset.staggerMax)
      : (group.dataset.staggerStep !== undefined ? Infinity : MAX_DELAY_MS);
    let i = 0;
    [...group.children].forEach((child) => {
      const target = child.classList.contains("reveal") ? child : child.querySelector(".reveal");
      if (!target) return; // non-animated children (e.g. a lightbox) don't consume a slot
      // Decorative members of the group (the process strip's rail) are revealed with
      // everything else but must not take a slot in the cascade, or every real item
      // shifts one step later. They set their own timing in CSS.
      if (target.dataset.staggerSkip !== undefined) return;
      target.style.setProperty("--reveal-delay", `${Math.min(i * step, max)}ms`);
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

  // A [data-stagger-step] group runs as ONE sequence: the container is what gets
  // observed, and it reveals its own children so they always fire in DOM order at
  // the pace set above. Observing each child separately (the default path below)
  // would start whichever crossed the trigger line first — fine for a grid, but it
  // breaks a numbered walkthrough, where a stacked mobile layout would otherwise
  // reveal step 1, then 2, then 3 only as the user scrolled past each one.
  const sequenced = new Set();
  document.querySelectorAll(".stagger[data-stagger-step]").forEach((group) => {
    const children = [...group.querySelectorAll(".reveal")];
    if (!children.length) return;
    children.forEach((el) => sequenced.add(el));

    // data-stagger-loop="<hold ms>": replay the walkthrough on a loop instead of
    // freezing after one pass. The whole sequence is CSS transitions keyed on
    // .in-view, so a replay is: strip the class, let the elements actually paint
    // at their start values, then re-add it.
    //
    // RESET_MS is why this is a timeout and not a rAF pair. Dropping the class and
    // restoring it a frame or two later is visually a no-op: the transition never
    // gets a rendered frame at the start value, so the ring simply stays at scale 1
    // and only the class flickers (measured — the ring never left 1.0). The reset
    // needs to be a state the user briefly sees for the replay to read as a replay.
    // Reduced motion gets the one-shot reveal, never the loop: repeating motion is
    // exactly what that preference is asking us not to do.
    const loopHold = prefersReducedMotion ? 0 : Number(group.dataset.staggerLoop);
    const stepMs = Number(group.dataset.staggerStep) || STEP_MS;
    // Last step starts at (n-1)*step; its caption is the final thing to land at
    // +0.52s delay +0.5s duration (see the PROCESS STEPS block in style.css).
    const passMs = (children.length - 1) * stepMs + 1020;
    let timer = null;
    // Tracked separately from `timer`, which is briefly null during the two-rAF
    // reset gap — keying "is it running?" off the handle alone would let a
    // re-entry start a second, overlapping loop.
    let running = false;

    const RESET_MS = 260;

    const play = () => {
      if (!running) return;  // stopped while we were waiting out the reset
      children.forEach((el) => el.classList.add("in-view"));
      timer = setTimeout(() => {
        // .stagger-resetting kills transitions for the rewind, so the strip snaps
        // back to its start state instead of playing the whole build backwards as
        // a 0.85s shrink. Forced reflow between the two class changes commits the
        // snapped-back values, so re-adding .in-view animates from zero again.
        group.classList.add("stagger-resetting");
        children.forEach((el) => el.classList.remove("in-view"));
        void group.offsetWidth;
        group.classList.remove("stagger-resetting");
        timer = setTimeout(play, RESET_MS);
      }, passMs + loopHold);
    };

    const stop = () => {
      running = false;
      clearTimeout(timer);
      timer = null;
    };

    const seqObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        // Looping groups keep their observer: leaving the viewport stops the timer
        // so an offscreen section isn't burning frames, and re-entering restarts it.
        if (!entry.isIntersecting) {
          if (loopHold) stop();
          return;
        }
        if (loopHold) {
          if (!running) { running = true; play(); }
          return;
        }
        children.forEach((el) => el.classList.add("in-view"));
        seqObserver.unobserve(entry.target);
      });
    }, { threshold: 0.1, rootMargin: "0px 0px -80px 0px" });
    seqObserver.observe(group);
  });

  items.forEach((el) => { if (!sequenced.has(el)) observer.observe(el); });
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

// Pointer tilt on .tilt elements.
//
// These last two IIFEs live in this file specifically so they can read the
// module-scoped `prefersReducedMotion` above — it isn't exported, so a separate
// file would have to re-derive it and could drift out of sync.
//
// Layering: the inline `transform` written here belongs to .tilt and nothing
// else. See the "one transform consumer per element" note in style.css — the
// hover lift lives on a child, the reveal on a parent, and none of the three
// can cancel the others.
(function pointerTilt() {
  if (prefersReducedMotion) return;
  // No cursor to follow on touch/coarse pointers, and binding a move listener
  // there burns battery for an effect nobody can trigger. The CSS carries a
  // matching (hover: none) rule so the classes are neutralised too.
  if (!window.matchMedia("(hover: hover) and (pointer: fine)").matches) return;
  if (!document.querySelector(".tilt")) return;

  const clamp = (v, lo, hi) => (v < lo ? lo : v > hi ? hi : v);

  const MAX_DEG = 6;   // past ~8deg the text on the card face visibly shears
  const LIFT_PX = 10;  // translateZ — the card coming toward the viewer
  const EASE = 0.22;   // per-frame approach rate; ~0.2s to settle at 60fps

  let active = null;
  let pending = null;
  let last = null;   // most recent pointer position, survives active/pending resets
  let frame = 0;
  // Rendered angle, which chases the cursor's target angle instead of being set to
  // it outright. A CSS transition cannot do this job: `transition:none` is required
  // for 1:1 tracking, and re-enabling it just for the entry does not interpolate
  // (the resting style is `transform: none`, and none -> rotate snaps). So the
  // easing lives here, in the same rAF that already writes the transform.
  let curX = 0, curY = 0;
  let idle = true;   // nothing rendered yet this hover — snap to target, no travel

  function apply() {
    if (!active || !pending) { frame = 0; return; }
    const r = active.getBoundingClientRect();
    if (!r.width || !r.height) { frame = 0; return; }
    frame = 0;
    // -0.5 .. 0.5, measured from the element's centre. Clamped because pointermove
    // is bound to the document, not the card: while a card is active the cursor can
    // sit well outside it (a grid gap, or the moment before pointerover hands over
    // to the neighbour), and an unclamped offset scales linearly with that distance
    // — a cursor 3 card-heights below produced ~30deg instead of MAX_DEG.
    const px = clamp((pending.x - r.left) / r.width - 0.5, -0.5, 0.5);
    const py = clamp((pending.y - r.top) / r.height - 0.5, -0.5, 0.5);
    // rotateX is negated: pushing the cursor DOWN should tip the top edge toward
    // you, which is the opposite sign of the raw offset.
    const targetX = -py * MAX_DEG * 2;
    const targetY = px * MAX_DEG * 2;

    if (idle) {
      // First frame of this hover: start AT rest and travel out, rather than
      // appearing already tilted. Entering near a corner used to be an ~8deg jump
      // in a single frame — the snap that read as the card lurching.
      curX = 0;
      curY = 0;
      idle = false;
    }
    // Exponential chase. EASE is the fraction of the remaining gap closed per
    // frame: high enough that the card never feels laggy under the cursor, low
    // enough that a big jump (entry, or a fast flick across the card) is spread
    // over a few frames instead of landing in one.
    curX += (targetX - curX) * EASE;
    curY += (targetY - curY) * EASE;

    active.style.transform =
      "rotateX(" + curX.toFixed(2) + "deg) " +
      "rotateY(" + curY.toFixed(2) + "deg) " +
      "translateZ(" + LIFT_PX + "px)";

    // Keep chasing until the card has effectively arrived, otherwise a cursor that
    // stops moving would freeze the card part-way through its travel.
    if (Math.abs(targetX - curX) > 0.01 || Math.abs(targetY - curY) > 0.01) {
      if (!frame) frame = requestAnimationFrame(apply);
    }
  }

  function enter(el) {
    if (active === el) return;
    if (active) leave();
    active = el;
    // will-change only while tracking. Left on permanently it promotes every
    // card to its own compositor layer for the whole session — on a 40-card grid
    // that is hundreds of MB of GPU memory for an effect used one card at a time.
    el.style.willChange = "transform";
    el.style.transition = "none";
    idle = true;   // next rendered frame starts the travel from rest
    // Card-to-card moves fire pointerover BEFORE the next pointermove, and leave()
    // just nulled `pending`. Without re-seeding it here the new card renders one
    // frame flat with transition:none already set, then jumps when the move lands.
    pending = last;
    if (pending && !frame) frame = requestAnimationFrame(apply);
  }

  function leave() {
    if (!active) return;
    const el = active;
    active = null;
    pending = null;
    idle = true;
    el.style.transition = "";  // hand back to the CSS return-home easing
    el.style.transform = "";
    // Drop the hint only once the return animation has finished (CSS: .5s).
    setTimeout(function () { el.style.willChange = ""; }, 550);
  }

  // One delegated listener rather than one per card: with ~40 cards that would be
  // 40 listeners and 40 closures for an effect only one card can hold at a time.
  // pointerover bubbles (pointerenter does not), which is what makes this work.
  document.addEventListener("pointerover", function (e) {
    const el = e.target.closest && e.target.closest(".tilt");
    if (el) enter(el); else leave();
  }, { passive: true });

  document.addEventListener("pointermove", function (e) {
    last = { x: e.clientX, y: e.clientY };
    if (!active) return;
    pending = last;
    // pointermove fires faster than the display refreshes; batching to rAF means
    // one style write per frame instead of several per frame for one visible result.
    if (!frame) frame = requestAnimationFrame(apply);
  }, { passive: true });

  document.addEventListener("pointerleave", leave);
  window.addEventListener("blur", leave);
  // A scroll under a stationary cursor would otherwise leave a card frozen at a
  // stale angle after it has moved out from under the pointer.
  window.addEventListener("scroll", leave, { passive: true });
})();

// Scroll parallax for decorative layers.
(function scrollParallax() {
  if (prefersReducedMotion) return;
  const items = Array.prototype.slice.call(document.querySelectorAll("[data-parallax]"));
  if (!items.length) return;

  let frame = 0;

  function update() {
    frame = 0;
    const vh = window.innerHeight;
    for (let i = 0; i < items.length; i++) {
      const el = items[i];
      const r = el.getBoundingClientRect();
      // Skip off-screen elements: parallax only exists for what you can see, and
      // this keeps the per-frame cost proportional to the viewport, not the page.
      if (r.bottom < -200 || r.top > vh + 200) continue;
      // -1 .. 1 across the viewport; 0 when the element is vertically centred.
      const progress = (r.top + r.height / 2 - vh / 2) / vh;
      const depth = parseFloat(el.dataset.parallax) || 20;
      // Writes a CSS variable, not `transform` — the element may also carry a
      // keyframe animation (animate-drift), and two writers to one `transform`
      // would silently cancel each other.
      el.style.setProperty("--parallax-y", (progress * depth).toFixed(1) + "px");
    }
  }

  // rAF-coalesced: however many scroll events fire, at most one write per frame.
  // Kept as its own listener rather than folded into backToTop() so the four
  // original IIFEs stay untouched.
  window.addEventListener("scroll", function () {
    if (!frame) frame = requestAnimationFrame(update);
  }, { passive: true });
  window.addEventListener("resize", function () {
    if (!frame) frame = requestAnimationFrame(update);
  }, { passive: true });
  update();
})();
