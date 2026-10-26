---
name: blackstage-pptx
description: Create or revise black-background PPTX decks with large bold text and concise top navigation. Includes same-slide roadmap-to-navigation text motion and static PDF handouts. Use for this presentation style, not arbitrary PPTX conversion.
---

# Blackstage PPTX

Use the scripts in this directory to create generic presentations. When preserving this style, do not introduce decorative cards, extra ornaments, or small text. This is a JSON-based generator, not a lossless importer or editor for arbitrary existing PPTX files.

## Setup and execution

Treat this directory as the repository root. Follow `README.md` for commands and input fields, starting from `examples/demo.json`. Requires Node.js 20+, Python 3.10+, and `npm ci`; LibreOffice is needed only for PDF conversion. Image paths are relative to the input JSON file.

```bash
node scripts/build.mjs spec.json output/deck-v1.pptx --pdf
npm test
```

Check input paths, output paths, and supported slide types before running the scripts. The built-in layout supports 16:9 slides, up to four navigation sections, up to six agenda entries, three-step roadmaps, and 2x2 photo grids. If a request exceeds those limits, explain the constraint and use an appropriate implementation.

## Style

- Use a black background, white body text, light-gray inactive navigation, and `#FFD54A` for dates only. The default font is NanumGothic Bold. Check its availability on the presentation computer and disclose any substitution.
- Use approximately 65-74 pt titles, 39 pt body text, and 27 pt navigation labels. Split long copy rather than hiding overflow with shrinking or unwanted wrapping. Check content accuracy separately from geometry.
- Hide navigation on covers, agenda slides, and standalone titles when appropriate. The agenda and top navigation are independent; removing a navigation entry does not imply deleting its slide.
- Keep repeated information at consistent positions and sizes. Use a title and at most two body lines; put supporting explanations in `notes`.
- Contain photos and posters without cropping. Group multiple photos in 2x2 layouts with large labels and borders. Do not invent missing photos, links, QR codes, or content.
- Calculate weekdays from ISO dates. Keep labels and times white. Apply spelling changes consistently to related slides and motion destinations.

## Motion and revisions

For moving text, read [references/continuous-motion.md](references/continuous-motion.md). On the first click, the original visible roadmap object must shrink and move into the navigation, followed by a content or photo reveal on the same slide. Do not substitute a new text entrance on the next slide.

For full regeneration, edit the JSON and rerun the generator. Connect sections through stable IDs, not fixed slide or shape numbers. Do not assume an import/export round trip preserves timelines. Preserve existing user files and use new output names. After changing navigation, slides, posters, or photo order, run `npm test` and inspect the new outputs.

## Verification and delivery

1. Inspect `.checks.json` and run `python3 scripts/pptx.py check output/deck-v1.pptx` for structure, targets, and relationships. These checks do not prove PowerPoint playback.
2. Use `*.static.pptx` as the separate completed-state source for PDF conversion. Do not insert duplicate handout slides into the playable deck.
3. Render every slide and inspect aspect ratios, readability, clipping, and spelling. Successful PDF conversion or text extraction does not prove Korean glyphs are visible. Copy conversion fonts only into the temporary macOS profile; if automatic discovery fails, use `BLACKSTAGE_FONT_DIR` as documented in `README.md`. Do not change system font settings.
4. If PowerPoint slideshow playback is available, check the initial frame, first-click motion and scaling, same-slide reveal, and next-click advance. Otherwise state that actual PowerPoint playback is unverified. Do not describe LibreOffice or PDF previews as PowerPoint playback verification.
5. Deliver only the requested PPT and PDF files. If the attachment tool requires managed media, copy the final files there and confirm successful delivery. For ambiguous delivery, check status before retrying. Local validation and external delivery are separate outcomes.

Use neutral project content in public examples. Do not publish real user copy, photos, event details, conversation transcripts, or local paths.
