# og-image.png

This directory needs a `og-image.png` file at the path `web/og-image.png`
(referenced from `index.html` Open Graph + Twitter Card meta tags).

## Specs

- Dimensions: **1200 x 630 px** (standard Open Graph aspect ratio)
- Format: PNG (or JPG renamed to .png)
- File size: under 1 MB for fast loading
- URL it must live at: `https://courant.bryanbradfo.me/og-image.png`

## What to put in it

Suggested content:

- "Courant" wordmark in Fraunces font (large, centered)
- Tagline: "Cozy reminders for developers"
- A frame from the cozy-cabin or night-train scene as background
- The install command `pipx install courant` in JetBrains Mono
- Subtle branding (water-drop favicon icon)

## How to generate

Options:

1. Capture a 1200x630 screenshot of the landing page hero in a browser
   (Firefox/Chrome devtools can set a custom viewport).
2. Compose in Figma / Inkscape using the same fonts and colors as the site.
3. Use a tool like `playwright` to render the hero at the right dimensions.

Once generated, drop it at `web/og-image.png` and delete this README and
the sibling `og-image.png.placeholder` file.
