# Potential Abilities Plan (ATB Lane Combat)

This document outlines the proposed ability design for existing characters and enemies to fully utilize the new Single-Lane ATB mechanics (Rank positioning, Push/Pull, Melee vs. Ranged targeting).

## Core Concepts for ATB Abilities
- **Range:** 
  - `melee`: Can only target the frontmost enemy rank. Usable mostly from ranks 1 and 2.
  - `ranged`: Can target any enemy rank. Usable from any rank.
- **Positioning Effects:**
  - `push X`: Knocks the target back X ranks.
  - `pull X`: Drags the target forward X ranks.
  - `self_move X`: Moves the caster forward or backward.
- **Status Effects:** Stun, Bleed, Poison, Taunt (forces enemies to target this unit if in front).

---

## Player Characters

### 1. Shadow Wraith (Warlock)
*Role: Back-rank sustained damage and disruption.*
*   **Shadow Bolt (Existing):** Ranged. Single target dark damage. Add a chance to apply a slight ATB delay (slow).
*   **Grasping Shadows (New):** Ranged. Low damage. **Pull 2**. Drags a back-line enemy to the front, exposing them to melee attacks. *(Visual: `Animations/icons/magic/fb664.png` - purple dark magic orb/swirl)*
*   **Void Step (New):** Support. Swaps position with the ally in front of them and grants temporary dodge/phase to both. *(Visual: `Animations/icons/status/fb393.png` - purple magical buff/rune)*

### 2. Flame Knight (Paladin)
*Role: Front-rank tank and protector.*
*   **Shield Bash (Existing):** Melee. Moderate damage, applies Stun for 1 turn. **Push 1**. 
*   **Holy Provocation (New):** Support/Melee. Deals low damage, applies Taunt to self, and grants Armor. *(Visual: `Animations/icons/status/fb391.png` - glowing yellow/gold shield/aura)*
*   **Cleaving Flame (New):** Melee (AoE). Deals damage to Rank 1 and Rank 2 enemies simultaneously. *(Visual: `Animations/icons/magic/fb577.png` - fire burst)*

### 3. Goblin Mage (Sorcerer)
*Role: Any-rank AoE damage.*
*   **Arcane Blast (Existing):** Ranged (AoE). Strikes all enemy ranks. High ATB cost.
*   **Ignite (New):** Ranged. Deals moderate fire damage to a single target and applies a Burn dot (damage every time their ATB fills). *(Visual: `Animations/icons/magic/fb586.png` - flame or meteor)*
*   **Mana Shield (New):** Support. Can be cast on any ally to give them temporary HP/Block. *(Visual: `Animations/icons/status/fb401.png` - blue glowing shield/bubble)*

### 4. Nightfang (Barbarian)
*Role: Front-rank heavy burst damage.*
*   **Savage Rend (Existing):** Melee. High damage, applies Bleed. Deals bonus damage if Nightfang is below 50% HP.
*   **Bloodlust Charge (New):** Melee. **Self Move Forward 1**. High damage strike. If used from Rank 2, Nightfang dashes to Rank 1 and attacks. *(Visual: `Animations/icons/physical/fb545.png` - red sweeping slash)*
*   **Abyssal Smash (New/Unlockable):** Melee (AoE). Sweeping stun attack that hits the front two enemy ranks and applies Daze/Stun. 
    *   *Visual Strategy:* Uses the massive high-res `AoEStun.png` asset. We will use a **Tweening sequence** to animate it: spawn the asset aligned with Nightfang, scale it up slightly and rotate it forward (the "windup"), freeze the screen with a brief dark purple tint overlay + heavy camera shake on impact, spawn stun status icons (`fb385` etc.) over the enemies, and fade out.
*   **Frightful Roar (New):** Ranged (AoE). Zero damage, but applies ATB delay (pushes back enemy turn meters) to all enemies. *(Visual: `Animations/icons/status/fb683.png` - red debuff/shout icon)*

