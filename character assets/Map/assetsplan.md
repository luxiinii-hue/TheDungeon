# Gothic City Map Assets Plan

This directory contains the new high-quality props and building assets for the **Gothic City of the Acoc** map. These assets replace the generic `UI/icons/node_*.png` icons to provide a more immersive "street navigation" feel.

## 1. Node Type Mapping

| Map Node Type | Asset File | Visual Description |
| :--- | :--- | :--- |
| **Boss** | `chuch.png` | Large gothic cathedral (landmark) |
| **Combat** | `house-a.png` | Standard gothic town house |
| **Elite** | `house-b.png` | Different style town house |
| **Event** | `house-c.png` | Distinct architecture for storytelling |
| **Shop** | `wagon.png` | Traveling merchant's wagon |
| **Treasure** | `crate-stack.png` | Looted/abandoned supplies |
| **Rest** | `well.png` | Public well for recovery |
| **Start** | `street-lamp.png` | Entrance to the city streets |

## 2. Decorative Clutter (Atmospheric)

These assets can be randomly scattered between nodes to add detail to the city streets:
- `barrel.png`
- `crate.png`
- `sign.png`

## 3. Implementation Plan

### Step A: Update `MapState._draw_node`
Currently, the map state looks for icons in `UI/icons/node_{type}.png`.
1.  **New Path**: Update the search path to `Map/{asset_name}` based on the node type.
2.  **Asset Scaling**: Since these buildings are larger than simple icons, adjust `am.get_scaled` in `map_state.py` to use a larger base size (e.g., `(64, 64)` or higher).
3.  **Positioning**: Buildings should be drawn so their "base" sits on the node coordinate, or centered if preferred.

### Step B: Add Decorative Elements
1.  **Background Clutter**: In `MapState.enter`, generate a set of random decorative positions using the clutter assets (`barrel`, `sign`).
2.  **Connection Markers**: Use `street-lamp.png` as a marker halfway between connected nodes to "light the path".

### Step C: Visual Consistency
- Ensure these assets are slightly tinted or darkened (using `pygame.BLEND_RGBA_MULT`) when a node is **not yet available** or **already visited** to maintain the same UI feedback as the original circles/icons.
