# Titan Uprising PvP Defense Team Simulation

This Python script brute-forces the best possible PvP Defense Team in *Dragons: Titan Uprising* against a specific Attack Team.

## Mechanics Simulated
- **7x5 Board:** Simulates gem drops, cascades, and combos.
- **Positional Targeting:** Column 1-2 hits Left, 3-4 hits Top, 5-7 hits Right.
- **Gem Damage:** 1/3 of Dragon ATK, modified by defense (`DEF_K = 1250`), elemental advantage, and combo multipliers.
- **Skill Casting:** Full implementation of DoTs, Shields, Counters, Buffs, and Debuffs for all 16+ dragons.
- **AI:** Both offense and defense greedily match gems and cast skills.

## Usage
Run the main script to test all **15,120 permutations** (9P5) of the selected viable defense dragons over 50 battles each to find the Top 5 mathematically strongest defenses.

```bash
python main.py