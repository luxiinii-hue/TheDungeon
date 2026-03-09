"""Persistent run state — survives across MAP/COMBAT/REWARD transitions."""

from src.entities.character import CharacterData
from src.map.map_node import MapNode


class RunManager:
    def __init__(self, team: list[CharacterData], map_nodes: list[MapNode]):
        self.team = team
        self.map_nodes = map_nodes

        # HP tracking per character id
        self.team_hp: dict[str, int] = {}
        self.team_max_hp: dict[str, int] = {}
        for char in team:
            self.team_hp[char.id] = char.max_hp
            self.team_max_hp[char.id] = char.max_hp

        self.gold = 0
        self.relics: list[dict] = []
        self.ability_mods: dict[str, list[str]] = {c.id: [] for c in team}
        self.stat_boosts: dict[str, dict] = {c.id: {} for c in team}
        self.unlocked_abilities: dict[str, list[str]] = {c.id: [] for c in team}

        # Map position
        self.current_node_id: int | None = None
        self.available_node_ids: list[int] = self._get_starting_nodes()

        # Run stats
        self.enemies_defeated = 0
        self.floors_cleared = 0

    def _get_starting_nodes(self) -> list[int]:
        """Get the initial available nodes (row 0)."""
        return [n.id for n in self.map_nodes if n.row == 0]

    def visit_node(self, node_id: int):
        """Mark a node as visited and update available nodes."""
        node = self.map_nodes[node_id]
        node.visited = True
        self.current_node_id = node_id
        # Available = unvisited nodes connected from the visited node
        self.available_node_ids = [
            cid for cid in node.connections
            if not self.map_nodes[cid].visited
        ]

    def heal_team(self, fraction: float):
        """Heal all team members by a fraction of max HP."""
        for char in self.team:
            max_hp = self.team_max_hp[char.id]
            heal = int(max_hp * fraction)
            self.team_hp[char.id] = min(max_hp, self.team_hp[char.id] + heal)

    def apply_stat_boost(self, char_id: str, stat: str, value: int):
        """Apply a stat boost to a character."""
        boosts = self.stat_boosts[char_id]
        boosts[stat] = boosts.get(stat, 0) + value
        # If boosting max_hp, also heal the added amount
        if stat == "max_hp":
            self.team_max_hp[char_id] += value
            self.team_hp[char_id] += value

    def apply_ability_mod(self, char_id: str, mod: str):
        """Add an ability modifier to a character."""
        if mod not in self.ability_mods[char_id]:
            self.ability_mods[char_id].append(mod)

    def unlock_ability(self, char_id: str, ability_id: str):
        """Unlock a new ability for a character during the run."""
        if char_id in self.unlocked_abilities:
            if ability_id not in self.unlocked_abilities[char_id]:
                self.unlocked_abilities[char_id].append(ability_id)

    def apply_relic(self, relic: dict):
        """Apply a team-wide relic."""
        self.relics.append(relic)
        effect = relic.get("effect", "")
        value = relic.get("value", 0)

        if effect == "team_hp_boost":
            for char in self.team:
                bonus = int(self.team_max_hp[char.id] * value)
                self.team_max_hp[char.id] += bonus
                self.team_hp[char.id] += bonus
        elif effect == "team_armor":
            for char in self.team:
                self.apply_stat_boost(char.id, "armor", int(value))
        elif effect == "team_speed":
            for char in self.team:
                self.apply_stat_boost(char.id, "speed", int(value))

    def update_hp_after_combat(self, unit_hp: dict[str, int]):
        """Update team HP from combat results. unit_hp maps char_id -> remaining HP."""
        for char_id, hp in unit_hp.items():
            if char_id in self.team_hp:
                self.team_hp[char_id] = max(0, hp)

    def is_team_alive(self) -> bool:
        return any(hp > 0 for hp in self.team_hp.values())

    def get_alive_team(self) -> list[CharacterData]:
        return [c for c in self.team if self.team_hp[c.id] > 0]
