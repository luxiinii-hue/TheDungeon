# Dungeon of the Acoc — ATB Lane Combat Pivot

## Vision

Replace the real-time side-scroller (WASD + dodge) with a **Single-Lane ATB (Active Time Battle)** system inspired by Darkest Dungeon's positioning and Final Fantasy's speed bars. Combat is continuous and real-time but driven by speed bars rather than twitch movement.

---

## Layout (1D Lane)

```
Position 4    3    2    1          1    2    3    4
(Back)                (Front)  (Front)              (Back)

[Ranger] [Mage] [Pala] [Barb]  ~~~projectiles~~~  [Slime] [Goblin] [Bat] [Boss]
  ▓▓▓░    ▓▓░░   ▓▓▓▓   ▓▓▓░   →→→  ←←←  →→→    ▓▓░░    ▓▓▓░    ▓░░░   ▓▓▓▓
  SPD BAR  SPD    SPD    SPD                        SPD     SPD     SPD    SPD

|<-------- Player Team -------->|                  |<------- Enemy Team ------->|
```

- **Screen**: 1280x720 (unchanged)
- **Player team** arranged left side, positions 1-4 (front to back), evenly spaced
- **Enemy team** arranged right side, positions 1-4 (front to back), evenly spaced
- **No free movement** — characters are fixed at their rank position
- **Projectiles** travel horizontally between the two sides
- **HUD**: bottom strip for speed bars, ability icons, HP

### Position Coordinates (approximate)

Player team x-positions (front=1 to back=4): ~350, 250, 150, 50 (+ offset)
Enemy team x-positions (front=1 to back=4): ~930, 1030, 1130, 1230 (+ offset)
Y-positions: vertically centered with slight stagger per rank

---

## Core Mechanics

### Speed/ATB Bar System

Every unit has a **speed bar** that fills continuously based on their speed stat:

```
fill_rate = base_fill_rate * (1 + speed * speed_scaling)
```

- Bar range: 0.0 → 1.0
- When bar reaches 1.0: unit fires auto-attack, bar resets to 0.0
- Stunned units: bar paused (does not fill)
- Haste/slow buffs: multiply fill_rate

### Auto-Attacks

When a unit's speed bar fills:
- **Melee units** (position 1-2): attack the front-most living enemy (position 1 priority)
- **Ranged units** (position 3-4): projectile can target any enemy rank; defaults to lowest-HP or front
- Projectile spawns at attacker's position, travels horizontally to target
- Damage: `strength * auto_attack_scaling - target.armor * armor_factor`

### Abilities

Abilities have their own cooldown timers (seconds-based, independent of speed bar):

- **Player-controlled unit**: abilities are manually activated via click/hotkey (1-4) when off cooldown. Auto-attacks still fire automatically via speed bar.
- **AI allies**: use abilities automatically when off cooldown, choosing randomly or by priority
- **Enemies**: same as AI allies

Ability targeting respects position:
- "single_enemy" melee abilities: can only target position 1-2
- "single_enemy" ranged abilities: can target any position
- "all_enemies": hits all living enemies
- "single_ally" / "all_allies" / "self": unchanged

### Position-Based Mechanics

- **Front line (pos 1-2)**: takes hits first, melee attacks available, higher threat
- **Back line (pos 3-4)**: protected from melee, ranged attacks, support abilities
- Some abilities can **push/pull** units (change rank position):
  - Push: target moves back 1 rank (pos 1→2)
  - Pull: target moves forward 1 rank (pos 3→2)
  - If destination occupied, swap positions
- When front unit dies, remaining units slide forward (pos 2→1, 3→2, etc.)

---

## What Changes vs. Previous System

| Component | Old (Side-Scroller) | New (ATB Lane) |
|---|---|---|
| Movement | WASD free 2D movement | Fixed rank positions (no player movement) |
| Attack trigger | Timer-based auto-fire | Speed bar fills → auto-attack |
| Player interaction | Dodge + click abilities | Click abilities only (timing matters) |
| Positioning | Pixel x,y coords | Rank 1-4 integer |
| AI allies | Follow player, random ability use | Fixed rank, auto-ability on cooldown |
| Targeting | Nearest enemy by distance | Rank-based (melee=front, ranged=any) |
| Projectiles | Fly freely, collision detection | Fly to specific target rank, guaranteed hit |
| Dodging | Move out of projectile path | No dodge (position-based defense instead) |

### Files Impact

| File | Action | Notes |
|---|---|---|
| `combat_state.py` | **HEAVY REWRITE** | Remove WASD, add speed bar rendering, rank-based layout |
| `realtime_battle.py` | **HEAVY REWRITE** | Replace projectile-spam loop with ATB tick system |
| `unit.py` | **MODIFY** | Replace x,y with `rank: int`, add `speed_bar: float`, remove `attack_timer` |
| `ability.py` | **MODIFY** | Add `range` field (melee/ranged), add push/pull effect types |
| `projectile.py` | **SIMPLIFY** | Targeted projectiles (no collision detection, fly to rank x-pos) |
| `ai_controller.py` | **REWRITE** | Remove positioning logic, add ability priority/targeting by rank |
| `targeting.py` | **REWRITE** | Rank-based targeting (front priority for melee, any for ranged) |
| `config.py` | **MODIFY** | Replace zone constants with rank position constants, ATB tuning |
| `abilities.json` | **MODIFY** | Add range field, adjust targeting for rank system |
| `characters.json` | **MODIFY** | Add default_rank or preferred_position per character |
| `idle_animator.py` | PRESERVED | Still renders sprites at computed rank positions |
| `ability_animator.py` | PRESERVED | Impact effects at target rank position |
| `combat_animator.py` | PRESERVED | Hit flash, knockback (now horizontal shift at rank) |
| `particles.py` | PRESERVED | Hit sparks, death bursts |
| `run_manager.py` | PRESERVED | Unchanged |
| `auto_battle.py` | DELETE or IGNORE | Fully superseded |

