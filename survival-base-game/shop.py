"""Магазин между волнами."""

from settings import *


SHOP_ITEMS = [
    {"id": "medkit", "key": "4", "name": "Аптечка", "cost": SHOP_MEDKIT_COST, "desc": "+40 HP"},
    {"id": "key", "key": "5", "name": "Ключ", "cost": SHOP_KEY_COST, "desc": "+1 ключ"},
    {"id": "base", "key": "6", "name": "Ремонт базы", "cost": SHOP_BASE_REPAIR_COST, "desc": f"+{SHOP_BASE_REPAIR_AMOUNT} HP базы"},
    {"id": "turret", "key": "7", "name": "Турель", "cost": SHOP_TURRET_BUY_COST, "desc": "купить / улучшить"},
]


def buy(game, item_id):
    p = game.player
    if item_id == "medkit":
        if p.coins < SHOP_MEDKIT_COST:
            return "Нет монет"
        p.coins -= SHOP_MEDKIT_COST
        p.heal(40)
        return "Куплена аптечка"
    if item_id == "key":
        if p.coins < SHOP_KEY_COST:
            return "Нет монет"
        p.coins -= SHOP_KEY_COST
        p.keys += 1
        return "Куплен ключ"
    if item_id == "base":
        if p.coins < SHOP_BASE_REPAIR_COST:
            return "Нет монет"
        p.coins -= SHOP_BASE_REPAIR_COST
        max_base = BASE_HP + (game.level - 1) * 25
        game.base_hp = min(max_base, game.base_hp + SHOP_BASE_REPAIR_AMOUNT)
        return "База отремонтирована"
    if item_id == "turret":
        if game.turret.level == 0:
            if p.coins < SHOP_TURRET_BUY_COST:
                return "Нет монет"
            p.coins -= SHOP_TURRET_BUY_COST
            game.turret.activate()
            return "Турель установлена!"
        if p.coins < SHOP_TURRET_UPGRADE_COST:
            return "Нет монет"
        p.coins -= SHOP_TURRET_UPGRADE_COST
        lvl = game.turret.upgrade()
        return f"Турель ур. {lvl}"
    return None
