import random

SPIRIT_SPEEDS = {
    "Very Fast": 8, "Fast": 9, "Moderate": 10, "Slow": 11, "Very Slow": 12
}

DEF_K = 1250.0  # Calibrated mitigation factor

def _mitigate(dmg, defense):
    return dmg * (1.0 / (1.0 + defense / DEF_K))

class Dragon:
    def __init__(self, name, element, atk, defense, hp, spirit_speed, skill_id):
        self.name = name
        self.element = element
        self.atk = atk
        self.defense = defense
        self.max_hp = hp
        self.current_hp = hp
        self.spirit_speed = spirit_speed
        self.spirit_req = SPIRIT_SPEEDS[spirit_speed]
        self.current_spirit = 0
        self.skill_id = skill_id

        # Status Effects
        self.heal_blocked_turns = 0
        self.ability_locked_turns = 0
        self.atk_buff_turns = 0
        self.atk_buff_mult = 1.0
        self.def_buff_turns = 0
        self.counter_ratio = 0.0
        self.counter_turns = 0
        self.vulnerability_turns = 0
        self.vulnerability_mult = 1.0
        self.shield_hp = 0
        self.crit_chance = 0.0
        self.crit_turns = 0
        self.dot_damage_per_turn = 0
        self.dot_turns = 0

    def is_alive(self):
        return self.current_hp > 0

    def take_damage(self, amount, attacker=None):
        if not self.is_alive(): return
        dmg = amount
        if self.vulnerability_turns > 0: dmg *= self.vulnerability_mult
        if self.def_buff_turns > 0: dmg *= 0.55
        if self.shield_hp > 0:
            absorbed = min(self.shield_hp, dmg)
            self.shield_hp -= absorbed
            dmg -= absorbed
        self.current_hp = max(0, self.current_hp - dmg)
        
        if attacker and attacker.is_alive() and self.counter_turns > 0:
            counter_dmg = amount * self.counter_ratio
            attacker.take_damage(counter_dmg)

    def heal(self, amount):
        if self.is_alive() and self.heal_blocked_turns == 0:
            self.current_hp = min(self.max_hp, self.current_hp + amount)

    def gain_spirit(self, amount):
        if self.is_alive():
            self.current_spirit = min(self.spirit_req, self.current_spirit + amount)

    def process_turn(self):
        if self.dot_turns > 0 and self.is_alive():
            self.take_damage(self.dot_damage_per_turn)
            self.dot_turns -= 1
            if self.dot_turns == 0: self.dot_damage_per_turn = 0
            
        if self.heal_blocked_turns > 0:   self.heal_blocked_turns -= 1
        if self.ability_locked_turns > 0: self.ability_locked_turns -= 1
        if self.atk_buff_turns > 0:
            self.atk_buff_turns -= 1
            if self.atk_buff_turns == 0: self.atk_buff_mult = 1.0
        if self.def_buff_turns > 0:  self.def_buff_turns -= 1
        if self.counter_turns > 0:   self.counter_turns -= 1
        if self.vulnerability_turns > 0:
            self.vulnerability_turns -= 1
            if self.vulnerability_turns == 0: self.vulnerability_mult = 1.0
        if self.crit_turns > 0:
            self.crit_turns -= 1
            if self.crit_turns == 0: self.crit_chance = 0.0

DEFENSE_POOL = {
    "Stormfly":              Dragon("Stormfly", "Blue", 583, 609, 2528, "Fast", "Stormfly"),
    "Toothless":             Dragon("Toothless", "Purple", 585, 562, 2740, "Fast", "Toothless"),
    "Shattermaster":         Dragon("Shattermaster", "Yellow", 570, 640, 2650, "Slow", "Shattermaster"),
    "Murmurquil":            Dragon("Murmurquil", "Purple", 561, 614, 2730, "Fast", "Murmurquil"),
    "Slick Nicker":          Dragon("Slick Nicker", "Red", 589, 535, 2818, "Very Fast", "Slick_Nicker"),
    "Crom Lech":             Dragon("Crom Lech", "Green", 565, 610, 2710, "Slow", "Crom_Lech"),
    "Sawmaw":                Dragon("Sawmaw", "Green", 580, 620, 2600, "Very Fast", "Sawmaw"),
    "Seezering Seetle":      Dragon("The Searing Seethsizzle", "Red", 540, 606, 2760, "Very Fast", "Searing_Seethsizzle"),
    "Radiant Skyglow":       Dragon("Radiant Skyglow", "Blue", 597, 537, 2622, "Slow", "Radiant_Skyglow"),
    "Easter Barf & Belch":   Dragon("Easter Barf & Belch", "Blue", 610, 550, 2700, "Moderate", "Easter_Barf_Belch"),
    "Infamous Flameout":     Dragon("Infamous Flameout", "Blue", 625, 515, 2656, "Very Fast", "Infamous_Flameout"),
    "Harvest Stormfly":      Dragon("Harvest Stormfly", "Yellow", 618, 598, 2500, "Very Fast", "Harvest_Stormfly"),
    "Maeve Heart":           Dragon("Maeve Heart", "Yellow", 550, 620, 2780, "Moderate", "Maeve_Heart"),
    "Sunsail Windshear":     Dragon("Sunsail Windshear", "Green", 576, 606, 2878, "Slow", "Sunsail_Windshear"),
    "Freedom Hookfang":      Dragon("Freedom Hookfang", "Yellow", 588, 563, 2800, "Moderate", "Freedom_Hookfang"),
    "Meatlug":               Dragon("Meatlug", "Yellow", 520, 680, 2800, "Fast", "Meatlug"),
}