---

## ATB Tick System (combat loop detail)

Each frame (`dt` = time since last frame):

```
for each living unit:
    if unit.stunned: continue

    # 1. Fill speed bar
    unit.speed_bar += fill_rate(unit.speed) * dt

    # 2. Check if bar full
    if unit.speed_bar >= 1.0:
        unit.speed_bar = 0.0

        # 3. Determine target based on rank
        target = select_target(unit, enemy_team)

        # 4. Spawn auto-attack projectile toward target
        spawn_projectile(unit, target, is_auto=True)

    # 5. Tick ability cooldowns
    unit.tick_cooldowns_rt(dt)

    # 6. AI ability usage (non-player units)
    if unit is not player_controlled and has_ready_ability(unit):
        use_random_ability(unit)

# 7. Update all active projectiles (move toward target)
for projectile in active_projectiles:
    projectile.update(dt)
    if projectile.reached_target():
        apply_damage(projectile)
        remove(projectile)

# 8. Tick buffs (burn, stun duration)
for each living unit:
    unit.tick_buffs_rt(dt)

# 9. Check win/lose
if all enemies dead: victory
if all players dead: defeat
```

---

## Agent Division of Labor

### Claude Code — Core Systems & Logic

Claude builds the ATB engine, rank system, targeting logic, and data schema changes.

| Priority | Task | Key Files |
|----------|------|-----------|
| 1 | Define rank position constants and ATB tuning in config | `config.py` |
| 2 | Modify CombatUnit: replace x/y with rank, add speed_bar, remove attack_timer | `unit.py` |
| 3 | Add range field to AbilityDef, push/pull effect types | `ability.py` |
| 4 | Rewrite RealtimeBattle as ATB tick engine | `realtime_battle.py` |
| 5 | Rewrite targeting.py for rank-based targeting | `targeting.py` |
| 6 | Simplify Projectile to targeted (no collision, fly to rank) | `projectile.py` |
| 7 | Rewrite AIController for rank-aware ability selection | `ai_controller.py` |
| 8 | Rewrite combat_state.py structure: ATB loop, input, rank layout | `combat_state.py` |
| 9 | Update abilities.json with range fields | `data/abilities.json` |
| 10 | Update characters.json with default_rank | `data/characters.json` |
| 11 | Death rank-slide logic (units shift forward when front dies) | `realtime_battle.py` |
| 12 | Victory/defeat transitions | `combat_state.py`, `realtime_battle.py` |

### Gemini CLI — Visual / UI / Frontend

Gemini handles speed bar UI, rank layout rendering, ability animations, and visual polish.

| Priority | Task | Key Files |
|----------|------|-----------|
| 1 | Speed bar UI widget (per-unit fill bar, class-colored) | `src/ui/speed_bar.py` (new) |
| 2 | Rank-based unit rendering (draw units at computed rank positions) | `combat_state.py` (draw) |
| 3 | Ability HUD update (adapt for no-movement, rank context) | `src/ui/ability_hud.py` |
| 4 | Projectile flight animation (smooth travel from rank to rank) | `combat_state.py` (draw) |
| 5 | Rank position push/pull animation (unit slides between ranks) | `src/animation/combat_animator.py` |
| 6 | Combat background (Darkest Dungeon corridor style) | `combat_state.py` (background) |
| 7 | Turn indicator / "ready!" flash when speed bar fills | Visual polish |
| 8 | Death animation + rank collapse visual (units slide forward) | `combat_state.py`, `particles.py` |

### Coordination Rules

- Claude completes structural combat_state.py rewrite (Sprint 1) before Gemini layers visuals
- `config.py`: Claude uses `# ATB combat` section, Gemini uses `# Visual tuning` section
- `abilities.json`: Claude owns schema, Gemini tunes visual values
- `todo.md` remains single source of truth for task status

---

## Implementation Sprints

### Sprint 1: ATB Prototype (Claude leads)

Get the ATB tick loop running with rank positions and auto-attacks.

1. Config: rank positions, ATB fill rates, targeting constants
2. Unit: rank field, speed_bar, remove x/y movement
3. RealtimeBattle: ATB tick loop (fill bars → fire → projectiles → damage)
4. Targeting: front-priority melee, any-rank ranged
5. Projectile: targeted (fly to rank, guaranteed hit on arrival)
6. combat_state.py: wire ATB battle, draw units at ranks, basic speed bars
7. **Milestone**: units auto-attack based on speed bars, damage flows, win/lose works

### Sprint 2: Abilities & AI (Claude + Gemini parallel)

- **Claude**: ability firing with rank targeting, AI controller, cooldowns, push/pull effects, player ability input
- **Gemini**: speed bar widget, rank rendering polish, ability HUD, projectile visuals
- **Milestone**: full ATB combat with abilities, AI, proper speed bar UI

### Sprint 3: Polish & Balance (Both)

- Balance: speed scaling, damage, cooldowns, rank advantages
- Visual: corridor background, turn indicators, death animations, rank-slide animation
- Data: tune all abilities for rank system, add range fields
- **Milestone**: combat feels complete, Darkest Dungeon-style lane battles
