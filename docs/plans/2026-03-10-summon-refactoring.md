# Summon Refactoring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Move summon unit creation from the UI layer (`combat_state.py`) into the battle engine (`realtime_battle.py`) so the engine owns all unit state, with a MAX_RANKS=4 guard and deferred unit merging.

**Architecture:** The battle engine receives pre-loaded enemy templates at init. On summon, it creates the `CombatUnit` internally, queues it in a pending list, and merges at end of `update()`. The combat state only creates animators and particles for new units.

**Tech Stack:** Python 3.13, pygame-ce

---

### Task 1: Add Enemy Templates and Pending Units to RealtimeBattle

**Files:**
- Modify: `src/combat/realtime_battle.py:50-68` (constructor)
- Modify: `src/combat/realtime_battle.py:9-13` (imports)

**Step 1: Add MAX_RANKS constant and import EnemyData**

At `src/combat/realtime_battle.py:1-13`, add the import and constant:

```python
from src.entities.enemy import EnemyData
```

After the `CLASS_ATTACK_COLORS` dict (after line 37), add:

```python
MAX_RANKS = 4
```

**Step 2: Add enemy_templates and _pending_units to __init__**

Modify `__init__` to accept and store enemy templates, and add the pending list:

```python
class RealtimeBattle:
    def __init__(self, player_units: list[CombatUnit],
                 enemy_units: list[CombatUnit],
                 ability_registry: AbilityRegistry,
                 player_controlled_id: str = "",
                 asset_manager=None,
                 enemy_templates: dict[str, EnemyData] | None = None):
        self.player_units = player_units
        self.enemy_units = enemy_units
        self.ability_registry = ability_registry
        self.player_controlled_id = player_controlled_id
        self.asset_manager = asset_manager
        self.enemy_templates = enemy_templates or {}
        self.projectiles: list[Projectile] = []
        self.result: str | None = None
        self._actions: list[BattleAction] = []
        self._pending_units: list[CombatUnit] = []
```

Keep the rest of `__init__` (rank assignment, sync) unchanged.

**Step 3: Commit**

```bash
git add src/combat/realtime_battle.py
git commit -m "refactor: add enemy_templates and _pending_units to RealtimeBattle"
```

---

### Task 2: Implement Engine-Side Summoning

**Files:**
- Modify: `src/combat/realtime_battle.py:290-306` (`_execute_self_ability`)

**Step 1: Replace the summon event emission with actual unit creation**

Replace the summon branch in `_execute_self_ability` (lines 293-299):

```python
    def _execute_self_ability(self, unit: CombatUnit, ability: AbilityDef):
        """Handle self-targeting abilities (summon, buffs, self_move)."""
        for effect in ability.effects:
            if effect.type == "summon":
                self._do_summon(unit, effect.enemy_id, effect.value)
            elif effect.type == "self_move":
                self._apply_position_effect(unit, unit, effect.type, effect.value)
        self._actions.append(BattleAction(
            type="ability", source=unit.name, target=unit.name,
            ability_name=ability.name,
            message=f"{unit.name} uses {ability.name}!",
        ))
```

**Step 2: Add `_do_summon` helper method**

Add after `_execute_self_ability`:

```python
    def _do_summon(self, summoner: CombatUnit, enemy_id: str, count: int):
        """Create summoned units in the engine. Deferred to end of tick."""
        template = self.enemy_templates.get(enemy_id)
        if not template:
            return
        alive_enemies = [u for u in self.enemy_units if u.alive]
        alive_count = len(alive_enemies) + len(self._pending_units)
        for _ in range(max(1, count)):
            if alive_count >= MAX_RANKS:
                break
            # Create a fresh EnemyData copy from template
            edata = EnemyData(
                id=template.id,
                name=f"{template.name} {len(self.enemy_units) + len(self._pending_units) + 1}",
                sprite=template.sprite,
                max_hp=template.max_hp,
                strength=template.strength,
                armor=template.armor,
                speed=template.speed,
                abilities=list(template.abilities),
                tier=template.tier,
                gold_reward=template.gold_reward,
                color=template.color,
                idle_config=template.idle_config,
            )
            new_unit = CombatUnit.from_enemy(edata)
            new_unit.rank = alive_count + 1
            new_unit.x, new_unit.y = rank_to_pos(new_unit.rank, "enemy")
            new_unit._summon_edata = edata  # stash for UI to read sprite info
            self._pending_units.append(new_unit)
            alive_count += 1
            self._actions.append(BattleAction(
                type="summon", source=summoner.name,
                target=new_unit.name,
                message=f"{summoner.name} summons {new_unit.name}!",
            ))
```

**Step 3: Commit**

```bash
git add src/combat/realtime_battle.py
git commit -m "feat: engine-side summon creation with MAX_RANKS guard"
```

---

### Task 3: Merge Pending Units at End of Update

**Files:**
- Modify: `src/combat/realtime_battle.py:104-153` (`update` method)

