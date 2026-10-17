import random
import copy
import itertools
from dragon_skills import Dragon, DEFENSE_POOL, get_offense_team, cast_skill, _mitigate

ELEMENTS = ["Red", "Green", "Blue", "Yellow", "Purple"]

ELEMENT_ADVANTAGE = {
    "Red":    {"Green": 1.5, "Blue": 0.5, "Red": 1.0, "Yellow": 1.0, "Purple": 1.0},
    "Green":  {"Blue": 1.5,  "Red": 0.5,  "Green": 1.0, "Yellow": 1.0, "Purple": 1.0},
    "Blue":   {"Red": 1.5,   "Green": 0.5, "Blue": 1.0,  "Yellow": 1.0, "Purple": 1.0},
    "Yellow": {"Purple": 1.5, "Yellow": 1.0, "Red": 1.0, "Green": 1.0, "Blue": 1.0},
    "Purple": {"Yellow": 1.5, "Purple": 1.0, "Red": 1.0, "Green": 1.0, "Blue": 1.0},
}

GEM_DAMAGE_RATIO = 1.0 / 3.0
COMBO_BONUS = 0.1
CRIT_MULT = 2.5
STRONG_HIT_MULT = 1.5

class Board7x5:
    def __init__(self):
        self.cols = 7
        self.rows = 5
        self.grid = []
        self.reset_board()

    def reset_board(self):
        self.grid = [[random.choice(ELEMENTS) for _ in range(self.cols)] for _ in range(self.rows)]
        while self.find_matches():
            self.grid = [[random.choice(ELEMENTS) for _ in range(self.cols)] for _ in range(self.rows)]

    def find_matches(self):
        runs = []
        for r in range(self.rows):
            c = 0
            while c < self.cols:
                start = c
                while c + 1 < self.cols and self.grid[r][c+1] == self.grid[r][start]:
                    c += 1
                if c - start + 1 >= 3: runs.append(("H", r, start, c))
                c += 1
        for c in range(self.cols):
            r = 0
            while r < self.rows:
                start = r
                while r + 1 < self.rows and self.grid[r+1][c] == self.grid[start][c]:
                    r += 1
                if r - start + 1 >= 3: runs.append(("V", c, start, r))
                r += 1
        return runs

    def execute_move(self, active_colors):
        candidates = []
        for r in range(self.rows):
            for c in range(self.cols - 1):
                self.grid[r][c], self.grid[r][c+1] = self.grid[r][c+1], self.grid[r][c]
                runs = self.find_matches()
                if runs:
                    score = 0
                    for run in runs:
                        if run[0] == "H":
                            _, row, cs, ce = run
                            color = self.grid[row][cs]
                            length = ce - cs + 1
                        else:
                            _, col, rs, re_ = run
                            color = self.grid[rs][col]
                            length = re_ - rs + 1
                        score += (2 if color in active_colors else 1) * length
                    candidates.append((score, (r, c), (r, c+1)))
                self.grid[r][c], self.grid[r][c+1] = self.grid[r][c+1], self.grid[r][c]

        if not candidates:
            self.reset_board()
            return self.execute_move(active_colors)

        candidates.sort(key=lambda x: x[0], reverse=True)
        _, p1, p2 = candidates[0]
        self.grid[p1[0]][p1[1]], self.grid[p2[0]][p2[1]] = self.grid[p2[0]][p2[1]], self.grid[p1[0]][p1[1]]
        return self._resolve_cascades()

    def _resolve_cascades(self):
        events = []
        runs = self.find_matches()
        while runs:
            run_data = []
            for run in runs:
                if run[0] == "H":
                    _, row, cs, ce = run
                    length = ce - cs + 1
                    coords = [(row, c) for c in range(cs, ce + 1)]
                else:
                    _, col, rs, re_ = run
                    length = re_ - rs + 1
                    coords = [(r, col) for r in range(rs, re_ + 1)]
                
                color = self.grid[coords[0][0]][coords[0][1]]
                mult = CRIT_MULT if length >= 5 else (STRONG_HIT_MULT if length == 4 else 1.0)
                run_data.append((color, coords, mult))

            for color, coords, mult in run_data:
                for r, c in coords:
                    events.append((color, c + 1, mult))
                    self.grid[r][c] = None

            for c in range(self.cols):
                empty = 0
                for r in range(self.rows - 1, -1, -1):
                    if self.grid[r][c] is None: empty += 1
                    elif empty > 0:
                        self.grid[r + empty][c] = self.grid[r][c]; self.grid[r][c] = None
                for r in range(empty): self.grid[r][c] = random.choice(ELEMENTS)
            runs = self.find_matches()
        return events


class PositionalTeamManager:
    def __init__(self, roster):
        self.active_slots = roster[:3] # [Top, Left, Right]
        self.bench = roster[3:]

    def get_column_zones(self):
        return {1: [1], 2: [1], 3: [0], 4: [0], 5: [2], 6: [2], 7: [2]}

    def update_roster(self):
        for i in range(len(self.active_slots)):
            if self.active_slots[i] and not self.active_slots[i].is_alive():
                self.active_slots[i] = self.bench.pop(0) if self.bench else None

    def get_alive_active(self):
        return [d for d in self.active_slots if d is not None and d.is_alive()]

    def is_eliminated(self):
        return not (any(d is not None and d.is_alive() for d in self.active_slots) or len(self.bench) > 0)


