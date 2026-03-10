# ATB Lane Combat — Task Tracker

> **Coordination file for Claude Code and Gemini CLI.**
> Check this file before starting any task. Update status when you start and finish.
> Format: `TODO` → `IN PROGRESS (Claude|Gemini)` → `DONE`

---

## Sprint 1: ATB Prototype (Claude leads)

| # | Task | Owner | Status | Files | Depends On |
|---|------|-------|--------|-------|------------|
| 1.1 | Add ATB/rank constants to config (rank x/y positions, fill rates, targeting) | Claude | DONE | `config.py` | — |
| 1.2 | Modify CombatUnit: add `rank`, `speed_bar`, `reduce_atb()`, remove x/y free-movement | Claude | DONE | `src/combat/unit.py` | — |
| 1.3 | Add `range` field to AbilityDef (melee/ranged), push/pull effect types | Claude | DONE | `src/combat/ability.py` | — |
| 1.4 | Rewrite RealtimeBattle as ATB tick engine (fill bars → trigger attacks → projectiles → damage → win/lose) | Claude | DONE | `src/combat/realtime_battle.py` | 1.1, 1.2 |
| 1.5 | Rewrite targeting.py for rank-based logic (melee=front, ranged=any, front_two) | Claude | DONE | `src/combat/targeting.py` | 1.1 |
| 1.6 | Simplify Projectile to targeted flight (fly to target rank, no collision grid) | Claude | DONE | `src/combat/projectile.py` | 1.1 |
| 1.7 | Rewrite combat_state.py: wire ATB battle, remove WASD, render units at rank positions, speed bar rendering | Claude | DONE | `src/states/combat_state.py` | 1.1–1.6 |
| 1.8 | Update abilities.json with `range` field + 5 new abilities from potentialabilitiesplan.md | Claude | DONE | `data/abilities.json` | 1.3 |
| 1.9 | Update characters.json with `default_rank` + 2nd abilities per character | Claude | DONE | `data/characters.json` | 1.1 |
| 1.10 | Death rank-slide logic (when front dies, back units shift forward) | Claude | DONE | `src/combat/realtime_battle.py` | 1.4 |
| 1.11 | Add `default_rank` field to CharacterData entity | Claude | DONE | `src/entities/character.py` | 1.9 |
| 1.12 | Rewrite AIController (remove positioning, keep rank-aware ability usage) | Claude | DONE | `src/combat/ai_controller.py` | 1.4 |
| 1.13 | Push/pull/self_move/atb_delay effect resolution in battle engine | Claude | DONE | `src/combat/realtime_battle.py` | 1.4, 1.10 |
| 1.14 | Support ability resolution (block grant, ally targeting) | Claude | DONE | `src/combat/realtime_battle.py` | 1.4 |

**Sprint 1 Milestone**: Speed bars fill, units auto-attack at their rank, projectiles fly to targets, damage applies, rank-slide on death, win/lose transitions work. New abilities: Grasping Shadows (pull), Cleaving Flame (front_two), Mana Shield (block), Frightful Roar (ATB delay), Piercing Arrow (front_two + armor pierce).

---

## Sprint 2: Visual & Polish (Parallel)

| # | Task | Owner | Status | Files | Depends On |
|---|------|-------|--------|-------|------------|
| 2.1 | Speed bar UI widget (per-unit, class-colored, fill animation) | Gemini | DONE | `src/ui/speed_bar.py` (new) | 1.7 DONE |
| 2.2 | Rank-based unit rendering (proper sprites at rank positions, stagger) | Gemini | DONE | `src/states/combat_state.py` (draw) | 1.7 DONE |
| 2.3 | Ability HUD update (adapt for rank targeting context, 2 abilities per char) | Gemini | DONE | `src/ui/ability_hud.py` | 1.7 DONE |
| 2.4 | Projectile flight animation (smooth travel between ranks) | Gemini | DONE | `src/states/combat_state.py` (draw) | 1.6 DONE |
| 2.5 | HP bars above units at rank positions | Gemini | DONE | `src/states/combat_state.py` (draw) | 2.2 |

**Sprint 2 Milestone**: Full ATB combat with polished speed bar UI, rank rendering, and proper visuals.

---

## Sprint 3: Polish & Balance (Both)

| # | Task | Owner | Status | Files | Depends On |
|---|------|-------|--------|-------|------------|
| 3.1 | Balance speed scaling, damage, cooldowns, rank advantages | Both | DONE | `config.py`, `data/` | Sprint 2 |
| 3.2 | Combat background (Darkest Dungeon corridor style) | Gemini | DONE | `combat_state.py` | Sprint 2 |
| 3.3 | "Ready!" flash / turn indicator when speed bar fills | Gemini | DONE | `combat_state.py`, UI | 2.1 |
| 3.4 | Rank push/pull slide animation | Gemini | DONE | `src/animation/combat_animator.py` | 1.13 |
| 3.5 | Death animation + rank collapse visual (units slide forward) | Both | DONE | `combat_state.py`, `particles.py` | 1.10 |
| 3.6 | Boss fight support (large sprites, multi-rank, special patterns) | Claude | DONE | `realtime_battle.py`, `combat_state.py`, `data/abilities.json`, `data/enemies.json` | Sprint 2 |
| 3.7 | Relic/mod integration with ATB system | Claude | DONE | `run_manager.py`, `data/rewards.json` | Sprint 2 |
| 3.8 | Run-manager HP sync after ATB combat | Claude | DONE | `combat_state.py` | Sprint 1 |

