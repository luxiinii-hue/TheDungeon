# Summon Refactoring — Design

## Problem

The `summon_cultist` ability has a logic-visual split: `RealtimeBattle` only emits a `BattleAction` event, while `CombatScreenState` creates the actual `CombatUnit` and appends it to the engine's lists. This is fragile and can desync if the engine continues updating before the UI processes the action. There's also no MAX_RANKS check, risking overflow.

## Design

### Battle Engine (`realtime_battle.py`)

- Add `self._pending_units: list[CombatUnit]` — units spawned during a tick, merged at end of `update()`
- Store enemy templates at init (passed from combat_state or loaded once)
- On summon effect: check `MAX_RANKS = 4` against alive enemies. If full, skip. Otherwise create `CombatUnit.from_enemy()`, assign next rank + position, append to `_pending_units`, emit `BattleAction(type="summon", target=new_unit.name)`
- End of `update()`: move pending units into `enemy_units`, clear list

### Combat State (`combat_state.py`)

- `_handle_summon()` becomes visual-only: find unit by name in `self.battle.enemy_units`, create `IdleAnimator`, spawn particles
- Remove all unit creation, rank assignment, and `battle.enemy_units.append()` from combat state

### Data Flow

```
Engine tick → summon effect → MAX_RANKS check → create CombatUnit → _pending_units
           → end of tick → merge into enemy_units → emit BattleAction
UI receives BattleAction → find unit by name → create animator + particles
```

### Unchanged

- `abilities.json` schema, `BattleAction` dataclass, `EnemyData`, `CombatUnit.from_enemy()`
