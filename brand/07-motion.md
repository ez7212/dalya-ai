# Dalya — Motion Principles

*Phase 2 deliverable. Read [`PHASE-1-LOCK.md`](./PHASE-1-LOCK.md), [`05-surface-spacing.md`](./05-surface-spacing.md), and [`06-components.md`](./06-components.md) first.*

---

## The frame

Eric was explicit in the brief: *"SaaS products often over-animate; we shouldn't."* This document is the operationalization of that instinct. Motion in Dalya is in service of two attributes from the brand triplet: **Calm** (motion that doesn't fatigue), and **Sharp** (motion that respects the user's time). It is *not* in service of Trustworthy — trustworthiness comes from accuracy and restraint, not animation.

The default posture: **motion is the exception, not the rule.** Every animation in the system is justified by name in §3. Everything not on that list is static.

---

## 1. What animation expresses, in priority order

| # | Purpose | Example |
|---|---|---|
| 1 | **State change confirmation** — the user did something; the interface acknowledges it physically. | Button press feedback, toggle flip, checkbox check. |
| 2 | **Spatial continuity** — show where something came from or where it went so the user maintains orientation. | Modal entering from center-with-fade, side-sheet sliding from edge, accordion expanding. |
| 3 | **Progress feedback** — a determinate operation is moving forward. | Upload progress bar, SPA parsing stage transitions. |
| 4 | **Attention to a destructive or high-stakes moment** — a single brief animation signals "pay attention to this." | Confirmation modal entry, error toast slide-in. |

Anything that does not serve one of these four is decoration. Decoration is banned.

---

## 2. What we never animate — the ban list

- **Number tickers.** AED amounts do not count up. They render at their final value. The user is making a financial decision; animated numbers are play.
- **Hover micro-bounce.** Buttons do not scale, lift, or jiggle on hover. They change background color.
- **Parallax.** No motion tied to scroll position. Ever.
- **Scroll-triggered fades.** Long marketing pages do not reveal content as the user scrolls. Render it all at mount and let the user scan.
- **AI "thinking" shimmers.** No animated gradient bars suggesting "Dalya is thinking." Latency is what it is; shimmer animations lie about it. See `06-components.md` §6.7.
- **Typing indicators (animated dots).** Same reason as above.
- **Loading spinners on the page background.** Use skeletons. Spinners are for inline action feedback (inside a button).
- **Hero text fade-up on page load.** The page renders; the user reads. No theater.
- **Page transitions** (route-to-route fades or slides). The browser handles navigation; we don't animate it.
- **Color cycling.** Brand colors do not animate between hues for emphasis.
- **Pulsing on rest-state elements.** Pulses are for active states only (e.g. a live conversation dot).
- **Confetti, celebration animations, or success choreography.** Closing a deal is its own reward. The toast says "Offer accepted" and that's it.

---

## 3. Where motion lives — the allow list

Only the patterns below are allowed. New animation proposals must justify by §1.

| Pattern | Purpose (per §1) | Timing | Easing |
|---|---|---|---|
| Button hover background-color | State change | `120ms` | `ease-out` |
| Button press (active state) | State change | `0ms` (instant) | — |
| Card hover background-color | State change | `120ms` | `ease-out` |
| Table row hover background-color | State change | `100ms` | `ease-out` |
| Input focus border-color | State change | `120ms` | `ease-out` |
| Toggle/switch position | State change | `160ms` | `ease-out` |
| Toast slide-in from edge | Spatial continuity | `200ms` | `ease-out-quart` |
| Toast slide-out (auto-dismiss or click) | Spatial continuity | `160ms` | `ease-in-quart` |
| Modal entry (scale 0.96 → 1 + opacity 0 → 1) | Spatial continuity + attention | `200ms` | `ease-out-quart` |
| Modal exit (opacity 1 → 0) | Spatial continuity | `120ms` | `ease-in-quart` |
| Side sheet slide-in from edge | Spatial continuity | `220ms` | `ease-out-quart` |
| Side sheet slide-out | Spatial continuity | `180ms` | `ease-in-quart` |
| Popover/dropdown open (scale + opacity) | Spatial continuity | `120ms` | `ease-out` |
| Popover/dropdown close | Spatial continuity | `80ms` | `ease-in` |
| Tab content cross-fade | State change | `120ms` | `ease-out` |
| Accordion expand/collapse height | Spatial continuity | `180ms` | `ease-out-quart` |
| Command-palette / search open (opacity + scale 0.98 → 1) | Spatial continuity | `120ms` | `ease-out` |
| Skeleton pulse | Progress feedback | `1400ms` cycle | `ease-in-out` |
| Indeterminate progress bar slide | Progress feedback | `1200ms` cycle, linear | `linear` |
| Determinate progress bar fill | Progress feedback | matches operation duration | `linear` |
| Live conversation dot pulse | Attention | `1600ms` cycle | `ease-in-out` |
| Notification badge appear (scale 0 → 1) | Attention | `160ms` | `ease-out-back` (very subtle back) |
| Toast action click feedback | State change | `80ms` | `ease-out` |

