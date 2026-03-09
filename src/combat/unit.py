"""Runtime combat unit wrapper — mutable state around static definitions."""

from dataclasses import dataclass, field
from config import ATB_BASE_FILL_RATE, ATB_SPEED_SCALING


@dataclass
class Buff:
    type: str  # "burn", "stun", "mana_surge"
    duration: int
    value: float = 0


class CombatUnit:
    def __init__(self, unit_id: str, name: str, team: str,
                 max_hp: int, strength: int, armor: int, speed: int,
                 ability_ids: list[str], passive: str | None = None,
                 ability_mods: list[str] | None = None,
                 default_rank: int = 1):
        self.id = unit_id
        self.name = name
        self.team = team  # "player" or "enemy"
        self.max_hp = max_hp
        self.hp = max_hp
        self.strength = strength
        self.armor = armor
        self.speed = speed
        self.block = 0
        self.ability_ids = list(ability_ids)
        self.passive = passive
        self.ability_mods = ability_mods or []

        # Rank position in the lane (1 = front, 4 = back)
        self.rank: int = default_rank

        # ATB speed bar (0.0 → 1.0, fires auto-attack when full)
        self.speed_bar: float = 0.0
        self.speed_bar_fill_rate: float = ATB_BASE_FILL_RATE + speed * ATB_SPEED_SCALING

        # Rendered position (computed from rank by combat state, not free-move)
        self.x: float = 0.0
        self.y: float = 0.0

        # Cooldown tracking: ability_id -> seconds remaining
        self.cooldowns: dict[str, float] = {}
        self.buffs: list[Buff] = []
        self.alive = True

        # Track stats for mana surge passive
        self.time_alive = 0.0

    @property
    def is_stunned(self) -> bool:
        return any(b.type == "stun" and b.duration > 0 for b in self.buffs)

    def tick_speed_bar(self, dt: float) -> bool:
        """Fill the speed bar. Returns True if bar just filled (trigger auto-attack)."""
        if self.is_stunned:
            return False
        self.speed_bar += self.speed_bar_fill_rate * dt
        if self.speed_bar >= 1.0:
            self.speed_bar = 0.0
            return True
        return False

    def tick_cooldowns_rt(self, dt: float):
        """Tick cooldowns by real-time delta (seconds)."""
        for ability_id in list(self.cooldowns):
            self.cooldowns[ability_id] = max(0.0, self.cooldowns[ability_id] - dt)

    def tick_buffs_rt(self, dt: float) -> int:
        """Tick buffs in real-time. Returns burn damage if a tick fires."""
        damage = 0
        for buff in self.buffs:
            if buff.type == "burn" and buff.duration > 0:
                if not hasattr(buff, '_tick_timer'):
                    buff._tick_timer = 0.0
                buff._tick_timer += dt
                if buff._tick_timer >= 1.0:
                    buff._tick_timer -= 1.0
                    damage += int(buff.value)
                    buff.duration -= 1
            elif buff.type == "stun":
                if not hasattr(buff, '_tick_timer'):
                    buff._tick_timer = 0.0
                buff._tick_timer += dt
                if buff._tick_timer >= 1.0:
                    buff._tick_timer -= 1.0
                    buff.duration -= 1
        self.buffs = [b for b in self.buffs if b.duration > 0]
        return damage

    def can_use_ability(self, ability_id: str) -> bool:
        return self.cooldowns.get(ability_id, 0) <= 0

    def put_on_cooldown(self, ability_id: str, cooldown: float):
        self.cooldowns[ability_id] = float(cooldown)

    def reduce_atb(self, amount: float):
        """Reduce the speed bar by a flat amount (ATB delay). Clamps to 0."""
        self.speed_bar = max(0.0, self.speed_bar - amount)

    def add_buff(self, buff_type: str, duration: int, value: float = 0):
        self.buffs.append(Buff(type=buff_type, duration=duration, value=value))

    def take_damage(self, amount: int) -> int:
        """Apply damage after block. Returns actual HP lost."""
        remaining = amount
        if self.block > 0:
            blocked = min(self.block, remaining)
            self.block -= blocked
            remaining -= blocked
        if remaining > 0:
            self.hp = max(0, self.hp - remaining)
        if self.hp <= 0:
            self.alive = False
        return remaining

    @classmethod
    def from_character(cls, char_data, ability_mods: list[str] | None = None,
                       stat_boosts: dict | None = None,
                       unlocked_abilities: list[str] | None = None) -> "CombatUnit":
        max_hp = char_data.max_hp
        strength = char_data.strength
        armor = char_data.armor
        speed = char_data.speed

        if stat_boosts:
            max_hp += stat_boosts.get("max_hp", 0)
            strength += stat_boosts.get("strength", 0)
            armor += stat_boosts.get("armor", 0)
            speed += stat_boosts.get("speed", 0)

        # Determine passive based on role
        passive = None
        if char_data.id == "acoc1":
            passive = "phase"  # 25% dodge
        elif char_data.id == "acoc2":
            passive = "flame_aura"  # reflect 20% damage
        elif char_data.id == "acoc3":
            passive = "mana_surge"  # +10% ability damage per 5s
        elif char_data.id == "acoc4":
            passive = "rage"  # +25% damage when below 50% HP

        default_rank = getattr(char_data, 'default_rank', 2)

        ability_ids = list(char_data.abilities)
        if unlocked_abilities:
            for ab_id in unlocked_abilities:
                if ab_id not in ability_ids:
                    ability_ids.append(ab_id)

        return cls(
            unit_id=char_data.id,
            name=char_data.name,
            team="player",
            max_hp=max_hp,
            strength=strength,
            armor=armor,
            speed=speed,
            ability_ids=ability_ids,
            passive=passive,
            ability_mods=ability_mods,
            default_rank=default_rank,
        )

    @classmethod
    def from_enemy(cls, enemy_data) -> "CombatUnit":
        return cls(
            unit_id=enemy_data.id,
            name=enemy_data.name,
            team="enemy",
            max_hp=enemy_data.max_hp,
            strength=enemy_data.strength,
            armor=enemy_data.armor,
            speed=enemy_data.speed,
            ability_ids=list(enemy_data.abilities),
            default_rank=1,  # enemies get sequential ranks assigned externally
        )
