const MOTION_URL = "https://cdn.jsdelivr.net/npm/motion@11.13.5/+esm";

export const MOTION = Object.freeze({
  pressIn: 0.09,
  pressOut: 0.14,
  micro: 0.18,
  content: 0.26,
  layout: 0.34,
  accordion: 0.42,
  ease: [0.22, 1, 0.36, 1],
});

export const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

let motionPromise;
function loadMotion() {
  if (!motionPromise) {
    motionPromise = import(MOTION_URL).catch((error) => {
      console.warn("Courier Control: Motion CDN unavailable, using Web Animations fallback.", error);
      return null;
    });
  }
  return motionPromise;
}

function easingCss(ease) {
  if (Array.isArray(ease) && ease.length === 4) return `cubic-bezier(${ease.join(",")})`;
  return typeof ease === "string" ? ease : "ease";
}

function applyFinalStyles(element, keyframes) {
  Object.entries(keyframes).forEach(([property, values]) => {
    const value = Array.isArray(values) ? values[values.length - 1] : values;
    element.style[property] = String(value);
  });
}

export async function animateElement(element, keyframes, options = {}) {
  if (!element) return;
  if (reduceMotion) {
    applyFinalStyles(element, keyframes);
    return;
  }

  const motion = await loadMotion();
  if (motion?.animate) {
    try {
      await motion.animate(element, keyframes, options);
      return;
    } catch (error) {
      console.warn("Courier Control: Motion animation failed, falling back to WAAPI.", error);
    }
  }

  const animation = element.animate(keyframes, {
    duration: Math.max(0, (options.duration ?? MOTION.micro) * 1000),
    delay: Math.max(0, (options.delay ?? 0) * 1000),
    easing: easingCss(options.ease),
    fill: "forwards",
  });
  try {
    await animation.finished;
  } catch (_) {
    // A cancelled animation is not a UI failure.
  }
}

function asElements(targets) {
  if (typeof targets === "string") return [...document.querySelectorAll(targets)];
  if (targets instanceof Element) return [targets];
  return [...(targets || [])];
}

export async function bindPressables(targets) {
  const elements = asElements(targets);
  elements.forEach((element) => element.classList.add("motion-managed"));
  if (reduceMotion || !elements.length) return;

  const motion = await loadMotion();
  if (motion?.press && motion?.animate) {
    elements.forEach((element) => {
      motion.press(element, (target) => {
        motion.animate(target, { transform: "scale(.985)", filter: "brightness(.94)" }, {
          duration: MOTION.pressIn,
          ease: MOTION.ease,
        });
        return () => motion.animate(target, { transform: "scale(1)", filter: "brightness(1)" }, {
          duration: MOTION.pressOut,
          ease: MOTION.ease,
        });
      });
    });
    return;
  }

  elements.forEach((element) => {
    const down = () => {
      element.animate(
        [{ transform: "scale(1)", filter: "brightness(1)" }, { transform: "scale(.985)", filter: "brightness(.94)" }],
        { duration: MOTION.pressIn * 1000, easing: easingCss(MOTION.ease), fill: "forwards" },
      );
    };
    const up = () => {
      element.animate(
        [{ transform: "scale(.985)", filter: "brightness(.94)" }, { transform: "scale(1)", filter: "brightness(1)" }],
        { duration: MOTION.pressOut * 1000, easing: easingCss(MOTION.ease), fill: "forwards" },
      );
    };
    element.addEventListener("pointerdown", down, { passive: true });
    element.addEventListener("pointerup", up, { passive: true });
    element.addEventListener("pointercancel", up, { passive: true });
    element.addEventListener("pointerleave", up, { passive: true });
  });
}

const nextFrame = () => new Promise((resolve) => requestAnimationFrame(resolve));

export class SingleAccordion {
  constructor(items, options = {}) {
    this.items = asElements(items);
    this.bodySelector = options.bodySelector || ":scope > .route-detail-body";
    this.summarySelector = options.summarySelector || ":scope > summary";
    this.busy = false;
    this.pending = null;

    const initiallyOpen = this.items.filter((item) => item.open);
    this.current = initiallyOpen[0] || null;
    initiallyOpen.slice(1).forEach((item) => { item.open = false; });

    this.items.forEach((item) => this.bind(item));
  }

  bind(item) {
    const summary = item.querySelector(this.summarySelector);
    if (!summary) return;
    summary.classList.add("motion-managed");
    summary.addEventListener("click", (event) => {
      event.preventDefault();
      this.request(item);
    });
  }

