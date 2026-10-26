# Move existing text into navigation on the same slide

## Required behavior

1. The original roadmap label is visible in the initial frame.
2. One click on that slide moves and shrinks the same object over 1.2 seconds.
3. Once the label reaches its navigation position, reveal the body content or photos below it.
4. The next click advances to the next logical slide. Do not insert a static intermediate slide that repeats the photos.

An entrance animation on an empty next slide, a full-slide transition, or swapping the original for a new label does not satisfy this behavior.

## Implementation

- `bs-focus`: the original editable text object. Both `animMotion` and `animScale` target its current shape ID.
- `bs-anchor`: the actual destination box. Motion is the difference between object centers divided by slide dimensions. Scale is the destination font size divided by the source font size.
- `bs-reveal-*`: content placed beneath the black `bs-mask` before it is revealed.
- `bs-exit-*`: the remaining roadmap objects. They disappear during the motion; `bs-focus` receives neither entrance nor exit effects.
- The main timeline sequence waits for a click on the current slide. The reveal belongs to that same click group.
- In the static deck, place the same label at the destination size and coordinates, then remove the mask, roadmap objects, and timeline. Keep the logical slide count unchanged.

The scripts patch only slide XML in PptxGenJS-generated drafts. Verify that other ZIP parts, including relationships, media, and notes, remain unchanged. Do not apply this patch to arbitrary third-party PPTX files.

## Regression checks after edits

| Change | What to verify |
| --- | --- |
| Navigation wording | Source and destination labels match exactly; target IDs point to actual objects |
| Navigation order | Destination center coordinates are recalculated |
| Slide insertion or removal | Effects stay on the actual roadmap rather than a fixed slide number |
| Photo insertion or replacement | Aspect ratios, labels, and borders remain intact; the same click reveals them |
| PDF export | Completed states appear without duplicate pages or a black mask |
| Font changes | Text fits with the actual font, which is also available on the presentation computer |

`npm test` checks object identity, path calculation, reordering, static output, and relationships. Verify actual PowerPoint behavior, presentation-computer readability, and click timing through a separate playback session.

## Official references

- [PptxGenJS text](https://gitbrent.github.io/PptxGenJS/docs/api-text/)
- [PptxGenJS image sizing](https://gitbrent.github.io/PptxGenJS/docs/api-images/)
- [Microsoft PresentationML animation](https://learn.microsoft.com/en-us/office/open-xml/presentation/working-with-animation)
- [Microsoft AnimateScale](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.presentation.animatescale)
