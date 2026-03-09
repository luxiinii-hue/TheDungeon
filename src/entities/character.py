"""CharacterData dataclass."""

from dataclasses import dataclass, field


@dataclass
class IdleConfig:
    bob_amplitude: float = 1.0
    bob_frequency: float = 0.7
    breathe_min: float = 0.996
    breathe_max: float = 1.004
    glow_color: tuple = (200, 150, 255)
    glow_enabled: bool = False
    glow_radius_factor: float = 0.25
    glow_alpha_min: int = 8
    glow_alpha_max: int = 25

    @classmethod
    def from_dict(cls, data: dict) -> "IdleConfig":
        d = dict(data)
        if "glow_color" in d:
            d["glow_color"] = tuple(d["glow_color"])
        return cls(**d)


@dataclass
class CharacterData:
    id: str
    name: str
    sprite: str
    max_hp: int
    strength: int
    armor: int
    speed: int
    abilities: list[str]
    role: str
    unlocked: bool
    description: str
    idle_config: IdleConfig = field(default_factory=IdleConfig)
    default_rank: int = 2

    @classmethod
    def from_dict(cls, data: dict) -> "CharacterData":
        d = dict(data)
        idle_cfg = IdleConfig.from_dict(d.pop("idle_config", {}))
        default_rank = d.pop("default_rank", 2)
        return cls(**d, idle_config=idle_cfg, default_rank=default_rank)