---

## Backlog (Future)

| # | Task | Notes |
|---|------|-------|
| B.1 | Position swap ability (player can rearrange their team mid-combat) | Strategic depth |
| B.2 | Taunt mechanic (force enemies to target specific rank) | Tank role |
| B.3 | Multi-rank bosses (occupy positions 1-2, wider sprite) | Boss variety |
| B.4 | Speed buff/debuff abilities (haste/slow fill rate) | ATB manipulation |
| B.5 | Sound effects (attack, hit, ability, death, speed bar ding) | Audio |
| B.6 | Multiplayer (second player controls a different party member) | Coop |
| B.7 | Remaining abilities from potentialabilitiesplan.md (Void Step, Holy Provocation, Ignite, Bloodlust Charge, Caltrops, enemy abilities) | More depth |

---

## Shared File Rules

| File | Primary Owner | Secondary | Rule |
|------|--------------|-----------|------|
| `combat_state.py` | Claude (Sprint 1) | Gemini (Sprint 2+) | Claude finishes structural rewrite before Gemini touches draw methods |
| `config.py` | Claude | Gemini | Claude uses `# ATB combat` section; Gemini uses `# Visual tuning` section |
| `abilities.json` | Claude | Gemini | Claude owns schema (field names); Gemini tunes visual values (sprites, tints) |
| `particles.py` | Gemini | Claude | Gemini owns new presets; Claude may call spawn functions |
| `ability_animator.py` | Gemini | — | Gemini only |
| `ability_hud.py` | Gemini | — | Gemini only |
| `speed_bar.py` | Gemini | — | Gemini only (new file) |

---

## Status Log

_Record major milestones and blockers here:_

| Date | Agent | Note |
|------|-------|------|
| 2026-03-09 | — | ATB Lane Combat pivot planned. Previous side-scroller sprints archived. |
| 2026-03-09 | Gemini | Sprint 2 task 2.1 (speed_bar.py) completed. |
| 2026-03-09 | Claude | Sprint 1 COMPLETE (1.1–1.14). ATB engine, rank system, targeting, projectiles, all new abilities (Grasping Shadows, Cleaving Flame, Mana Shield, Frightful Roar, Piercing Arrow), push/pull/atb_delay effects, support abilities, AI controller, combat_state.py rewrite. Smoke tested — all imports pass, 5-second simulated battle runs correctly. |
| 2026-03-09 | Claude | Added Abyssal Smash (unlockable melee AoE stun for Nightfang). Wired through abilities.json, rewards.json (ability_unlock type), events.json (Abyssal Altar event), RunManager.unlock_ability(), CombatUnit.from_character(unlocked_abilities=), reward_state.py. Uses AoEStun.png asset. |
| 2026-03-09 | Claude | Sprint 3 Claude tasks DONE (3.6–3.8). Boss: added Life Drain ability for Goblin Warlock (ranged drain + self-heal), wired life_drain effect in battle engine. Relics: wired team_speed effect (Quicksilver Pendant) in RunManager.apply_relic(). HP sync was already done in Sprint 1 (combat_state lines 179-180). |
| 2026-03-09 | Claude | Balance pass (3.1): DAMAGE_ARMOR_FACTOR 0.5->1.0 (armor is now meaningful flat reduction), ATB_BASE_FILL_RATE 0.25->0.22 + ATB_SPEED_SCALING 0.06->0.08 (wider speed spread, 1.8x ratio from speed 1->4). Shadow Wraith +1 armor, Goblin Mage str 1->2. Enemy rebalance: Fat Fly HP 30->25 (trash), Goblin Brute str 3->4/HP 45->40 (glass cannon brute), Sentinel armor 2->3/HP 50->55 (true tank), Assassin str 4->5/speed 4->5/HP 55->45 (deadly glass cannon), Boss HP 120->160/armor 2->3 (longer fights), Cultist HP 15->20. Mana Shield block 12->15, Summon cd 7->9. Simulated: normal ~9s, elite ~6s, boss ~15s. |
| 2026-03-10 | Gemini | Theme Pivot: Dungeon â†’ Gothic City. Converted .jpg assets from `potential assets/New backgrounds` to .png, resized to 1280x720, and applied gothic nocturnal tint. Updated `combat_state.py` to randomly select from these new backgrounds (`gothic_stairs.png`, `gothic_entrance.png`, `gothic_street.png`). |