That's the complete list. Anything outside this table is banned and needs a documented exception.

---

## 4. Timing tokens

Five duration tokens. Every motion in §3 maps to one of these.

```css
@theme {
  --duration-instant: 0ms;     /* press states, no transition */
  --duration-fast: 80ms;       /* small dismissals, micro-feedback */
  --duration-base: 120ms;      /* the default — hover, focus, most state changes */
  --duration-medium: 180ms;    /* spatial movement (toggle, accordion) */
  --duration-slow: 220ms;      /* large spatial movement (modal, sheet) */
}
```

Tailwind v4 utility classes:
- `transition-none` → `--duration-instant`
- `duration-80` → `--duration-fast`
- `duration-120` → `--duration-base` (recommend as default in `tailwind.config`)
- `duration-180` → `--duration-medium`
- `duration-220` → `--duration-slow`

**Banned: durations >300ms in product UI.** Anything that takes longer than a third of a second to complete feels sluggish in a daily-use tool. Marketing-page animation may go up to 400ms; product chrome may not.

---

## 5. Easing tokens

Four easing curves. They map to perceived "physics":

```css
@theme {
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  /* Default for state changes. Strong start, settles smoothly. */

  --ease-in: cubic-bezier(0.7, 0, 0.84, 0);
  /* Default for exits and dismissals. Gentle start, accelerates out. */

  --ease-out-quart: cubic-bezier(0.25, 1, 0.5, 1);
  /* Modal and sheet entries. More dramatic than ease-out, still feels mechanical. */

  --ease-in-quart: cubic-bezier(0.5, 0, 0.75, 0);
  /* Modal and sheet exits. */

  --ease-out-back: cubic-bezier(0.34, 1.4, 0.64, 1);
  /* RARE. Only for notification-badge appearance. The 1.4 overshoot is intentionally tiny — barely perceptible. */
}
```

**Banned eases:**
- Material Design's `ease-in-out` curve (`cubic-bezier(0.4, 0, 0.2, 1)`). It's too soft and feels "designed." Our default is sharper.
- Linear (except for the indeterminate progress bar slide where linear is correct).
- Bounce / elastic curves. Never.
- Cubic-bezier curves outside the tokens above. Every motion uses one of the five.

The default `--ease-out` curve was chosen because it has a strong initial movement (the user sees the change start immediately) and a soft tail (the change resolves without visible deceleration). This is the "calm but sharp" combination — fast enough to feel responsive, smooth enough not to be jarring.

---

## 6. Mobile vs desktop motion behavior

Mobile gets slightly *more* motion than desktop. The reason: touch surfaces lack hover affordance, so tap-feedback motion replaces the visual cue that hover provides on desktop.

| Pattern | Desktop | Mobile |
|---|---|---|
| Button press | Instant background drop | Instant background drop + 80ms opacity pulse (0.7 → 1) |
| Card tap | No press feedback (hover already prepared the user) | `80ms` opacity pulse + selected state |
| Sheet entry | Side-sheet slide from right (220ms) | Bottom-sheet slide from bottom (220ms) — same duration, different direction |
| Modal entry | Center scale + opacity | Bottom-sheet slide (replaces the modal pattern entirely on mobile per `06-components.md` §5.1) |
| Hover effects | Apply | Disabled (touch never hovers) |

Mobile-specific extras:
- Pull-to-refresh on the conversations list. Uses a native or near-native pattern. Spring physics handled by the OS, not by us.
- Swipe-to-archive on a conversation card. The card slides out at the user's velocity; if released past the threshold, an archive toast appears.

Mobile-specific bans:
- No haptics on idle interactions. Haptics are reserved for *destructive* actions and *error* events. Tap-to-open a card does not vibrate.
- No bottom-sheet that occupies more than 90% of viewport height. If you need 100%, use a full-screen route, not a sheet.

---

## 7. Reduced-motion accessibility

`prefers-reduced-motion: reduce` is honored across every pattern. The rules:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

The above is the global reset. Specific overrides for cases where reduced-motion users still need *some* visible state change:

- **Skeleton loaders:** the pulse animation stops, but the skeleton element stays visible as a static gray block. Loading is still communicated by the presence of the skeleton, not by its pulse.
- **Indeterminate progress bars:** the slide animation stops, but the bar still renders (static gradient at midpoint). The presence of the bar communicates loading.
- **Notification badge appear:** the scale animation is replaced by an instant opacity change.
- **Toasts:** slide-in replaced by instant opacity. Toast still appears; it just doesn't slide.

