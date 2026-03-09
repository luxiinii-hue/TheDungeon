# Real-Time Side-Scroller Combat — Task Tracker

> **Coordination file for Claude Code and Gemini CLI.**
> Check this file before starting any task. Update status when you start and finish.
> Format: `TODO` → `IN PROGRESS (Claude|Gemini)` → `DONE`

---

## Sprint 1: Playable Prototype (Claude leads)

| # | Task | Owner | Status | Files | Depends On |
|---|------|-------|--------|-------|------------|
| 1.1 | Create Projectile class | Claude | DONE | `src/combat/projectile.py` | — |
| 1.2 | Add real-time combat constants | Claude | DONE | `config.py` | — |
| 1.3 | Extend CombatUnit (x, y, attack_timer, attack_interval) | Claude | DONE | `src/combat/unit.py` | — |
| 1.4 | Extend AbilityDef (projectile config fields) | Claude | DONE | `src/combat/ability.py` | — |
| 1.5 | Add projectile_config to abilities.json | Claude | DONE | `data/abilities.json` | 1.4 |
| 1.6 | Create RealtimeBattle engine | Claude | DONE | `src/combat/realtime_battle.py` | 1.1, 1.3 |
| 1.7 | Rewrite combat_state.py (structural) | Claude | DONE | `src/states/combat_state.py` | 1.1–1.6 |
| 1.8 | WASD player movement | Claude | DONE | `src/states/combat_state.py` | 1.7 |
| 1.9 | Basic projectile rendering (circles/rects) | Claude | DONE | `src/states/combat_state.py` | 1.7 |
| 1.10 | Adapt targeting.py (nearest enemy) | Claude | DONE | `src/combat/targeting.py` | — |

**Sprint 1 Milestone**: Player moves with WASD, auto-attacks fly as projectiles, enemies take damage and can be defeated.

---

## Sprint 2: Gameplay Layer (Parallel)

| # | Task | Owner | Status | Files | Depends On |
|---|------|-------|--------|-------|------------|
| 2.1 | AI controller (ally positioning + abilities) | Claude | DONE | `src/combat/ai_controller.py` | 1.6 |
| 2.2 | Player ability firing (click/keyboard) | Claude | DONE | `src/states/combat_state.py` | 1.7, 1.8 |
| 2.3 | Cooldown system (per-unit ability timers) | Claude | DONE | `src/combat/realtime_battle.py` | 1.6 |
| 2.4 | Passive effects in real-time context | Claude | DONE | `src/combat/realtime_battle.py` | 1.6 |
| 2.5 | Victory/defeat transitions | Claude | DONE | `src/states/combat_state.py`, `realtime_battle.py` | 1.7 |
| 2.6 | Ability HUD (icons, cooldown overlay, hotkeys) | Gemini | DONE | `src/ui/ability_hud.py` | 1.7 |
| 2.7 | Projectile sprites per class/ability | Gemini | DONE | `character assets/`, configs | 1.1 |
| 2.8 | Unit rendering at x,y with IdleAnimator | Gemini | DONE | `src/states/combat_state.py` (draw) | 1.7 DONE |
| 2.9 | Projectile trail + impact particles | Gemini | DONE | `src/animation/particles.py` | 1.1 |
| 2.10 | Ability impact animations at hit position | Gemini | DONE | `src/animation/ability_animator.py` | 1.7 DONE |
| 2.11 | HP bars above units at their position | Gemini | DONE | `src/states/combat_state.py` (draw) | 2.8 |

**Sprint 2 Milestone**: Full combat with abilities, AI allies, proper visuals, and HUD.

---

## Sprint 3: Polish & Balance (Both)

| # | Task | Owner | Status | Files | Depends On |
|---|------|-------|--------|-------|------------|
| 3.1 | Balance attack/projectile speeds | Both | DONE | `config.py`, `data/` | Sprint 2 |
| 3.2 | Combat background (side-scroller style) | Gemini | DONE | `combat_state.py` | Sprint 2 |
| 3.3 | Player-controlled unit highlight/indicator | Gemini | DONE | `combat_state.py` | 2.8 |
| 3.4 | Enemy projectile dodge feedback | Gemini | DONE | particles, animations | 2.9 |
| 3.5 | Boss fight support (large sprites, patterns) | Claude | DONE | `realtime_battle.py`, `combat_state.py` | Sprint 2 |
| 3.6 | Relic/mod integration with real-time | Claude | DONE | `realtime_battle.py` | Sprint 2 |
| 3.7 | Death animations and cleanup | Both | DONE | `combat_state.py`, particles | Sprint 2 |
| 3.8 | Run-manager HP sync after combat | Claude | DONE | `combat_state.py` | 2.5 |

---

## Backlog (Future)

| # | Task | Notes |
|---|------|-------|
| B.1 | Melee enemies that advance into player zone | Requires enemy movement AI |
| B.2 | Multi-tile bosses with attack patterns | Boss-specific projectile sequences |
| B.3 | Multiplayer (second player controls ally) | Swap AI controller for input handler |
| B.4 | Sound effects | Attack, hit, ability, death, dodge |
| B.5 | Screen-relative parallax background | Depth layers scrolling at different rates |

---

## Shared File Rules

| File | Primary Owner | Secondary | Rule |
|------|--------------|-----------|------|
| `combat_state.py` | Claude (Sprint 1) | Gemini (Sprint 2+) | Claude finishes structural rewrite before Gemini touches draw methods |
| `config.py` | Claude | Gemini | Claude uses `# Real-time combat` section; Gemini uses `# Visual tuning` section |
| `abilities.json` | Claude | Gemini | Claude owns schema (field names); Gemini tunes visual values (sprites, tints) |
| `particles.py` | Gemini | Claude | Gemini owns new presets; Claude may call spawn functions |
| `ability_animator.py` | Gemini | — | Gemini only |
| `ability_hud.py` | Gemini | — | Gemini only |

---

## Status Log

_Record major milestones and blockers here:_

| Date | Agent | Note |
|------|-------|------|
| 2026-03-09 | Claude | Sprint 1 complete + Sprint 2 tasks 2.1-2.5 done. All engine/logic tasks finished. Gemini tasks (2.6-2.11) ready to start. |
| 2026-03-09 | Gemini | Started tasks 2.6-2.11. |
| 2026-03-09 | Gemini | Completed tasks 2.6-2.11. Sprint 2 milestone reached! UI/HUD and all visual effects (particles, animations, sprites) integrated. |
| 2026-03-09 | Gemini | Started Sprint 3 tasks (3.1, 3.2, 3.3, 3.4, 3.7). |
| 2026-03-09 | Gemini | Completed visual Polish & Balance tasks (3.1, 3.2, 3.3, 3.4, 3.7) for Sprint 3. |
| 2026-03-09 | Claude | Sprint 3 tasks 3.5, 3.6, 3.8 DONE. Fixed critical bug: armor was not applied in real-time damage calc. Added piercing mod support. Boss fires 3-projectile spread pattern. HP sync already wired. |
