# Contract: Selection view layout

What a browser test can rely on in the Selection tab after this feature.

## Structure

- One list of selected variables: `#basket-cols` (`ol`), one `li` per selected variable,
  after the identifier row. There is no `#basket-list` and no resize grip.
- Each variable row has: the output-column input (`aria-label="Output column name for
  <name>"`), its label, sweep and file, a problem message when there is one, and a
  remove button (`aria-label="Remove <name>"`).
- `#basket-files`: the data files needed (unchanged content).
- `#basket-download-area`: the language checkboxes (R, Python, Stata), the format radios,
  the missing-values checkbox, the download button `#basket-download` and its status line.
- Dropping a dragged variable anywhere on the Selection view adds it.

## Layout rules

| Viewport | Rule |
|---|---|
| ≥ 1024 wide and ≥ 700 tall | The page does not scroll. The list area scrolls on its own; `#basket-download-area` is fully visible at all times. |
| Narrower or shorter | The page scrolls; `#basket-download-area` stays stuck to the bottom of the viewport, showing the download button and a "Download options" toggle that reveals the options. No horizontal scroll at 390px. |

## Unchanged

The empty-selection message, column renaming rules and messages, "Replace every . with _",
file links that open the Variables tab filtered to a file, and the download itself.
