# Girls Just Want to Be One

A one-page invitation site for a first birthday party. Single self-contained
`index.html` — no build step, no dependencies, no network requests. Open it in a
browser, or drop it on any static host (GitHub Pages, Netlify, S3).

## Editing

Everything party-specific lives in one `CONFIG` block at the top of the `<script>`
at the bottom of `index.html`:

```js
var CONFIG = {
  name: "Nora",                 // PLACEHOLDER — the birthday girl's name
  address: "3234 Morning Springs Drive, Henderson, NV 89074",
  rsvpEmail: "ccastonguay07@gmail.com",
  rsvpSubject: "RSVP — Girls Just Want to Be One",
  startsAtISO: "2026-09-12T17:00:00Z"   // Sat Sep 12 2026, 10:00 AM Pacific
};
```

`name` drives the hero line, `address` builds the Google Maps link, `rsvpEmail`
builds the mailto, and `startsAtISO` drives the countdown. Note that
`startsAtISO` is **UTC** — 10:00 AM Pacific in September is `17:00:00Z`, since
Nevada is on daylight time (UTC−7) then.

The run of show (the Side A / Side B tracklist) and the four detail panels are
plain markup in the `<body>` — edit them directly.

## Design notes

The theme plays on Cyndi Lauper rather than the usual neon-on-black synthwave,
so the page is built as a **printed 45 rpm record sleeve**: warm sleeve stock,
hard offset shadows with no blur, slight rotations on each card, Impact for
display type and Courier for the typewritten J-card labels. The party schedule
is set as a mixtape tracklist.

Colors are CSS custom properties on `:root`, with a second "night pressing"
palette (deep grape ground) under `prefers-color-scheme: dark` and the
`[data-theme]` overrides.

## Animations

Balloons and confetti share one `<canvas>` behind the content. The title drops
in letter by letter on load, the record and cassette reels spin, cards pop in on
scroll, and tapping the big **ONE** fires a confetti burst.

All of it is gated behind `prefers-reduced-motion` — when that's set, the canvas
is removed entirely, nothing spins, and every section renders in place. The
scroll reveals are also gated behind a `.js` class on `<html>`, so with
JavaScript disabled the full page still renders rather than staying invisible.

## Typography caveat

Display type is `Impact`, a system font on macOS, Windows, and iOS. Artifact/CSP
rules block external font CDNs, so nothing is loaded over the network. On the
handful of platforms without Impact (most Android builds, some Linux distros)
the stack falls back to Haettenschweiler → Franklin Gothic Bold → Arial Black →
the generic sans. The layout holds up, but the poster-face character is lost.
Self-host a webfont as a `@font-face` data URI if that matters.
