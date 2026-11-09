---
name: real-logos
description: Puts the real, official logo on screen whenever a product, app, company or AI tool is named (ChatGPT, Claude, Cursor, Notion, GitHub, any brand) in a video, reel, thumbnail, slide or design, and saves every logo to one local library so it is downloaded once and reused in every project. Use whenever a logo or brand icon is needed, the user says "add the X logo", or a script or caption names a product. Never draws, generates or imitates a logo.
---

# Real Logos

Two rules, every time:

1. **Only the real logo.** It comes from the brand's own files. Never draw one, generate one with AI, retype a wordmark in a similar font, or grab a lookalike from an icon pack or an image search thumbnail.
2. **Download once, keep forever.** Every logo goes into one library on this computer. Before searching the web, look in the library. A logo already saved is never downloaded again.

The library is `~/.real-logos` (all projects share it; set `REAL_LOGOS_DIR` to move it). `scripts/logos.py` manages it with Python's standard library, no installs. Below, `logos.py` means `python <this skill's folder>/scripts/logos.py`.

## 1. Look in the library first

```bash
python logos.py find <brand>
```

- `OK` with the variant you need → use that file. **Stop here: no web search.**
- `MISSING` → the file was moved or deleted. Look for it before downloading again.
- Not found → go to step 2, only for the logos this project actually needs.

## 2. Find the official file

Try in this order and stop at the first good **SVG** (it stays sharp at any size; take a PNG only when no SVG exists):

1. The brand's own press, media or brand-assets page (search "<brand> press kit", "<brand> brand guidelines", "<brand> brand assets").
2. The brand's official website or GitHub organisation (logo files in their repos or docs).
3. Wikimedia Commons, **only** when its file page shows the logo comes from the brand's own artwork. Say so in `--notes`.

Pick the variant that fits the background: the color logo on light backgrounds, the white or "for dark backgrounds" version on dark ones. Save each variant you use as its own entry.

If nothing official exists, don't make one. Tell the user, and use the brand name as plain text instead.

## 3. Download and check it

Download into a temporary folder (not the project), then look at it before saving:

- Open it in a browser or image viewer and confirm it is the real, current logo: right shape, spelling and colors. Brands redesign, so prefer the version on their site today.
- The edges are tight around the logo, with no big empty margin. If not, make a trimmed copy and save it with `--from` (step 4). Never edit the original.

## 4. Save it to the library

```bash
python logos.py add <downloaded file> --brand "<Brand>" --variant <color|white|black|symbol|wordmark…> \
  --source "<the official page you got it from>" --aliases "<product names, common misspellings>" --move
```

The script refuses a web page saved as `.svg`, a picture wrapped in an SVG, or a broken PNG, and says when the same file is already saved (reuse that one). For a copy you made from a saved logo (trimmed, recolored white for a dark video, exported to PNG) add `--from <original id>` instead of `--source`.

## 5. Use it in the project

```bash
python logos.py path <brand> --variant white --format png
```

prints the file's full path. Use the file where it is, or copy it into the project when the editor needs it there, but always save new logos to the library first.

- **Editors that take PNG only (CapCut, some phone apps):** use the brand's official PNG, or turn the SVG into a large PNG (at least 1000 px wide, transparent background) with any converter you have, then save that PNG with `--from`.
- **On screen:** show the logo while the product is named, at a size people can recognise on a phone. Never put it over a face, the main subject or the captions, and keep its original proportions and colors (no stretching, cropping or recoloring, except the brand's own white or black version on a dark or light background).
- Logos shown side by side get the same box size, so none looks bigger than the others.

## 6. Report

At the end, list the logos you used, which ones were newly saved to the library, and any brand with no official logo found.
