# open1320-modder

Car modding tools for Nitto Legends (open1320 / nittolol clients).

## Tools

- **1320CarModder.exe** — Car & rim editor with wheel/plate aligner
- **Car Installer.exe** — Downloads and installs cars and rim packs from nitto.lol

## Changelog

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