**Step 1: Add pending unit merge before win/lose check**

Insert before the `self._check_result()` call (line 151):

```python
        # Merge pending summoned units
        if self._pending_units:
            self.enemy_units.extend(self._pending_units)
            self._pending_units.clear()
```

The full end of `update()` becomes:

```python
        # Remove dead projectiles
        self.projectiles = [p for p in self.projectiles if p.alive]

        # Merge pending summoned units
        if self._pending_units:
            self.enemy_units.extend(self._pending_units)
            self._pending_units.clear()

        # Check win/lose
        self._check_result()

        return self._actions
```

**Step 2: Commit**

```bash
git add src/combat/realtime_battle.py
git commit -m "refactor: merge pending summons at end of battle tick"
```

---

### Task 4: Pass Enemy Templates from Combat State

**Files:**
- Modify: `src/states/combat_state.py:84-133` (`enter` method, battle init)

**Step 1: Build enemy_templates dict from loaded enemy data**

After loading `enemies_data` (line 85-86), build the template dict:

```python
        # Load and create enemy units
        enemies_data = am.load_json("enemies.json")
        all_enemies = [EnemyData.from_dict(e) for e in enemies_data]

        # Build template lookup for engine-side summoning
        enemy_templates = {e.id: e for e in all_enemies}
```

**Step 2: Pass enemy_templates to RealtimeBattle**

Modify the battle construction (line 129-133):

```python
        self.battle = RealtimeBattle(
            self.player_units, self.enemy_units,
            self.ability_registry, player_id,
            asset_manager=am,
            enemy_templates=enemy_templates,
        )
```

**Step 3: Commit**

```bash
git add src/states/combat_state.py
git commit -m "refactor: pass enemy templates to battle engine for summoning"
```

---

### Task 5: Make _handle_summon Visual-Only

**Files:**
- Modify: `src/states/combat_state.py:289-321` (`_handle_summon`)

**Step 1: Rewrite _handle_summon to only create animators**

Replace the entire `_handle_summon` method:

```python
    def _handle_summon(self, action: BattleAction):
        """Create visual representation for a unit summoned by the engine."""
        unit_name = action.target
        # Find the new unit in the engine's enemy list
        new_unit = None
        for u in self.battle.enemy_units:
            if u.name == unit_name:
                new_unit = u
                break
        if not new_unit:
            return

        # Track in our local lists if not already present
        if new_unit not in self.enemy_units:
            self.enemy_units.append(new_unit)

        # Get sprite info from stashed enemy data
        edata = getattr(new_unit, '_summon_edata', None)
        if edata and edata not in self.enemy_data:
            self.enemy_data.append(edata)

        # Create animator if we don't have one yet
        if unit_name not in self.enemy_animators:
            if edata and edata.sprite:
                am = self.game.asset_manager
                img = am.load_image(edata.sprite)
                sprite_h = 100
                aspect = img.get_width() / img.get_height()
                sprite_w = int(sprite_h * aspect)
                scaled = am.get_scaled(edata.sprite, sprite_w, sprite_h)
                self.enemy_animators[unit_name] = IdleAnimator(
                    scaled, edata.idle_config)
            else:
                self.enemy_animators[unit_name] = None

        # Spawn entry particles at the new unit's position
        from src.animation.particles import spawn_death_burst
        spawn_death_burst(self.particle_emitter, new_unit.x, new_unit.y)

        # Track position for slide animation
        self.previous_positions[unit_name] = (new_unit.x, new_unit.y)
```

**Step 2: Commit**

```bash
git add src/states/combat_state.py
git commit -m "refactor: combat state summon handler is now visual-only

Unit creation, rank assignment, and MAX_RANKS checking are now
handled by the battle engine. The UI only creates animators and
particles for summoned units."
```

---

### Task 6: Verify and Clean Up

**Step 1: Verify imports work**

Run: `cd TheDungeon && python -c "from src.combat.realtime_battle import RealtimeBattle; from src.states.combat_state import CombatScreenState; print('OK')"`
Expected: `OK`

**Step 2: Search for any remaining UI-driven summon logic**

Run: `grep -rn "battle.enemy_units.append" src/states/combat_state.py`
Expected: No results (the old `self.battle.enemy_units.append(new_unit)` line should be gone)

**Step 3: Commit design doc**

```bash
git add docs/plans/2026-03-10-summon-refactoring-design.md docs/plans/2026-03-10-summon-refactoring.md
git commit -m "docs: add summon refactoring design and implementation plan"
```

---

## File Change Summary

| File | Action | Task |
|------|--------|------|
| `src/combat/realtime_battle.py` | Modify (add import, MAX_RANKS, enemy_templates, _pending_units, _do_summon, merge in update) | 1, 2, 3 |
| `src/states/combat_state.py` | Modify (build templates dict, pass to engine, rewrite _handle_summon as visual-only) | 4, 5 |