**Banned in reduced-motion mode:**
- The live conversation dot pulse. Falls back to a static dot.
- Modal scale entry. Falls back to instant opacity.

Tailwind v4: every motion utility class above pairs with a `motion-reduce:` variant:

```tsx
<div className="
  transition-colors duration-120 ease-out
  motion-reduce:transition-none
">
```

---

## 8. Motion in the chat surface

The chat surface is the most-used view. Motion calibration here matters disproportionately.

### 8.1 New message appearance

When a new message arrives (buyer, Dalya, or agent), it appears with:
- Opacity `0` → `1` over `120ms`
- Translate-Y `4px` → `0` over `120ms` (subtle nudge up from below)
- No scale, no border flash

The chat auto-scrolls to the bottom only if the user was already at the bottom. If the user has scrolled up to read history, the scroll position stays; a small "↓ New messages" pill appears above the composer until the user clicks it or scrolls down.

### 8.2 Composer focus

When the agent clicks the composer, the composer expands from one-line (default) to three-line (focused). Transition: height `180ms ease-out`. This is the *only* component in the system that auto-expands on focus.

### 8.3 No typing indicator

Per `06-components.md` §6.7. No animated dots. No "Dalya is typing" string. If latency exceeds 6 seconds, a single static-text indicator appears in the agent's surface (not the buyer's): *"Dalya is preparing a response..."* — no animation on the text itself, just a single subtle dot pulse next to it.

### 8.4 Inline-data-card appearance

When Dalya surfaces an inline data card (offer summary, Verified-SPA snippet), the card appears as part of the bubble — no separate animation. The whole bubble appears at once.

### 8.5 Scroll-to-bottom button

When the user scrolls up and a new message arrives, a "↓ New messages" pill fades in above the composer. Fade: `120ms ease-out`. Click: instant scroll to bottom (`scroll-behavior: smooth` is *off* — we want immediate response, not a long scroll animation).

---

## 9. Brand motion moments

Two surfaces are allowed to have a single brand-grade motion moment each. Both are signed-out:

1. **Login page** — the Dalya wordmark fades in over `400ms` (the only animation in the system that exceeds 300ms; this is a signed-out marketing-class surface). Once. Not on every re-render.
2. **First-time SPA upload** — when the parsing completes successfully on a user's *first* upload, the success toast lingers `8s` instead of `4s`, and the toast text adopts a tonal lift (one extra tonal step) for the lifespan of that toast.

These are the *only* brand moments. They are not in the chat, not on the dashboard, not in the working surface.

---

## 10. Tailwind v4 implementation

Final block, ready to merge into the `@theme` in `05-surface-spacing.md`:

```css
@theme {
  /* Durations */
  --duration-instant: 0ms;
  --duration-fast: 80ms;
  --duration-base: 120ms;
  --duration-medium: 180ms;
  --duration-slow: 220ms;

  /* Easings */
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-in: cubic-bezier(0.7, 0, 0.84, 0);
  --ease-out-quart: cubic-bezier(0.25, 1, 0.5, 1);
  --ease-in-quart: cubic-bezier(0.5, 0, 0.75, 0);
  --ease-out-back: cubic-bezier(0.34, 1.4, 0.64, 1);

  /* Keyframes — used for skeleton pulse, dot pulse, indeterminate progress */
  @keyframes pulse-skeleton {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.6; }
  }

  @keyframes pulse-dot {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.7; transform: scale(0.85); }
  }

  @keyframes progress-indeterminate {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(400%); }
  }
}

@layer utilities {
  .animate-pulse-skeleton {
    animation: pulse-skeleton 1400ms ease-in-out infinite;
  }
  .animate-pulse-dot {
    animation: pulse-dot 1600ms ease-in-out infinite;
  }
  .animate-progress-indeterminate {
    animation: progress-indeterminate 1200ms linear infinite;
  }

  @media (prefers-reduced-motion: reduce) {
    .animate-pulse-skeleton,
    .animate-pulse-dot,
    .animate-progress-indeterminate {
      animation: none;
    }
  }
}
```

---

## Motion review checklist

Before any animation ships to the product:

1. Which of the four purposes (§1) does this serve? If none, cut it.
2. Is the duration ≤220ms? If not, justify or cut.
3. Does it have a reduced-motion fallback?
4. Does it work on mobile (where touch replaces hover)?
5. Is the easing one of the five tokens? If not, why?
6. Is this animating something the user will see repeatedly per session? If yes, halve the duration.
7. Does the motion lie about anything (latency, completion, progress, AI thinking)? If yes, cut it.

If a proposed animation fails any of these, it doesn't ship.
