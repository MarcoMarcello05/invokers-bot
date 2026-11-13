"""Deterministic integration simulator with invented, non-personal game data."""
from copy import deepcopy
from arena_autopilot import ArenaFrame
from arena_snapshot import ArenaObservation
from arena_actor import search_selected_candidate


def synthetic_state(power=10000):
    def opponent(name, value, identity):
        return {'name': name, 'combat_power': value, 'player_id_bytes': identity,
                'arena_points': 100, 'level': 5}
    return {'arena': {'status': 'available', 'value': {
        'opponents': [opponent('WeakTarget', 2000, 'a'*32), opponent('NextTarget', 3000, 'b'*32),
                      opponent('VisibleStrong', 9000, 'c'*32)],
        'stats': {'total_offense_battles': 0, 'total_offense_wins': 0},
        'own_combat_power': {'value': power, 'source': 'UserConfig.arena_combat_power'}}},
        'resources': {'status': 'available', 'value': {'current': {'values': {'Gem': 10, 'Arena_Token': 10}}}}}


class SimulatedArena:
    simulated = True

    def __init__(self, power=10000, outcomes=('VICTORY', 'VICTORY')):
        self.state = synthetic_state(power)
        self.phase, self.scroll_position, self.battle_reads = 'HOME', 0, 0
        self.commands, self.reads, self.outcomes = [], 0, list(outcomes)
        self.selected, self.stop = None, False
        self.auto_off = True

    def read(self):
        import time
        self.reads += 1
        return ArenaObservation(deepcopy(self.state), time.time(), str(self.reads))

    def stopped(self):
        return self.stop

    def observe(self):
        if self.phase == 'BATTLE':
            self.battle_reads += 1
            if self.battle_reads > 1:
                self.phase = self.outcomes.pop(0) if self.outcomes else 'VICTORY'
                stats = self.state['arena']['value']['stats']
                stats['total_offense_battles'] += 1
                stats['total_offense_wins'] += self.phase == 'VICTORY'
                self.state['resources']['value']['current']['values']['Arena_Token'] -= 1
        rows = []
        if self.phase == 'ARENA_LIST':
            opponents = self.state['arena']['value']['opponents']
            visible = opponents if self.scroll_position else [o for o in opponents if o['name'] == 'VisibleStrong']
            rows = [{'text': o['name'], 'conf': .99, 'x': 650, 'y': 350+i*150} for i,o in enumerate(visible)]
        return ArenaFrame(self.phase, rows=rows, selected_name=(self.selected or {}).get('name'),
                          own_power=self.state['arena']['value']['own_combat_power']['value'],
                          token_cost=1, token_currency_verified=True, auto_off=self.auto_off,
                          controls={'back': (100, 80), 'return_to_arena': (100,80)})

    def locate(self, target, observe, check_stop):
        def scroll(direction):
            check_stop()
            self.commands.append('scroll_'+direction)
            self.scroll_position = 0 if direction == 'up' else 1
        found, meta = search_selected_candidate(target, observe, scroll, self.stopped, max_steps=4)
        return (found[0], (1750, found[1]['y'])) if found else None

    def perform(self, command, frame, target=None):
        self.commands.append(command)
        if command == 'open_battles': self.phase = 'BATTLE_MENU'
        elif command == 'open_arena': self.phase = 'ARENA_LIST'
        elif command == 'open_formation': self.selected = target['opponent']; self.phase = 'FORMATION'
        elif command == 'start_battle': self.phase = 'BATTLE'; self.battle_reads = 0
        elif command in ('return_to_arena', 'back'):
            if command == 'return_to_arena':
                self.state['arena']['value']['opponents'] = [o for o in self.state['arena']['value']['opponents']
                    if o['player_id_bytes'] != self.selected['player_id_bytes']]
            self.phase, self.scroll_position = 'ARENA_LIST', 0
        else: raise ValueError(command)

    def screenshot(self, path):
        return None  # No fake screenshot is presented as a real Windows capture.