### 5. Briarfoot (Ranger)
*Role: Back-rank sniper and utility.*
*   **Twin Shot (Existing):** Ranged. Fires two arrows. High critical hit chance against back-rank enemies.
*   **Piercing Arrow (New):** Ranged. Shoots through Rank 1, hitting Rank 1 and Rank 2 enemies. Ignores 50% of armor. *(Visual: `Animations/icons/physical/fb557.png` - piercing projectile effect)*
*   **Caltrops (New):** Ranged (Trap). Applies a debuff to a specific enemy rank. If an enemy is Pushed or Pulled into that rank, they take damage and lose ATB. *(Visual: `Animations/icons/physical/fb701.png` - spiked ground/trap)*

---

## Enemies

### Normal Enemies
*   **Fat Fly:** 
    *   *Buzzing Strike:* Melee. Basic attack.
    *   *Evasive Maneuver:* Passive. High dodge chance if in Rank 1.
*   **Goblin Brute:**
    *   *Club Smash:* Melee. High damage, **Push 1**. Can mess up player formations.
*   **Goblin Sentinel:**
    *   *Defensive Stance:* Support. Gives Armor to itself and the enemy behind it. Applies Taunt.

### Elite Enemies
*   **Goblin Assassin:**
    *   *Backstab:* Ranged/Melee. Jumps to Rank 1, deals massive damage to the player's back-most rank, then retreats.
    *   *Poison Dart:* Ranged. Applies Poison (DoT).
*   **Bloated Fly:**
    *   *Noxious Spit:* Ranged. Hits Rank 1 and 2, applying Poison.
    *   *Death Burst:* Passive. On death, explodes dealing damage to the front two player ranks and the enemy rank immediately behind it.

### Boss & Minions
*   **Goblin Warlock (Boss):**
    *   *Summon Cultist (Existing):* Spawns a Cultist Minion in Rank 1 (pushing other enemies back).
    *   *Life Drain:* Ranged. Deals damage and heals the Warlock for the same amount.
    *   *Eldritch Command:* Support. Forces a Cultist Minion to instantly take its turn and attack.
*   **Cultist Minion:**
    *   *Zealous Strike:* Melee. Weak attack.
    *   **Dark Sacrifice:** Support. If below 50% HP, destroys itself to heal the Warlock and grant the Warlock a damage buff.

    ---

    ## Code Implementation Guidelines

    To implement these abilities smoothly within the new ATB engine, we need specific updates to our data schemas and combat logic:

    ### 1. `abilities.json` Schema Updates
    We need to expand the `AbilityDef` dictionary structure parsed in `src/combat/ability.py`:
    *   **`range` field**: Add a string field `"range": "melee" | "ranged" | "support"`.
    *   **`effects` list expansions**: 
        *   `{"type": "push", "value": X}` 
        *   `{"type": "pull", "value": X}`
        *   `{"type": "self_move", "value": X}` (where positive X is forward, negative X is backward)
        *   `{"type": "atb_delay", "value": X}` (where X is a flat reduction in the target's current speed bar)

    ### 2. Targeting Logic (`src/combat/targeting.py`)
    *   **Melee Constraint:** If an ability's `range` is `"melee"`, the `get_valid_targets()` function must *only* return the unit occupying Rank 1 (or the lowest populated rank if Rank 1 is empty).
    *   **Ranged Advantage:** If an ability is `"ranged"`, it can return a list of units in any populated rank.
    *   **Piercing/Cleave Logic:** Introduce a new targeting enum like `"front_two"` which returns Rank 1 and Rank 2 for abilities like *Cleaving Flame* and *Piercing Arrow*.

    ### 3. Combat Engine Resolution (`src/combat/realtime_battle.py`)
    *   **Position Swapping:** When handling a `"push"`, `"pull"`, or `"self_move"` effect during `resolve_ability()`, the engine must safely swap the unit with the entity currently occupying the destination rank. 
    *   **Rank Array:** The combat state should manage units in a fixed array/dictionary of Ranks (e.g., `self.player_ranks = {1: UnitA, 2: UnitB, 3: None, 4: UnitC}`) rather than a loose list, to make pushing/pulling math explicit.
    *   **Action Delays:** Add a method `unit.reduce_atb(amount)` to handle ATB delays safely without dropping below 0.
