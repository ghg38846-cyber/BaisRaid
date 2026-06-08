"""Простые текстуры (рисуются кодом, без файлов картинок)."""

import pygame

from settings import *


def _surf(size, color=(0, 0, 0, 0)):
    return pygame.Surface(size, pygame.SRCALPHA).convert_alpha()


def _player():
    s = _surf((32, 32))
    pygame.draw.circle(s, (55, 110, 200), (16, 17), 11)
    pygame.draw.circle(s, (230, 200, 170), (16, 10), 6)
    pygame.draw.rect(s, (35, 35, 45), (20, 14, 10, 4))
    pygame.draw.circle(s, (255, 255, 255), (18, 9), 2)
    return s


def _enemy():
    s = _surf((24, 24))
    pygame.draw.rect(s, (180, 45, 55), (4, 6, 16, 16))
    pygame.draw.rect(s, (120, 25, 35), (6, 2, 12, 8))
    pygame.draw.line(s, (255, 80, 80), (8, 14), (16, 14), 2)
    return s


def _enemy_runner():
    s = _surf((20, 20))
    pygame.draw.ellipse(s, (255, 120, 50), (2, 6, 16, 12))
    pygame.draw.circle(s, (255, 200, 80), (10, 6), 4)
    return s


def _enemy_tank():
    s = _surf((30, 30))
    pygame.draw.rect(s, (90, 95, 110), (3, 8, 24, 18))
    pygame.draw.rect(s, (60, 65, 80), (8, 4, 14, 8))
    pygame.draw.rect(s, (50, 55, 70), (0, 12, 6, 10))
    pygame.draw.rect(s, (50, 55, 70), (24, 12, 6, 10))
    return s


def _turret():
    s = _surf((28, 28))
    pygame.draw.circle(s, (100, 100, 110), (14, 16), 10)
    pygame.draw.rect(s, (70, 130, 200), (12, 8, 12, 6))
    pygame.draw.circle(s, (180, 220, 255), (14, 12), 4)
    return s


def _bullet_turret():
    s = _surf((8, 8))
    pygame.draw.circle(s, (100, 200, 255), (4, 4), 3)
    return s


def _base():
    s = _surf((64, 64))
    pygame.draw.rect(s, (45, 130, 70), (8, 20, 48, 36))
    pygame.draw.polygon(s, (35, 100, 55), [(8, 20), (32, 4), (56, 20)])
    pygame.draw.rect(s, (25, 70, 40), (26, 36, 12, 20))
    pygame.draw.circle(s, (90, 200, 110), (32, 14), 5)
    return s


def _wall():
    s = _surf((48, 48))
    for y in range(0, 48, 12):
        for x in range(0, 48, 16):
            shade = 55 + (x + y) % 20
            pygame.draw.rect(s, (shade, shade, shade + 10), (x, y, 16, 12))
    pygame.draw.rect(s, (30, 30, 35), (0, 0, 48, 48), 2)
    return s


def _fence():
    s = _surf((48, 48))
    pygame.draw.rect(s, (62, 66, 74), (0, 0, 48, 48))
    pygame.draw.rect(s, (48, 52, 60), (0, 0, 48, 6))
    pygame.draw.rect(s, (48, 52, 60), (0, 42, 48, 6))
    for i in range(6, 42, 12):
        pygame.draw.line(s, (78, 82, 92), (i, 2), (i, 46), 2)
    pygame.draw.rect(s, (88, 92, 102), (0, 0, 48, 48), 2)
    return s


def _tree():
    s = _surf((36, 36))
    pygame.draw.circle(s, (40, 100, 50), (18, 14), 13)
    pygame.draw.circle(s, (55, 130, 65), (14, 10), 8)
    pygame.draw.circle(s, (55, 130, 65), (22, 11), 7)
    pygame.draw.rect(s, (70, 45, 28), (16, 24, 4, 10))
    return s


def _chest(closed=True):
    s = _surf((40, 32))
    if closed:
        pygame.draw.rect(s, (110, 70, 40), (4, 10, 32, 20))
        pygame.draw.rect(s, (140, 95, 55), (4, 4, 32, 12))
        pygame.draw.rect(s, (60, 40, 25), (18, 16, 6, 8))
        pygame.draw.circle(s, (240, 200, 60), (21, 19), 3)
    else:
        pygame.draw.rect(s, (70, 70, 75), (4, 14, 32, 16))
        pygame.draw.rect(s, (90, 90, 95), (4, 6, 32, 10))
    return s


def _loot(kind):
    s = _surf((22, 22))
    if kind == "coin":
        pygame.draw.circle(s, (240, 200, 50), (11, 11), 9)
        pygame.draw.circle(s, (180, 140, 30), (11, 11), 6)
    elif kind == "key":
        pygame.draw.circle(s, (80, 200, 220), (8, 10), 5)
        pygame.draw.rect(s, (80, 200, 220), (12, 9, 8, 4))
    elif kind == "medkit":
        pygame.draw.rect(s, (220, 60, 60), (4, 6, 14, 12))
        pygame.draw.rect(s, (240, 240, 240), (9, 8, 4, 10))
        pygame.draw.rect(s, (240, 240, 240), (6, 11, 10, 4))
    else:
        pygame.draw.rect(s, (120, 120, 130), (5, 8, 12, 10))
        pygame.draw.rect(s, (200, 200, 80), (8, 4, 6, 6))
    return s


def _bullet_player():
    s = _surf((8, 8))
    pygame.draw.circle(s, (255, 230, 80), (4, 4), 3)
    return s


def _ground_tile():
    s = _surf((64, 64))
    pygame.draw.rect(s, (48, 52, 60), (0, 0, 64, 64))
    for i in range(4):
        pygame.draw.line(s, (42, 46, 54), (i * 16, 0), (i * 16, 64))
        pygame.draw.line(s, (42, 46, 54), (0, i * 16), (64, i * 16))
    return s


WEAPON_ORDER = ["pistol", "rifle", "auto", "shotgun"]

WEAPON_NAMES = {
    "pistol": "пистолет",
    "rifle": "винтовка",
    "auto": "автомат",
    "shotgun": "дробовик",
}


def create_textures():
    return {
        "player": _player(),
        "enemy": _enemy(),
        "enemy_runner": _enemy_runner(),
        "enemy_tank": _enemy_tank(),
        "turret": _turret(),
        "bullet_turret": _bullet_turret(),
        "base": _base(),
        "wall": _wall(),
        "fence": _fence(),
        "tree": _tree(),
        "chest": _chest(True),
        "chest_open": _chest(False),
        "bullet": _bullet_player(),
        "ground": _ground_tile(),
        "loot_coin": _loot("coin"),
        "loot_key": _loot("key"),
        "loot_medkit": _loot("medkit"),
        "loot_ammo": _loot("ammo"),
    }
