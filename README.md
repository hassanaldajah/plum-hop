# Plum Hop

An original bouncing platformer that runs in the browser on phone and desktop. One self-contained file (`public/index.html`), no libraries, no build step.

- 4 worlds, 20 levels, 30 gems per level
- Keyboard and multi-touch controls, progress saved in the browser
- All graphics drawn in code, all sound generated with the Web Audio API

## Run
Open `public/index.html` in a browser.

## Deploy
Static hosting: publish the `public` folder (no build command). `public/_headers` holds the security headers for Cloudflare.

## Tests
`node tools/verify-levels.js public/index.html` searches every level for a run that collects all gems without falling.
`tools/e2e.js` and `tools/e2e-resume.js` are real-browser checks (they need playwright-core and Microsoft Edge).
