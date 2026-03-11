# Gothic City of Pepruvia

## Asset Conventions
- All game-ready assets live under `character assets/` in organized subdirectories:
  - `Characters/` — playable character sprites
  - `Enemies/` — enemy sprites
  - `Animations/abilities/` — multi-frame ability animation sequences (PNG frames)
  - `UI/icons/` — stat and map node icons (24x24, 32x32)
  - `UI/ability_icons/` — ability effect icons (32x32)
  - `UI/weapon_icons/` — weapon sprites (32x32)
  - `UI/fonts/` — TTF font files
  - `UI/ribbons/set_01..set_18/` — decorative ribbon/banner assets (banner_main, path_horizontal, end_cap, connector_small, frame_icon per set). Used for UI framing, not map paths.
- `Potential assets/` is a staging area for unintegrated free assets. When using an asset from there, copy it into the appropriate permanent subdirectory first — do not reference `Potential assets/` paths in code for new integrations.
- Only PNG format is used in-game. Aseprite/PSD/AI/EPS files are editor source files — do not reference them in code.
- Sprite paths in JSON data files are relative to `ASSET_DIR` (`character assets/`).

## Map Rendering
- Map paths between nodes use procedural bezier curves (`src/map/path_renderer.py`), not tiled ribbon assets.
- Path state (visited/available/locked) controls color and style; constants live in `config.py` under `MAP_PATH_*`.
- Available paths render with animated glow each frame; visited and locked paths are cached once on enter.
