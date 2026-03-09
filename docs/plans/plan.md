# Dungeon of the Acoc — Real-Time Side-Scroller Combat Pivot

## Vision

Replace the turn-based auto-battler with **real-time side-scroller combat** (Castle Crashers / Cuphead style). Party of 2-4 characters on the left, enemies on the right. Auto-attacks fire continuously as horizontal projectiles. One character is player-controlled (WASD movement + clickable abilities with cooldowns), the rest are AI-driven. Designed for future multiplayer.

---

## Layout & Zones

```
|<--- Player Zone (0-400px) --->|<--- No-Man's Land --->|<--- Enemy Zone (880-1280px) --->|
|                                |                       |                                 |
|  [Player]  [AI Ally]           |   ~~~projectiles~~~   |          [Enemy1]  [Enemy2]     |
|            [AI Ally]           |   ~~~projectiles~~~   |          [Enemy3]               |
|                                |                       |                                 |
| Y: 100-600 (playable area)    |                       | Enemies hold positions or drift |
```

- **Screen**: 1280x720 (unchanged)
- **Player zone**: x 40-400, y 100-600 — player character moves freely with WASD
- **Enemy zone**: x 880-1240, y 100-600 — enemies hold positions or drift vertically
- **Projectile travel**: horizontal across the middle gap
- **HUD**: bottom strip (y 620-720) for ability bar, HP, info

---

## Core Mechanics

### Auto-Attacks (All Units)

Every unit fires auto-attacks on a repeating timer derived from speed stat:
```
attack_interval = max(0.5, 2.5 - speed * 0.4)  # seconds between shots
```
- Player units fire rightward, enemy units fire leftward
- Auto-attack projectiles deal `strength`-based damage
- Simple horizontal movement at constant speed (~500 px/s)
- Small sprite or colored circle (class-themed)

### Player Character

- **WASD movement**: free 2D movement within player zone, ~200 px/s
- **Auto-attacks**: fire automatically like everyone else
- **Abilities**: activated via mouse click on HUD buttons or keyboard (1-4)
  - Each ability has a cooldown timer (seconds, from ability data)
  - Abilities spawn special projectiles (larger, animated, more damage)
  - Some abilities are AoE (hit all enemies in a vertical band)
- **Dodge potential**: move vertically to avoid incoming enemy projectiles

### AI Allies

- Auto-attack on their timer (same as all units)
- Use abilities randomly when off cooldown
- Position: maintain loose formation around player character
  - Follow player's Y with offset and slight delay (smooth lerp)
  - Stay in player zone, spread vertically to avoid clustering

### Enemies

- Auto-attack leftward on their timer
- Use abilities when off cooldown (same logic as current enemy AI)
- Hold assigned positions with slight vertical drift/bob
- Phase 1: stationary. Later: melee enemies can advance toward player zone

---

## What Gets Replaced vs Preserved

| Current File | Action | Notes |
|---|---|---|
| `auto_battle.py` | **REPLACED** by `realtime_battle.py` | Turn system → continuous real-time loop |
| `combat_state.py` | **HEAVY REWRITE** | New rendering, input handling, projectile drawing |
| `unit.py` | **EXTENDED** | Add `x, y` position, `attack_timer`, `attack_interval` |
| `ability.py` | **EXTENDED** | Add `projectile_speed`, `projectile_sprite`, `is_aoe` |
| `targeting.py` | **SIMPLIFIED** | Nearest-enemy or all-enemies, no turn order |
| `idle_animator.py` | **PRESERVED** | Renders unit sprites at their x,y position |
| `ability_animator.py` | **PRESERVED** | Impact effects at hit location |
| `combat_animator.py` | **PRESERVED** | Shake/flash on hit |
| `particles.py` | **PRESERVED** | Hit sparks, death bursts, floating numbers |
| `config.py` | **EXTENDED** | Zone boundaries, projectile speeds, attack intervals |
| `run_manager.py` | **PRESERVED** | Run persistence unchanged |
| `state_machine.py` | **PRESERVED** | Same state flow (TITLE→TEAM_SELECT→MAP→COMBAT→REWARD→RESULT) |
| `data/abilities.json` | **EXTENDED** | Add projectile config fields per ability |
| `data/characters.json` | **PRESERVED** | Stats still drive combat math |

---

## New Modules

```
src/combat/
    realtime_battle.py   # NEW — real-time engine: timers, projectile spawning, collision, win/lose
    projectile.py        # NEW — Projectile class: position, velocity, damage, update, draw
    ai_controller.py     # NEW — AI for ally positioning + ability usage
    auto_battle.py       # KEPT as backup, not imported

src/ui/
    ability_hud.py       # NEW — bottom bar: ability icons, cooldown overlays, hotkey labels
```

---

## Damage & Combat Math (Preserved)

```
raw = base_value + strength * scaling
final = max(1, raw - target.armor * 0.5)
```

