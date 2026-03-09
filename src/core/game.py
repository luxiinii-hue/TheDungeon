"""Master game loop, clock, and state machine owner."""

import asyncio
import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE
from src.core.state_machine import StateMachine, GameState
from src.core.asset_manager import AssetManager
from src.states.title_state import TitleState
from src.states.team_select_state import TeamSelectState
from src.states.map_state import MapState
from src.states.combat_state import CombatScreenState
from src.states.reward_state import RewardState
from src.states.result_state import ResultState


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.running = True

        self.asset_manager = AssetManager()
        self.state_machine = StateMachine()

        # RunManager lives here — survives across state transitions
        self.run_manager = None

        self._register_states()
        self.state_machine.transition(GameState.TITLE)

    def _register_states(self):
        self.state_machine.register(GameState.TITLE, TitleState(self))
        self.state_machine.register(GameState.TEAM_SELECT, TeamSelectState(self))
        self.state_machine.register(GameState.MAP, MapState(self))
        self.state_machine.register(GameState.COMBAT, CombatScreenState(self))
        self.state_machine.register(GameState.REWARD, RewardState(self))
        self.state_machine.register(GameState.RESULT, ResultState(self))

    async def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                else:
                    self.state_machine.current.handle_event(event)
            self.state_machine.current.update(dt)
            self.state_machine.current.draw(self.screen)
            pygame.display.flip()
            await asyncio.sleep(0)

        pygame.quit()