def get_offense_team():
    return [
        Dragon("Stormfly", "Blue", 610, 580, 2600, "Fast", "Stormfly"),
        Dragon("Fearsome Flamellion", "Red", 596, 555, 2622, "Slow", "Fearsome_Flamellion"),
        Dragon("Thanksgiving Meatlug", "Yellow", 567, 555, 2562, "Moderate", "Thanksgiving_Meatlug"),
        Dragon("Valiant Vingthor", "Green", 526, 552, 2956, "Moderate", "Valiant_Vingthor"),
        Dragon("Shattermaster", "Purple", 570, 640, 2650, "Slow", "Shattermaster"),
    ]

def cast_skill(caster, allies_mgr, enemies_mgr):
    if caster.ability_locked_turns > 0: return
    caster.current_spirit = 0
    allies = allies_mgr.get_alive_active()
    enemies = enemies_mgr.get_alive_active()
    if not enemies: return
    
    atk_mult = caster.atk_buff_mult if caster.atk_buff_turns > 0 else 1.0
    target = min(enemies, key=lambda x: x.current_hp)

    def raw(pct, tgt):
        return _mitigate(caster.atk * pct * atk_mult, tgt.defense)

    if caster.skill_id == "Radiant_Skyglow":
        for a in allies:
            a.def_buff_turns = 4
            if a != caster:
                a.gain_spirit(a.spirit_req * 0.25); a.counter_ratio = 2.05; a.counter_turns = 4
    elif caster.skill_id == "Toothless":
        target.take_damage(raw(1.90, target), caster)
        others = [e for e in enemies if e != target]
        if others: o = random.choice(others); o.take_damage(raw(1.90, o), caster)
        for e in enemies: e.current_spirit = max(0, e.current_spirit - (e.spirit_req * 0.30))
        for a in allies:
            if a != caster: a.gain_spirit(a.spirit_req * 0.25)
    elif caster.skill_id == "Stormfly":
        for e in enemies:
            e.dot_damage_per_turn = _mitigate(caster.atk * (1.70 / 4) * atk_mult, e.defense)
            e.dot_turns = 4; e.vulnerability_turns = 5; e.vulnerability_mult = 1.40
        weakest = min(allies, key=lambda x: x.current_hp)
        bonus = weakest.max_hp * 0.30; weakest.max_hp += bonus; weakest.current_hp += bonus
    elif caster.skill_id == "Murmurquil":
        total = 0
        for e in enemies:
            d = raw(1.74, e); e.take_damage(d, caster); total += d; e.heal_blocked_turns = 5
        caster.heal(total * 0.15)
        for a in allies: a.atk_buff_turns = 5; a.atk_buff_mult = 1.35
    elif caster.skill_id == "Sawmaw":
        total = 0
        for e in enemies:
            d = raw(1.64, e); e.take_damage(d, caster); total += d
            e.current_spirit = max(0, e.current_spirit - (e.spirit_req * 0.30))
        caster.heal(total * 0.10)
        for a in allies: a.atk_buff_turns = max(a.atk_buff_turns, 4); a.atk_buff_mult = max(a.atk_buff_mult, 1.25)
    elif caster.skill_id == "Shattermaster":
        for e in enemies: e.ability_locked_turns = 5
        for a in allies:
            a.atk_buff_turns = max(a.atk_buff_turns, 3); a.atk_buff_mult = max(a.atk_buff_mult, 1.25)
            if a != caster: a.gain_spirit(a.spirit_req * 0.33)
    elif caster.skill_id == "Easter_Barf_Belch":
        for e in enemies:
            e.dot_damage_per_turn = _mitigate(caster.atk * (3.20 / 4) * atk_mult, e.defense); e.dot_turns = 4
        for a in allies: a.atk_buff_turns = max(a.atk_buff_turns, 3); a.atk_buff_mult = max(a.atk_buff_mult, 1.25)
    elif caster.skill_id == "Meatlug":
        for e in enemies:
            e.take_damage(raw(1.55, e), caster); e.atk_buff_turns = 5; e.atk_buff_mult = 0.75
        weakest = min(allies, key=lambda x: x.current_hp); weakest.gain_spirit(weakest.spirit_req * 0.60)
    elif caster.skill_id == "Thanksgiving_Meatlug":
        for _ in range(5):
            if enemies: t = random.choice(enemies); t.take_damage(raw(0.80, t), caster)
        for a in allies:
            bonus = a.max_hp * 0.32; a.max_hp += bonus; a.current_hp += bonus
            a.crit_chance = 0.40; a.crit_turns = 5
    elif caster.skill_id == "Infamous_Flameout":
        target.take_damage(raw(3.00, target), caster); caster.take_damage(caster.atk * 1.95)
        for a in allies:
            if a != caster: a.heal(a.max_hp * 0.33)
    elif caster.skill_id == "Slick_Nicker":
        target.take_damage(raw(1.70, target), caster)
        others = [e for e in enemies if e != target]
        if others: o = random.choice(others); o.take_damage(raw(1.70, o), caster)
        target.def_buff_turns = 0; target.atk_buff_turns = 0; target.counter_turns = 0; target.atk_buff_mult = 1.0
        caster.counter_ratio = 2.35; caster.counter_turns = 5
    elif caster.skill_id == "Searing_Seethsizzle":
        target.take_damage(raw(2.50, target), caster)
        caster.atk_buff_turns = 4; caster.atk_buff_mult = 1.32
        caster.gain_spirit(caster.spirit_req * 0.25)
    elif caster.skill_id == "Harvest_Stormfly":
        target.dot_damage_per_turn = _mitigate(caster.atk * (2.10 / 5) * atk_mult, target.defense)
        target.dot_turns = 5; target.heal_blocked_turns = 5
        for a in allies:
            if a != caster: a.gain_spirit(a.spirit_req * 0.25)
    elif caster.skill_id == "Maeve_Heart":
        for e in enemies:
            e.dot_damage_per_turn = _mitigate(caster.atk * (1.60 / 4) * atk_mult, e.defense)
            e.dot_turns = 4; e.vulnerability_turns = 4; e.vulnerability_mult = 1.30
            e.atk_buff_turns = max(e.atk_buff_turns, 4); e.atk_buff_mult = min(e.atk_buff_mult, 0.62)
    elif caster.skill_id == "Sunsail_Windshear":
        total = 0
        for e in enemies:
            d = raw(1.79, e); e.take_damage(d, caster); total += d
        caster.heal(total * 0.05)
        for a in allies:
            if a != caster:
                bonus = a.max_hp * 0.30; a.max_hp += bonus; a.current_hp += bonus
                a.atk_buff_turns = max(a.atk_buff_turns, 5); a.atk_buff_mult = max(a.atk_buff_mult, 1.45)
    elif caster.skill_id == "Freedom_Hookfang":
        for _ in range(10):
            if enemies: t = random.choice(enemies); t.take_damage(raw(0.95, t), caster)
        for a in allies:
            a.gain_spirit(a.spirit_req * 0.15); a.atk_buff_turns = max(a.atk_buff_turns, 4); a.atk_buff_mult = max(a.atk_buff_mult, 1.40)
    elif caster.skill_id == "Crom_Lech":
        target.take_damage(raw(1.70, target), caster)
        others = [e for e in enemies if e != target]
        if others: o = random.choice(others); o.take_damage(raw(1.70, o), caster)
        for a in allies: a.shield_hp += a.max_hp * 0.30
    elif caster.skill_id == "Fearsome_Flamellion":
        for e in enemies:
            e.dot_damage_per_turn = _mitigate(caster.atk * (1.80 / 3) * atk_mult, e.defense)
            e.dot_turns = 3; e.ability_locked_turns = 3
        for a in allies: a.atk_buff_turns = max(a.atk_buff_turns, 3); a.atk_buff_mult = max(a.atk_buff_mult, 1.30)
    elif caster.skill_id == "Valiant_Vingthor":
        for _ in range(3):
            if enemies: t = random.choice(enemies); t.take_damage(raw(1.20, t), caster)
        for a in allies:
            a.crit_chance = max(a.crit_chance, 0.40); a.crit_turns = 5
            if a != caster: a.gain_spirit(a.spirit_req * 0.20)