All passives remain:
- Phase (25% dodge on hit) — projectile passes through with "dodge" effect
- Flame Aura (20% reflect) — on-hit reflect damage
- Rage (+25% dmg below 50% HP) — applied at projectile spawn
- Mana Surge (+10% dmg per N seconds alive) — accumulates over real time

Ability mods remain: vampiric, burning, piercing.

---

## Collision Detection

Simple axis-aligned rectangle overlap:
- Each projectile has a hitbox (e.g., 16x8 px for auto-attacks, larger for abilities)
- Each unit has a hitbox centered on their position (e.g., 60x120 px)
- Check: projectile rect overlaps any enemy unit rect in opposing team
- On hit: apply damage, destroy projectile (or pierce for some abilities), spawn effects
- Projectiles pass through friendly units (no friendly fire)
- Projectiles despawn when off-screen (x < 0 or x > SCREEN_WIDTH)

---

## Agent Division of Labor

### Claude Code — Backend / Engine / Logic

Claude handles the systems architecture, real-time loop, physics, input, and data flow.

| Priority | Task | Files |
|----------|------|-------|
| 1 | `Projectile` class (position, velocity, hitbox, update, collision check) | `src/combat/projectile.py` |
| 2 | `RealtimeBattle` engine (per-frame update: tick timers → spawn projectiles → move projectiles → detect collisions → apply damage → emit BattleAction events → check win/lose) | `src/combat/realtime_battle.py` |
| 3 | Extend `CombatUnit` with `x, y, attack_timer, attack_interval` | `src/combat/unit.py` |
| 4 | Extend `AbilityDef` with `projectile_speed, projectile_sprite, is_aoe` | `src/combat/ability.py` |
| 5 | Add projectile_config to each ability entry | `data/abilities.json` |
| 6 | `AIController` for ally unit positioning + ability timing | `src/combat/ai_controller.py` |
| 7 | Rewrite `combat_state.py` — structural: wire RealtimeBattle, handle WASD input, render units at x,y, draw projectiles, integrate HUD | `src/states/combat_state.py` |
| 8 | Add real-time combat constants to config | `config.py` |
| 9 | Adapt targeting for nearest-enemy / all-enemies | `src/combat/targeting.py` |
| 10 | Death handling, victory/defeat transitions | `realtime_battle.py`, `combat_state.py` |

### Gemini CLI — Frontend / Visuals / UI

Gemini handles visual presentation, animation integration, UI widgets, and asset work.

| Priority | Task | Files |
|----------|------|-------|
| 1 | `AbilityHUD` widget — bottom bar with ability icon buttons, cooldown sweep animation, hotkey labels (1-4), click handling | `src/ui/ability_hud.py` |
| 2 | Projectile sprites — source/create auto-attack and ability projectile art per class, integrate into asset dirs | `character assets/` |
| 3 | Adapt unit rendering — draw player/enemy sprites at their x,y coords using IdleAnimator, with HP bars floating above | `src/states/combat_state.py` (draw methods, after Claude's rewrite) |
| 4 | Projectile trail particles — add particle presets for projectile travel (small trail) and impact (burst) | `src/animation/particles.py` |
| 5 | Ability impact animations — ensure AbilityAnimator plays at correct hit position | `src/animation/ability_animator.py` |
| 6 | Combat background — side-scroller appropriate background with parallax or atmospheric depth | `src/states/combat_state.py` (background) |
| 7 | Player character highlight — subtle glow or indicator showing which unit is player-controlled | Visual polish |
| 8 | Incoming projectile warning — subtle visual cue for dodgeable enemy projectiles | Visual polish |

### Coordination Protocol

- **`todo.md`** is the single source of truth for task status
- Before touching a shared file, check todo.md for `IN PROGRESS` status
- Claude completes the structural `combat_state.py` rewrite first (Sprint 1), then Gemini layers visuals on top (Sprint 2+)
- `config.py` additions: Claude uses `# Real-time combat` section, Gemini uses `# Visual tuning` section
- `abilities.json` changes: Claude adds schema fields, Gemini tunes visual values (sprite paths, tints)

---

## Implementation Order

### Sprint 1: Playable Prototype (Claude, ~solo)
Get projectiles flying across the screen with basic collision and damage.
1. Create `projectile.py` and `realtime_battle.py`
2. Extend `unit.py` and `ability.py`
3. Rewrite `combat_state.py` structurally
4. Basic rendering: units at positions, projectiles as circles, simple HUD
5. WASD movement for player character
6. **Milestone**: you can move, auto-attacks fly, enemies take damage and die

### Sprint 2: Gameplay Layer (Claude + Gemini parallel)
- **Claude**: AI controller, ability firing, cooldown system, passives, win/lose flow
- **Gemini**: Ability HUD, projectile sprites, unit rendering polish, particles
- **Milestone**: full combat loop with abilities, AI allies, proper visuals

### Sprint 3: Polish (Both)
- Balance: attack speeds, projectile speeds, damage, cooldowns
- Visual: backgrounds, trails, impacts, death animations
- Edge cases: multiple enemies, boss fights, relic/mod integration
- **Milestone**: combat feels good, ready to replace auto-battler permanently
