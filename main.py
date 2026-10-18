import random
import itertools
import csv
import time
import os
from collections import Counter
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
DEFENSE_AUTO_MULT = 1.5 

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

class SlotWrapper:
    def __init__(self, dragon, original_number):
        self.dragon = dragon
        self.original_number = original_number

class PositionalTeamManager:
    def __init__(self, roster):
        self.active_slots = [
            SlotWrapper(roster[0], 1),
            SlotWrapper(roster[1], 2),
            SlotWrapper(roster[2], 3)
        ]
        self.bench = []
        for i in range(3, 10):
            if i < len(roster) and roster[i] is not None:
                self.bench.append(SlotWrapper(roster[i], i+1))
            else:
                self.bench.append(None)

    def get_column_zones(self):
        return {1: [1], 2: [1], 3: [0], 4: [0], 5: [2], 6: [2], 7: [2]}

    def update_roster(self):
        for i in range(len(self.active_slots)):
            if self.active_slots[i] and not self.active_slots[i].dragon.is_alive():
                while self.bench and (self.bench[0] is None or not self.bench[0].dragon.is_alive()):
                    self.bench.pop(0)
                self.active_slots[i] = self.bench.pop(0) if self.bench else None

    def get_alive_active(self):
        return [slot for slot in self.active_slots if slot is not None and slot.dragon.is_alive()]

    def get_cast_order(self):
        alive_slots = self.get_alive_active() + [s for s in self.bench if s is not None and s.dragon.is_alive()]
        alive_slots.sort(key=lambda s: s.original_number)
        return [slot.dragon for slot in alive_slots]

    def is_eliminated(self):
        return not (any(s is not None and s.dragon.is_alive() for s in self.active_slots) or 
                    any(s is not None and s.dragon.is_alive() for s in self.bench))

    def get_alive_dragons(self):
        return [s.dragon for s in self.get_alive_active()]

class SkillManagerWrapper:
    def __init__(self, team_mgr):
        self.team_mgr = team_mgr
    def get_alive_active(self):
        return self.team_mgr.get_alive_dragons()

class PositionalBattleSimulator:
    def __init__(self, offense_roster, defense_roster, board_pool):
        self.offense_mgr = PositionalTeamManager(offense_roster)
        self.defense_mgr = PositionalTeamManager(defense_roster)
        self.off_skill_mgr = SkillManagerWrapper(self.offense_mgr)
        self.def_skill_mgr = SkillManagerWrapper(self.defense_mgr)
        
        self.off_board = board_pool.pop()
        self.def_board = board_pool.pop()
        self.board_pool = board_pool

    def _best_attacker(self, color, active_slots):
        c = [s.dragon for s in active_slots if s.dragon.element == color and s.dragon.is_alive()]
        return max(c, key=lambda d: d.atk) if c else None

    def _resolve_side(self, board, attacker_mgr, defender_mgr):
        active_att = attacker_mgr.get_alive_active()
        if not active_att: return

        active_colors = [s.dragon.element for s in active_att]
        events = board.execute_move(active_colors)
        
        zone_map = defender_mgr.get_column_zones()
        combo = 0
        
        for color, col, mult in events:
            for slot in active_att:
                if slot.dragon.element == color and slot.dragon.is_alive(): 
                    slot.dragon.gain_spirit(1)
            
            slots = zone_map.get(col, [])
            valid = [defender_mgr.active_slots[s] for s in slots
                     if defender_mgr.active_slots[s] and defender_mgr.active_slots[s].dragon.is_alive()]
            if not valid: continue
                
            target_slot = random.choice(valid)
            target = target_slot.dragon
            
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

        for slot in self.offense_mgr.get_alive_active(): slot.dragon.gain_spirit(1)
        for slot in self.defense_mgr.get_alive_active(): slot.dragon.gain_spirit(1)

        for d in self.offense_mgr.get_cast_order():
            if d.is_alive() and d.current_spirit >= d.spirit_req:
                cast_skill(d, self.off_skill_mgr, self.def_skill_mgr)

        for d in self.defense_mgr.get_cast_order():
            if d.is_alive() and d.current_spirit >= d.spirit_req:
                cast_skill(d, self.def_skill_mgr, self.off_skill_mgr)

        for slot in self.offense_mgr.get_alive_active() + self.defense_mgr.get_alive_active():
            if slot.dragon.is_alive(): slot.dragon.process_turn()

    def simulate(self):
        self.off_board.reset_board()
        self.def_board.reset_board()
        
        turns = 0
        while turns < 40:
            self.offense_mgr.update_roster()
            self.defense_mgr.update_roster()
            
            if self.defense_mgr.is_eliminated(): 
                result = "Offense Win"
                break
            if self.offense_mgr.is_eliminated(): 
                result = "Defense Win"
                break
            
            self.run_turn()
            turns += 1
        else:
            off_hp = sum(s.dragon.current_hp for s in self.offense_mgr.get_alive_active())
            def_hp = sum(s.dragon.current_hp for s in self.defense_mgr.get_alive_active())
            result = "Offense Win" if off_hp > def_hp else "Defense Win"
            
        self.board_pool.append(self.off_board)
        self.board_pool.append(self.def_board)
        return result

