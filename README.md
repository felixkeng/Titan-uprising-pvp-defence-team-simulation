# Titan Uprising PvP Defense Simulator

A Python-based Monte Carlo simulation designed to find the mathematically optimal PvP defense team in *Dragons: Titan Uprising*. 

## Features
- **Full 10-Dragon Roster:** Simulates the 3 frontline slots and 7 bench slots exactly as they appear in the game.
- **Turn-Order Mechanics:** Skills fire in strict sequence (Top -> Left -> Right -> Bench 1-7), meaning buffs and debuffs apply exactly when they should.
- **Accurate Skill Logic:** Includes DoTs, buffs, spirit drains, counters, and the "overwrite, don't stack" rule for status effects. 
- **15% Defense Stat Buff:** All defense dragons receive the 15% stat bonus applied in the game.
- **Wins-Not-Percentage:** Instead of a fixed number of battles, the simulator counts how many wins a team can string together before hitting a 7-loss cutoff. This eliminates RNG flukes and measures consistency.
- **Iterative Deep Dive (Stages 1 - 2G):** 
  - **Stage 1:** Tests all 60 frontline permutations.
  - **Stage 2A-2G:** Adds one bench dragon at a time, testing all available options, and keeping the Top 30, 45, 60, 75, 90, and 105 teams at each step.

## How to Run
1. Ensure you have Python 3.8+ installed.
2. Clone this repository.
3. Ensure both `main.py` and `dragon_skills.py` are in the same folder.
4. Run the simulation:
   ```bash
   python3 main.py