class PositionalBattleSimulator:
    def __init__(self, offense_roster, defense_roster):
        self.offense_mgr = PositionalTeamManager(offense_roster)
        self.defense_mgr = PositionalTeamManager(defense_roster)
        self.off_board = Board7x5()
        self.def_board = Board7x5()

    def _best_attacker(self, color, active):
        c = [d for d in active if d.element == color and d.is_alive()]
        return max(c, key=lambda d: d.atk) if c else None

    def _resolve_side(self, board, attacker_mgr, defender_mgr):
        active_att = attacker_mgr.get_alive_active()
        if not active_att: return

        events = board.execute_move([d.element for d in active_att])
        zone_map = defender_mgr.get_column_zones()
        combo = 0
        
        for color, col, mult in events:
            for d in active_att:
                if d.element == color and d.is_alive(): d.gain_spirit(1)
            
            slots = zone_map.get(col, [])
            valid = [defender_mgr.active_slots[s] for s in slots
                     if defender_mgr.active_slots[s] and defender_mgr.active_slots[s].is_alive()]
            if not valid: continue
                
            target = random.choice(valid)
            attacker = self._best_attacker(color, active_att)
            
            if attacker is None: dmg = 1
            else:
                base = attacker.atk * GEM_DAMAGE_RATIO * mult
                combo += 1
                combo_mult = 1.0 + COMBO_BONUS * (combo - 1)
                elem = ELEMENT_ADVANTAGE[color][target.element]
                crit_chance_mult = CRIT_MULT if (attacker.crit_chance > 0 and random.random() < attacker.crit_chance) else 1.0
                dmg = max(1, _mitigate(base * combo_mult * elem * crit_chance_mult, target.defense))
                
            target.take_damage(dmg)

    def run_turn(self):
        self.offense_mgr.update_roster()
        self.defense_mgr.update_roster()

        self._resolve_side(self.off_board, self.offense_mgr, self.defense_mgr)
        self._resolve_side(self.def_board, self.defense_mgr, self.offense_mgr)

        for d in self.offense_mgr.get_alive_active(): d.gain_spirit(1)
        for d in self.defense_mgr.get_alive_active(): d.gain_spirit(1)

        for d in list(self.offense_mgr.get_alive_active()):
            if d.is_alive() and d.current_spirit >= d.spirit_req:
                cast_skill(d, self.offense_mgr, self.defense_mgr)

        for d in list(self.defense_mgr.get_alive_active()):
            if d.is_alive() and d.current_spirit >= d.spirit_req:
                cast_skill(d, self.defense_mgr, self.offense_mgr)

        for d in self.offense_mgr.get_alive_active() + self.defense_mgr.get_alive_active():
            if d.is_alive(): d.process_turn()

    def simulate(self):
        turns = 0
        while turns < 120:
            self.offense_mgr.update_roster()
            self.defense_mgr.update_roster()
            if self.defense_mgr.is_eliminated(): return "Offense Win"
            if self.offense_mgr.is_eliminated(): return "Defense Win"
            
            self.run_turn()
            turns += 1
            
        off_alive = self.offense_mgr.get_alive_active()
        def_alive = self.defense_mgr.get_alive_active()
        off_score = len(off_alive) * 1000 + sum(d.current_hp for d in off_alive)
        def_score = len(def_alive) * 1000 + sum(d.current_hp for d in def_alive)
        return "Offense Win" if off_score > def_score else "Defense Win"

# ==========================================
# 9P5 BRUTE-FORCE SEARCH (50 ITERATIONS)
# ==========================================

def find_top_defense_teams():
    # Filtered list of only the 9 viable dragons you specified
    viable_dragons = [
        "Stormfly", "Murmurquil", "Sawmaw", "Toothless", "Shattermaster", 
        "Meatlug", "Radiant Skyglow", "Harvest Stormfly", "Sunsail Windshear"
    ]
    
    # 9P5 = 15,120 permutations
    all_perms = list(itertools.permutations(viable_dragons, 5))
    total_perms = len(all_perms)
    
    # 50 iterations gives a very accurate win rate
    iterations_per_team = 50
    
    print(f"Testing {total_perms:,} teams ({iterations_per_team} battles each)...")
    print(f"Total simulations: {total_perms * iterations_per_team:,}")
    print("Running... This should take 2-4 minutes depending on your CPU.\n")
    
    results = []
    
    for idx, seq in enumerate(all_perms):
        defense_wins = 0
        
        for _ in range(iterations_per_team):
            offense = get_offense_team()
            defense = [copy.deepcopy(DEFENSE_POOL[n]) for n in seq]
            sim = PositionalBattleSimulator(offense, defense)
            if sim.simulate() == "Defense Win":
                defense_wins += 1
                
        win_rate = (defense_wins / iterations_per_team) * 100
        results.append((win_rate, seq))
        
        # Progress tracker
        if (idx + 1) % 2000 == 0:
            print(f"Progress: {idx + 1:,} / {total_perms:,} teams tested...")
        
    # Sort by highest win rate
    results.sort(key=lambda x: x[0], reverse=True)
    
    print("\n" + "=" * 60)
    print("TOP 5 DEFENSE TEAMS (Out of 15,120 permutations)")
    print("=" * 60)
    
    for rank, (win_rate, seq) in enumerate(results[:5], 1):
        print(f"\n#{rank} - Defense Win Rate: {win_rate:.1f}%")
        print(f"  [Top]    : {seq[0]}")
        print(f"  [Left]   : {seq[1]}")
        print(f"  [Right]  : {seq[2]}")
        print(f"  [Bench 1]: {seq[3]}")
        print(f"  [Bench 2]: {seq[4]}")
        
    print("\n" + "-" * 60)
    worst_rate, worst_seq = results[-1]
    print(f"WORST TEAM (Win Rate: {worst_rate:.1f}%)")
    print(f"  {worst_seq}")

if __name__ == "__main__":
    find_top_defense_teams()