  request(item) {
    if (this.busy) {
      this.pending = item;
      return;
    }
    void this.transitionTo(item);
  }

  async transitionTo(item) {
    this.busy = true;
    try {
      const isCurrentOpen = item === this.current && item.open;
      if (isCurrentOpen) {
        await this.animateOne(item, false);
        this.current = null;
      } else {
        const previous = this.current?.open
          ? this.current
          : this.items.find((candidate) => candidate !== item && candidate.open);

        if (previous && previous !== item) {
          await this.animateSwitch(previous, item);
        } else {
          await this.animateOne(item, true);
        }
        this.current = item;
      }

      this.items.forEach((candidate) => {
        if (candidate !== this.current && candidate.open) candidate.open = false;
      });
    } finally {
      this.busy = false;
      if (this.pending) {
        const pending = this.pending;
        this.pending = null;
        if (pending !== this.current || pending.open) this.request(pending);
      }
    }
  }

  parts(item) {
    return {
      summary: item.querySelector(this.summarySelector),
      body: item.querySelector(this.bodySelector),
      chevron: item.querySelector(":scope > summary .route-chevron"),
    };
  }

  prepare(item, open) {
    const { summary, body, chevron } = this.parts(item);
    if (!summary || !body) return null;

    const startHeight = item.getBoundingClientRect().height;
    if (open && !item.open) item.open = true;

    const summaryHeight = summary.getBoundingClientRect().height;
    const naturalHeight = item.getBoundingClientRect().height;
    const endHeight = open ? naturalHeight : summaryHeight;

    item.classList.add("motion-accordion");
    item.style.overflow = "hidden";
    item.style.height = `${startHeight}px`;

    body.style.opacity = open ? "0" : "1";
    body.style.transform = open ? "translateY(-4px)" : "translateY(0px)";
    if (chevron) chevron.style.transition = "none";

    return { item, summary, body, chevron, open, startHeight, endHeight };
  }

  async play(prepared) {
    if (!prepared) return;
    const { item, body, chevron, open, startHeight, endHeight } = prepared;
    const animations = [
      animateElement(item, { height: [`${startHeight}px`, `${endHeight}px`] }, {
        duration: MOTION.accordion,
        ease: MOTION.ease,
      }),
      animateElement(body, {
        opacity: open ? [0, 1] : [1, 0],
        transform: open
          ? ["translateY(-4px)", "translateY(0px)"]
          : ["translateY(0px)", "translateY(-3px)"],
      }, {
        duration: MOTION.content,
        delay: open ? 0.04 : 0,
        ease: MOTION.ease,
      }),
    ];

    if (chevron) {
      animations.push(animateElement(chevron, {
        transform: open ? ["rotate(45deg)", "rotate(225deg)"] : ["rotate(225deg)", "rotate(45deg)"],
        marginTop: open ? ["-4px", "4px"] : ["4px", "-4px"],
      }, {
        duration: MOTION.layout,
        ease: MOTION.ease,
      }));
    }

    await Promise.all(animations);
  }

  async finish(prepared) {
    if (!prepared) return;
    const { item, body, chevron, open, endHeight } = prepared;

    item.style.height = `${endHeight}px`;
    item.open = open;
    await nextFrame();

    item.style.height = "";
    item.style.overflow = "";
    body.style.opacity = "";
    body.style.transform = "";
    if (chevron) {
      chevron.style.transform = "";
      chevron.style.marginTop = "";
      chevron.style.transition = "";
    }
  }

  async animateOne(item, open) {
    const prepared = this.prepare(item, open);
    if (!prepared) return;
    if (!reduceMotion) await nextFrame();
    await this.play(prepared);
    await this.finish(prepared);
  }

  async animateSwitch(previous, next) {
    const closing = this.prepare(previous, false);
    const opening = this.prepare(next, true);
    if (!closing || !opening) {
      if (closing) await this.animateOne(previous, false);
      if (opening) await this.animateOne(next, true);
      return;
    }

    if (!reduceMotion) await nextFrame();
    await Promise.all([this.play(closing), this.play(opening)]);
    await Promise.all([this.finish(closing), this.finish(opening)]);
  }

  openInstant(item) {
    this.items.forEach((candidate) => {
      candidate.open = candidate === item;
    });
    this.current = item;
  }
}

export async function warmMotion() {
  return loadMotion();
}
