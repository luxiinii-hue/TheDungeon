# Dungeon of the Acoc

## Project Overview

**Dungeon of the Acoc** is a 2D game built with Python and the `pygame-ce` (Pygame Community Edition) library. The game features a structured, object-oriented architecture built around a core state machine. It is designed with separation of concerns in mind, dividing logic into specific subsystems like combat, map generation, animation, entities, and UI.

**Key Architecture Components:**
*   **State Machine (`src/states/`, `src/core/state_machine.py`):** The game flow is driven by discrete states including Title, Team Select, Map, Combat, Reward, and Result. 
*   **Data-Driven Design (`data/`):** Game entities such as characters, enemies, abilities, events, and rewards are defined via JSON files, making it easy to tune gameplay without changing code.
*   **Assets (`character assets/`):** Sprites and graphical assets are loaded by an `AssetManager` (`src/core/asset_manager.py`).
*   **Subsystems (`src/`):**
    *   `animation/`: Handles idle bobbing, particle effects, tweening, and combat animations.
    *   `combat/`: Manages abilities, targeting logic, combat units, and auto-battle functionality.
    *   `core/`: Contains the main `Game` class, `StateMachine`, and `AssetManager`.
    *   `entities/`: Defines character and enemy logic.
    *   `map/`: Handles node-based map generation and run progression (`RunManager`).
    *   `ui/`: Custom UI elements like buttons, panels, health bars, and text rendering.

## Building and Running

To run the game, you will need Python installed. Follow these steps:

1.  **Install Dependencies:**
    Install the required libraries (primarily `pygame-ce`) using pip:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run the Game:**
    Execute the main entry point:
    ```bash
    python main.py
    ```

## Development Conventions

*   **Configuration (`config.py`):** All global constants, colors, display settings (e.g., resolution, FPS), UI tuning knobs, and base asset paths are centralized in `config.py`. Always refer to this file for colors or system constants instead of hardcoding values.
*   **Typing:** The codebase incorporates Python type hints (e.g., `dict[GameState, object]`) for better readability and tooling support.
*   **State-Based Logic:** Any new game screens or primary phases should be implemented as a new state inheriting from a base state and registered in the `Game` class.
*   **UI Components:** When building new interfaces, utilize the existing components in `src/ui/` (like `button.py` and `panel.py`) to maintain a consistent aesthetic.
*   **Task Tracking (`todo.md`):** The `docs/plans/todo.md` file is the single source of truth for task status and coordination with Claude. Before starting any task, check this file to ensure it is not `IN PROGRESS` by someone else. Update the status of your assigned tasks from `TODO` to `IN PROGRESS (Gemini)` when you begin, and to `DONE` when you finish. Always adhere to the shared file rules (e.g., specific sections to edit in `config.py` and `abilities.json`) and log major milestones or blockers in the "Status Log" at the bottom of the file.
