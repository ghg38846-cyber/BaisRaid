"""Сохранение прогресса и настроек в JSON."""

import json
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent
SAVE_PATH = GAME_DIR / "savegame.json"
CONFIG_PATH = GAME_DIR / "config.json"

DEFAULT_CONFIG = {
    "sfx_volume": 0.7,
    "music_volume": 0.5,
    "fullscreen": True,
}


def load_config():
    if not CONFIG_PATH.exists():
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        cfg = DEFAULT_CONFIG.copy()
        cfg.update(data)
        return cfg
    except (json.JSONDecodeError, OSError):
        return DEFAULT_CONFIG.copy()


def save_config(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def has_save():
    return SAVE_PATH.exists()


def delete_save():
    if SAVE_PATH.exists():
        SAVE_PATH.unlink()


def save_game(game):
    p = game.player
    data = {
        "level": game.level,
        "wave": game.wave,
        "base_hp": game.base_hp,
        "state": game.state,
        "break_timer": game.break_timer,
        "is_night": game.is_night,
        "enemies_left_to_spawn": game.enemies_left_to_spawn,
        "boss_spawned": getattr(game, "boss_spawned", False),
        "player": {
            "x": p.x,
            "y": p.y,
            "hp": p.hp,
            "max_hp": p.max_hp,
            "speed": p.speed,
            "damage": p.damage,
            "coins": p.coins,
            "keys": p.keys,
            "weapon": p.weapon,
            "ammo": p.ammo,
            "unlocked_weapons": sorted(p.unlocked_weapons),
            "lifesteal": p.lifesteal,
        },
        "turret_level": game.turret.level,
        "turret_damage": game.turret.damage,
        "turret_range": game.turret.range,
        "chests": [
            {"opened": c.opened, "tier": c.tier}
            for c in game.chests
        ],
    }
    with open(SAVE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_game(game):
    if not has_save():
        return False
    try:
        with open(SAVE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False

    game.reset_game()
    p = game.player
    pd = data["player"]

    game.level = data.get("level", 1)
    game.wave = data.get("wave", 0)
    game.base_hp = data.get("base_hp", game.base_hp)
    game.break_timer = data.get("break_timer", 0)
    game.is_night = data.get("is_night", False)
    game.enemies_left_to_spawn = data.get("enemies_left_to_spawn", 0)
    game.boss_spawned = data.get("boss_spawned", False)

    p.x = pd.get("x", p.x)
    p.y = pd.get("y", p.y)
    p.hp = pd.get("hp", p.hp)
    p.max_hp = pd.get("max_hp", p.max_hp)
    p.speed = pd.get("speed", p.speed)
    p.damage = pd.get("damage", p.damage)
    p.coins = pd.get("coins", 0)
    p.keys = pd.get("keys", 0)
    p.weapon = pd.get("weapon", "pistol")
    p.ammo = pd.get("ammo", 0)
    p.unlocked_weapons = set(pd.get("unlocked_weapons", ["pistol"]))
    p.lifesteal = pd.get("lifesteal", 0)

    game.turret.level = data.get("turret_level", 0)
    game.turret.damage = data.get("turret_damage", game.turret.damage)
    game.turret.range = data.get("turret_range", game.turret.range)

    chest_data = data.get("chests", [])
    for i, chest in enumerate(game.chests):
        if i < len(chest_data):
            chest.opened = chest_data[i].get("opened", False)
            chest.tier = chest_data[i].get("tier", game.level)

    saved_state = data.get("state", game.STATE_BREAK)
    if saved_state == game.STATE_PLAY and game.enemies_left_to_spawn <= 0 and not game.enemies:
        saved_state = game.STATE_BREAK
    game.state = saved_state
    game.message = "Игра загружена"
    game.message_timer = 2.0
    return True
