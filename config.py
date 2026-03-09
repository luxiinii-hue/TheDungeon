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
DAMAGE_ARMOR_FACTOR = 0.5

# Map
MAP_ROWS = 5
MAP_COLS_MIDDLE = 3
MAP_NODE_RADIUS = 22
MAP_NODE_SPACING_X = 200
MAP_NODE_SPACING_Y = 120

# Real-time combat
PLAYER_ZONE_X_MIN = 40
PLAYER_ZONE_X_MAX = 400
PLAYER_ZONE_Y_MIN = 100
PLAYER_ZONE_Y_MAX = 580
ENEMY_ZONE_X_MIN = 880
ENEMY_ZONE_X_MAX = 1240
ENEMY_ZONE_Y_MIN = 100
ENEMY_ZONE_Y_MAX = 580
PLAYER_MOVE_SPEED = 250  # Increased for snappier dodging
PROJECTILE_BASE_SPEED = 700  # Faster auto-attacks
PROJECTILE_ABILITY_SPEED = 600
ATTACK_COOLDOWN_BASE = 2.0  # Slightly faster base attacks
ATTACK_COOLDOWN_SPEED_FACTOR = 0.3
ATTACK_COOLDOWN_MIN = 0.4
UNIT_HITBOX_W = 60
UNIT_HITBOX_H = 120

# Visual tuning (Gemini section)

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
