"""Перки при переходе на новый уровень."""

import random

ALL_PERKS = [
    {"id": "hp", "name": "Живучесть", "desc": "+35 к макс. HP"},
    {"id": "speed", "name": "Спринт", "desc": "+45 к скорости"},
    {"id": "damage", "name": "Сила", "desc": "+6 к урону"},
    {"id": "base", "name": "Укрепление базы", "desc": "База +80 HP"},
    {"id": "keys", "name": "Связка ключей", "desc": "+2 ключа"},
    {"id": "ammo", "name": "Ящик патронов", "desc": "+40 патронов"},
    {"id": "vampire", "name": "Вампиризм", "desc": "+6 HP за убийство"},
    {"id": "turret", "name": "Турель базы", "desc": "Бесплатная турель ур.1"},
]


def roll_perk_choices(count=3):
    pool = ALL_PERKS[:]
    random.shuffle(pool)
    return pool[:count]


def apply_perk(game, perk_id):
    from settings import BASE_HP

    p = game.player
    if perk_id == "hp":
        p.max_hp += 35
        p.hp += 35
    elif perk_id == "speed":
        p.speed += 45
    elif perk_id == "damage":
        p.damage += 6
    elif perk_id == "base":
        game.base_hp = min(BASE_HP + (game.level - 1) * 30, game.base_hp + 80)
    elif perk_id == "keys":
        p.keys += 2
    elif perk_id == "ammo":
        p.ammo += 40
    elif perk_id == "vampire":
        p.lifesteal += 6
    elif perk_id == "turret":
        if game.turret.level == 0:
            game.turret.activate()
        else:
            game.turret.upgrade()
