"""All constants, colors, paths, and tuning knobs."""

import os

# Display
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
TITLE = "Dungeon of the Acoc"

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.join(BASE_DIR, "character assets")
DATA_DIR = os.path.join(BASE_DIR, "data")
UI_DIR = os.path.join(ASSET_DIR, "UI")
ICON_DIR = os.path.join(UI_DIR, "icons")
FONT_TITLE_PATH = os.path.join(UI_DIR, "fonts", "alagard.ttf")
FONT_BODY_PATH = os.path.join(UI_DIR, "fonts", "Kenney Pixel.ttf")

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
DARK_GRAY = (64, 64, 64)
LIGHT_GRAY = (192, 192, 192)
RED = (200, 50, 50)
GREEN = (50, 200, 50)
BLUE = (50, 100, 200)
GOLD = (218, 165, 32)
DARK_RED = (139, 0, 0)
DARK_GREEN = (0, 100, 0)
DARK_BLUE = (0, 0, 139)
PANEL_BG = (30, 30, 40)
PANEL_BORDER = (80, 80, 100)
ORANGE = (220, 140, 40)
PURPLE = (160, 80, 200)
CYAN = (80, 200, 220)

# UI
BUTTON_WIDTH = 200
BUTTON_HEIGHT = 50
FONT_SIZE_SMALL = 16
FONT_SIZE_MEDIUM = 24
FONT_SIZE_LARGE = 36
FONT_SIZE_TITLE = 64

# Animation
IDLE_BOB_AMPLITUDE = 3.0
IDLE_BOB_FREQUENCY = 1.2
IDLE_BREATHE_MIN = 0.98
IDLE_BREATHE_MAX = 1.02
IDLE_BREATHE_FREQUENCY = 0.8
IDLE_GLOW_ALPHA_MIN = 30
IDLE_GLOW_ALPHA_MAX = 80
IDLE_GLOW_FREQUENCY = 1.5
IDLE_SCALE_STEPS = 16
SHADOW_ALPHA = 60

# Auto-Battle
AUTO_BATTLE_ACTION_DELAY = 1.0
AUTO_BATTLE_FAST_DELAY = 0.4
DAMAGE_ARMOR_FACTOR = 1.0  # armor is flat damage reduction per hit

# Map
MAP_ROWS = 5
MAP_COLS_MIDDLE = 3
MAP_NODE_RADIUS = 22
MAP_NODE_SPACING_X = 200
MAP_NODE_SPACING_Y = 120

# ATB Lane Combat
# Rank x-positions: index 0 unused, ranks 1(front)–4(back)
PLAYER_RANK_X = [0, 370, 280, 190, 100]
ENEMY_RANK_X = [0, 910, 1000, 1090, 1180]
COMBAT_Y_CENTER = 330
RANK_Y_STAGGER = 10  # slight y offset per rank for depth

# ATB speed bar fill
ATB_BASE_FILL_RATE = 0.22   # bar fill/sec at speed 0
ATB_SPEED_SCALING = 0.08    # additional fill/sec per speed point

# Projectiles (targeted flight — no collision grid)
PROJECTILE_TRAVEL_SPEED = 600
PROJECTILE_ABILITY_SPEED = 500

# Visual tuning (Gemini section)
SPEED_BAR_WIDTH = 80
SPEED_BAR_HEIGHT = 8
SPEED_BAR_BG_COLOR = (40, 40, 45)
SPEED_BAR_BORDER_COLOR = (20, 20, 25)
SPEED_BAR_FILL_COLOR_READY = (255, 215, 0) # Gold when full

# Class colors (for UI badges)
CLASS_COLORS = {
    "warlock": (160, 80, 200),
    "paladin": (80, 140, 220),
    "sorcerer": (200, 100, 180),
    "barbarian": (200, 60, 60),
    "ranger": (80, 180, 80),
}

CLASS_ATTACK_SPRITES = {
    "acoc1": "UI/weapon_icons/Icon28_19.png",   # Shadow Wraith (purple projectile/dagger)
    "acoc2": "UI/weapon_icons/Icon28_09.png",   # Flame Knight (sword)
    "acoc3": "UI/weapon_icons/Icon28_15.png",   # Goblin Mage (wand/orb)
    "acoc4": "UI/weapon_icons/Icon28_28.png",   # Nightfang (axe/claw)
    "acoc5": "UI/weapon_icons/Icon28_13.png",   # Briarfoot (arrow)
}
