# The Gothic City of Pepruvia

## Project Overview

**The Gothic City of Pepruvia** is a 2D RPG built with Python and the `pygame-ce` library. The game features a structured, object-oriented architecture centered around a core state machine and a tactical Single-Lane ATB (Active Time Battle) combat system.

**Key Architecture Components:**
*   **Tactical ATB Engine:** Units occupy ranks 1-4. Mechanics include melee/ranged targeting constraints, position manipulation (push/pull/swap), and multi-rank entities (Bosses).
*   **Procedural Gothic Map:** A complex rendering pipeline that uses modular ornate ribbons and building props. Connections are pre-rendered for performance.
*   **Global Settings & Audio:** Built-in `SettingsOverlay` for volume control. Dynamic music management integrated across state transitions.
*   **Data-Driven Design:** Game balance is maintained through JSON files in `data/` defining characters, enemies, and abilities.

**Recent Implementation Highlights:**
*   **Advanced Status Effects:** Full support for Taunt, Poison (ATB slow + DoT), Haste/Slow, and Phase.
*   **Dynamic AI Overhaul:** Conditional ability usage (e.g., Minions sacrificing only at low HP).
*   **Map Redesign:** Transitioned to a "City Streets" aesthetic with layered landmarks and ornate foundation banners.
*   **Multi-Rank Bosses:** The Goblin Warlock now occupies 2 rank slots, centered visually and immune to basic push effects.

## Building and Running

To run the game, you will need Python installed. Follow these steps:

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run the Game:**
    ```bash
    python main.py
    ```

## Development Conventions

*   **Configuration (`config.py`):** Refer to this file for colors, screen dimensions, and engine scaling factors.
*   **Shared File Rules:** 
    *   `MapState` and `CombatScreenState` rendering logic is primarily maintained by **Gemini**.
    *   Combat Engine logic and ability resolution is primarily maintained by **Claude**.
*   **Task Tracking:** Refer to `docs/plans/todo.md` for current sprint progress. Update status to `IN PROGRESS (Gemini)` when starting a task and `DONE` upon verification.
*   **Verification:** Always run `python -m py_compile` on modified files to check for syntax errors before committing.
