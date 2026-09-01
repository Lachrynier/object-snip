# ObjectSnip

ObjectSnip provides a quick way to extract an object from anything visible on
your screen. Capture a region, click the object, refine the generated mask, and
copy the result as a transparent image -- all within one integrated workflow.

Object selection is powered by SAM 2.1, a promptable image-segmentation
foundation model. The model runs fully on your computer and provides fast feedback as you
adjust the selection.

The workflow is:

1. Start a capture from the system tray or with the keyboard shortcut
   (`Super+Shift+O`).
2. Draw and adjust a region around the object, then choose **Lock region**.
3. Add a positive point to include part of the object or a negative point to
   exclude an area.
4. Review the generated masks and choose the best one. The chosen mask is used
   as the starting point for the next adjustment.
5. Repeat the previous two steps until the selection is right.
6. Copy the transparent cutout to the clipboard or save it as a PNG.

> [!IMPORTANT]
> ObjectSnip now provides the complete capture, selection, refinement, and
> export workflow. It has only been tested on Fedora with a Wayland session;
> other Linux distributions, desktop environments, display servers, and
> operating systems are currently unverified.

## Examples

<!-- TODO: Add a GIF or video demonstrating the complete workflow. -->

ObjectSnip can be used for tasks such as:

- extracting an object or person from media for use in a slide;
- removing a distracting background from a portrait to create a clean profile picture;
- isolating a diagram or figure for use in notes or documentation;
- preparing visual elements for design, mockup, or media creation;
- making a quick transparent cutout when opening a photo editor would be
  tedious.

Keeping capture, selection, and refinement in one workflow avoids moving a
screenshot through a separate photo editor or uploading it to a web service.

## Selection controls

- **Positive**: add a point that belongs to the object.
- **Negative**: add a point that should be excluded.
- Click an existing marker to remove it.
- **Mask 1–3**: choose between the candidates generated after each prompt.
- Mouse wheel: zoom toward the pointer.
- **Pan** drag or middle-button drag: move a zoomed image.
- **Reset prompts**: remove all points and generated masks.
- **Reset zoom**: return to the centered fit-to-window view.
- **Copy object**: copy the selected object as a tightly cropped image with a
  transparent background.
- **Save object as PNG**: choose a destination and save the same transparent
  cutout as a PNG file.


## Requirements

The current development build requires:

- Fedora with Wayland and a system tray (the only configuration tested so far);
- Python 3.12 or newer;
- [`uv`](https://docs.astral.sh/uv/);
- enough memory and storage to run the selected SAM 2.1 model.

Available model sizes are `tiny`, `small`, `base-plus`, and `large`. The default
is `small`.

On Wayland, screen capture and the global shortcut use XDG desktop portals. The
desktop may ask for permission or allow you to choose a different shortcut.
The code includes a direct screen-capture path for other Qt platforms, but it
has not yet been validated outside the Fedora Wayland setup.

## Install and run

ObjectSnip does not yet provide a packaged release. Install the development
environment from the repository with:

```bash
uv sync
```

Start ObjectSnip with the model you want to use:

```text
uv run objectsnip [--model <model>]
```

`<model>` may be one of:

- `tiny`
- `small` (default)
- `base-plus`
- `large`

If `--model` is omitted, ObjectSnip uses `small`. When the selected model is
not already present in `.models`, ObjectSnip says that it is downloading the
checkpoint and displays its progress, speed, and ETA in the terminal. It then
verifies and installs the checkpoint automatically before starting.

For example:

```bash
uv run objectsnip --model small
```

ObjectSnip remains available from the system tray. Right-click its icon, choose
**Capture region**, or press `Super+Shift+O` to begin.

Keep the context region reasonably close to square when practical. SAM resizes
each input to `1024 × 1024`, so extremely wide or tall regions give the object
fewer effective pixels.

## License

ObjectSnip is licensed under the
[GNU Affero General Public License v3.0 or later](LICENSE).