def run_battles_until_losses(seq, board_pool, max_losses=7):
    wins = 0
    losses = 0
    base_offense = get_offense_team()
    base_defense = [DEFENSE_POOL[n] for n in seq if n is not None]
    
    while losses < max_losses:
        offense = [Dragon(d.name, d.element, d.atk, d.defense, d.max_hp, d.spirit_speed, d.skill_id) for d in base_offense]
        defense = [Dragon(d.name, d.element, d.atk, d.defense, d.max_hp, d.spirit_speed, d.skill_id) for d in base_defense]
        
        sim = PositionalBattleSimulator(offense, defense, board_pool)
        if sim.simulate() == "Defense Win":
            wins += 1
        else:
            losses += 1
            
    return wins

def run_simulation():
    core_5 = ["Stormfly", "Sawmaw", "Toothless", "Murmurquil", "Shattermaster"]
    pool_14 = [
        "Stormfly", "Sawmaw", "Toothless", "Murmurquil", "Shattermaster",
        "Meatlug", "Sunsail Windshear", "Slick Nicker", "Infamous Flameout", 
        "Seezering Seetle", "Harvest Stormfly", "Crom Lech", "Easter Barf & Belch",
        "Freedom Hookfang"
    ]
    
    # ==========================================
    # STAGE 1: 60 Frontline Permutations
    # ==========================================
    print("STAGE 1: Testing 60 Frontlines (Max 7 Losses)...")
    frontlines = list(itertools.permutations(core_5, 3))
    stage1_results = []
    board_pool = [Board7x5() for _ in range(60)]
    
    start_time = time.time()
    for idx, front in enumerate(frontlines):
        team = list(front) + [None] * 7
        wins = run_battles_until_losses(team, board_pool, max_losses=7)
        stage1_results.append((wins, front))
        
        elapsed = time.time() - start_time
        print(f"[{elapsed:5.1f}s] {idx + 1:>2}/60 | {wins} wins | {front}")
        
    stage1_results.sort(key=lambda x: x[0], reverse=True)
    
    if len(stage1_results) > 15:
        cutoff = stage1_results[14][0]
        current_teams = [res for res in stage1_results if res[0] >= cutoff]
    else:
        current_teams = stage1_results
        
    print(f"\nSTAGE 1 COMPLETE. {len(current_teams)} Frontlines passed.")
    
    # ==========================================
    # STAGE 2 A-G: Add one dragon at a time
    # ==========================================
    cutoffs = [30, 45, 60, 75, 90, 105]
    
    for stage_idx in range(7):
        stage_letter = chr(65 + stage_idx) # A, B, C...
        dragon_slot = stage_idx + 4 # Bench 1 is slot 4
        
        print(f"\nSTAGE 2{stage_letter}: Adding Dragon {dragon_slot} (Max 7 Losses)...")
        
        stage_results = []
        board_pool = [Board7x5() for _ in range(60)]
        
        start_time = time.time()
        
        for idx, (_, team_so_far) in enumerate(current_teams):
            available_dragons = [d for d in pool_14 if d not in team_so_far]
            
            for new_dragon in available_dragons:
                new_team = list(team_so_far) + [new_dragon] + [None] * (6 - stage_idx)
                wins = run_battles_until_losses(new_team, board_pool, max_losses=7)
                stage_results.append((wins, tuple(new_team[:dragon_slot])))
                
            if (idx + 1) % 10 == 0 or (idx + 1) == len(current_teams):
                elapsed = time.time() - start_time
                print(f"  [{elapsed:5.1f}s] Tested options for {idx+1}/{len(current_teams)} base teams...")
                
        stage_results.sort(key=lambda x: x[0], reverse=True)
        
        # Apply cutoffs
        if stage_idx < len(cutoffs):
            target_cutoff = cutoffs[stage_idx]
            if len(stage_results) > target_cutoff:
                cutoff_val = stage_results[target_cutoff - 1][0]
                current_teams = [res for res in stage_results if res[0] >= cutoff_val]
            else:
                current_teams = stage_results
        else:
            # For the last stage (2G), keep the Top 100 (including ties)
            target_cutoff = 100
            if len(stage_results) > target_cutoff:
                cutoff_val = stage_results[target_cutoff - 1][0]
                current_teams = [res for res in stage_results if res[0] >= cutoff_val]
            else:
                current_teams = stage_results
                
        print(f"  STAGE 2{stage_letter} COMPLETE. {len(current_teams)} teams passed.")
    
    # ==========================================
    # FINAL RESULTS (From Stage 2G)
    # ==========================================
    # current_teams is already the final Top 100+ from Stage 2G.
    # We just need to pad any teams that didn't reach 10 dragons (shouldn't happen in 2G)
    final_results = []
    for wins, team in current_teams:
        if len(team) < 10:
            available = [d for d in pool_14 if d not in team]
            random.shuffle(available)
            team = tuple(list(team) + available[:10-len(team)])
        final_results.append((wins, team))
        
    final_results.sort(key=lambda x: x[0], reverse=True)
    
    with open("all_win_rates.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Wins", "Top", "Left", "Right", "Bench 1", "Bench 2", "Bench 3", "Bench 4", "Bench 5", "Bench 6", "Bench 7"])
        for wins, team in final_results:
            writer.writerow([wins] + list(team))
    print(f"\nSaved all results to 'all_win_rates.csv'")

    print("\n" + "=" * 60)
    print("FINAL TOP 10 DEFENSE TEAMS (By Wins)")
    print("=" * 60)
    
    for rank, (wins, team) in enumerate(final_results[:10], 1):
        print(f"\n#{rank} - {wins} Wins")
        for i, name in enumerate(team, 1):
            slot_name = ["Top", "Left", "Right", "Bench 1", "Bench 2", "Bench 3", "Bench 4", "Bench 5", "Bench 6", "Bench 7"][i-1]
            print(f"  [{slot_name:<7}]: {name}")

    if len(final_results) > 10:
        print("\n" + "-" * 60)
        print("RUNNER UPS (Ranks 11-100+)")
        print("-" * 60)
        for rank, (wins, team) in enumerate(final_results[10:100], 11):
            print(f"#{rank:>2} - {wins} wins | {team}")
            
    print("\n" + "=" * 60)
    print("TOP 100 DRAGON USAGE STATISTICS")
    print("=" * 60)

    top_100_final = [team for wins, team in final_results[:100]]
    
    def print_ranking(title, counter):
        print(f"\n--- {title} ---")
        for i, (dragon, count) in enumerate(counter.most_common(), 1):
            if dragon:
                print(f"  #{i:<2} {dragon:<20} : {count}")

    all_dragons = [d for team in top_100_final for d in team if d]
    print_ranking("MOST USED DRAGON (Overall)", Counter(all_dragons))

    pos_names = ["TOP", "LEFT", "RIGHT", "BENCH 1", "BENCH 2", "BENCH 3", "BENCH 4", "BENCH 5", "BENCH 6", "BENCH 7"]
    for i in range(10):
        pos_dragons = [team[i] for team in top_100_final if len(team) > i]
        print_ranking(f"MOST USED {pos_names[i]}", Counter(pos_dragons))

if __name__ == "__main__":
    print("============================================================")
    print("TITAN UPRISING PVP DEFENSE SIMULATOR")
    print("============================================================")
    run_simulation()