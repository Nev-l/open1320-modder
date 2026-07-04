# open1320-modder

Car modding tools for Nitto Legends (open1320 / nittolol clients).

## Tools

- **1320CarModder.exe** — Car & rim editor with wheel/plate aligner
- **Car Installer.exe** — Downloads and installs cars and rim packs from nitto.lol

## Changelog

### v0.3.6
- **Fix rim images loading incorrectly from source SWF**: `export_all_images` was reusing the same output directory across calls without clearing it. Stale `{char_id}.png` files from previous extractions would accumulate and be picked up by `glob`, causing the wrong image to be returned. Directory is now wiped clean before each FFDec export.
- **Fix rim FF (and any view) sometimes not rewritten on rebuild**: when the source and output SWF path are the same file (rebuilding same slot), FFDec could open the output for writing before finishing the read, producing an empty or unchanged result. Source is now copied to a temp file first when src == dst.

### v0.3.5
- **Fix rim builder — FF view outputs original rim**: two root causes: (1) `_build_worker` was reading tkinter `Scale` variables (`_tint_str`, `_bri`) from a non-main thread — Tcl is not thread-safe so the first view in the loop (always FF) could silently read stale 0 values instead of the user-set strength/brightness, producing an untinted output while FR/BF/BR got the correct values. Fixed by snapshotting all tkinter variables on the main thread before spawning the worker. (2) After a build, `_RIM_MEM` was storing the post-tint (tinted) image, so reloading the same slot would use the already-tinted image as the base for the NEXT build, compounding tints. Fixed by storing the pre-tint base image in the cache instead.
- **Fix rim builder — wrong char_id selected when SWF has multiple bitmaps**: used `list(imgs.keys())[0]` (arbitrary dict order) instead of the char_id of the largest bitmap, which could replace a mask/secondary bitmap and leave the main rim unchanged. Now mirrors `export_image`'s `max(..., key=getsize)` logic.

### v0.3.4
- **Fix Part Builder — image not appearing**: browsing an image now always triggers a canvas render, even when no template SWF is loaded yet
- **Fix Part Builder — user image alpha**: replaced `paste(img, mask=img)` with `alpha_composite` so semi-transparent pixels composite correctly without double-applying the alpha channel
- **Fix decal layer resetting mid-drag**: moving a decal slider was triggering a full slot reload (which reset the decal listbox selection and slider positions) because the "modified ★" label update briefly cleared the parts listbox selection and fired `<<ListboxSelect>>`. A guard flag now blocks that spurious reload during the label update.

### v0.3.3
- **Part Builder tab** — new dedicated tab for building custom car parts from existing templates. Pick any part type (hood, bumper, body, roof, etc.) and any car in the cache as a reference. Two canvas views:
  - **Align view** — template image shown semi-transparent; drag your custom image over it to position, Scale %, X/Y offset spinboxes, arrow key nudge, scroll to zoom, auto-fit/center helpers
  - **Car preview** — renders the full currently-loaded car composite with your custom part swapped in, so you can see exactly how it sits on the car before building
- Build replaces the exact bitmap character in the template SWF (same stage size, same paint clips preserved) — no more guessing dimensions.

### v0.3.2
- **Publish to GitHub — pre-flight checklist** — clicking "Publish to GitHub" now opens a dialog that scans the cache and shows every file with a NEW / CHANGED / SAME badge. New and changed files are pre-ticked; identical files are hidden by default (toggle "Show identical files" to reveal them with a note). Tick/untick any files before publishing. A filter box lets you search by path. Only the selected files are copied + committed + pushed.

### v0.3.1
- **Fix in-game paint shop** — mod cars (e.g. sourced from car 1002) have their car body SWF placed as `noPaint` instead of `paint`, causing `CarConstruction.initPart` to leave the Color object unset so `setPartColor` does nothing. The builder now detects this and renames the clip to `paint` in any output SWF that lacks one, making the paint shop work correctly for those cars.

### v0.3.0
- **Fix plate alignment** — the game positions the plate using `bumperRear.actual.p1._x` (PlaceObject2 matrix data inside `bumperRear.swf`), not via the standalone `p1-p4.swf` files. The aligner now reads/writes the correct source: `parse_plate_bumper_swf` / `patch_plate_bumper_swf` decode and patch the bit-packed SWF matrix in-place. Default corner values updated to match actual game positions.
- The standalone `p1-p4.swf` files are still copied unchanged (game still expects them present)

### v0.2.9
- Fixed plate coordinates never saving: build now always writes current tx/ty to p1-p4 SWFs instead of skipping when "unchanged" (the old diff check against `_plate_src` was always zero when source had no plate files)
- Plate quad on canvas now shows as a semi-transparent filled polygon with a solid yellow outline, coordinate labels on each corner handle, and a centre crosshair handle — makes it much easier to see where the plate sits on the car

### v0.2.8
- Wheel/plate aligner rebuilt: all controls now in a panel **above** the canvas (no side panel that collapses)
- Added **plate centre-point drag handle** (⊕) — drag it to move all 4 plate corners together
- Fixed custom/recolored rim thumbnails not updating in the Rim Browser after a build — cache is now invalidated and updated with the modified image on build

### v0.2.7
- Fix wheel aligner right panel not visible (W%/H% spinboxes + Plate tab)

### v0.2.6
- Publish to GitHub button — syncs modified cache files to nitto-legends-cache repo and pushes

### v0.2.5
- Custom rim folder now supports subfolders — each subfolder is one rim pack (4 SWFs), picker shown on load

### v0.2.4
- Fix rim preview not loading in Car Installer

### v0.2.3
- Rim pack server upload to nitto.lol (port 8184)
- Car Installer: added Rims tab alongside Cars tab

### v0.2.2
- Fix custom SWF rims not displaying (blank images)

### v0.2.1
- Direct SWF bitmap extraction — no FFDec required for rim previews (handles DefineBitsJPEG3/tag 35)

### v0.2.0
- Rim image cache (disk + memory) to avoid repeated FFDec extractions

### v0.1.x
- Rim editor: tint/brightness/custom image per view, Apply-to-All
- Rim browser: scrollable thumbnail grid
- Wheel/plate aligner: drag handles, arrow-key nudge, tire/rim overlay loading
- Plate corner drag (p1–p4)
- Badge editor, decal editor, car part image replacement
