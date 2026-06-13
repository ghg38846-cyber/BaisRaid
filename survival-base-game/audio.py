"""Звуки без внешних файлов — генерируются кодом."""

import array
import math

import pygame


def _tone(freq, duration, volume=0.4, sample_rate=22050, fade_out=True):
    n = int(sample_rate * duration)
    buf = array.array("h")
    amp = int(32767 * max(0.0, min(1.0, volume)))
    for i in range(n):
        t = i / sample_rate
        env = 1.0
        if fade_out and n > 0:
            env = max(0.0, 1.0 - i / n)
        sample = int(amp * env * math.sin(2 * math.pi * freq * t))
        buf.append(sample)
        buf.append(sample)
    return pygame.mixer.Sound(buffer=buf)


def _noise_burst(duration, volume=0.25, sample_rate=22050):
    import random

    n = int(sample_rate * duration)
    buf = array.array("h")
    amp = int(32767 * volume)
    for i in range(n):
        env = max(0.0, 1.0 - i / max(1, n))
        sample = int(amp * env * random.uniform(-1, 1))
        buf.append(sample)
        buf.append(sample)
    return pygame.mixer.Sound(buffer=buf)


class SoundManager:
    def __init__(self):
        self.enabled = False
        self.sfx_volume = 0.7
        self._sounds = {}

    def init(self, sfx_volume=0.7):
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        self.enabled = True
        self.sfx_volume = sfx_volume
        self._build_sounds()
        self.apply_volume()

    def _build_sounds(self):
        self._sounds = {
            "shoot": _tone(880, 0.06, 0.25),
            "shotgun": _noise_burst(0.08, 0.35),
            "hit": _tone(220, 0.08, 0.3),
            "enemy_die": _tone(140, 0.12, 0.35),
            "player_hurt": _tone(90, 0.15, 0.4),
            "base_hit": _tone(60, 0.2, 0.45),
            "loot": _tone(660, 0.07, 0.25),
            "chest": _tone(520, 0.1, 0.3),
            "wave": _tone(440, 0.18, 0.35),
            "boss": _tone(55, 0.35, 0.5),
            "menu": _tone(330, 0.05, 0.2),
            "save": _tone(740, 0.09, 0.25),
            "perk": _tone(550, 0.14, 0.3),
        }

    def apply_volume(self):
        for sound in self._sounds.values():
            sound.set_volume(self.sfx_volume)

    def set_sfx_volume(self, value):
        self.sfx_volume = max(0.0, min(1.0, value))
        self.apply_volume()

    def play(self, name):
        if not self.enabled:
            return
        sound = self._sounds.get(name)
        if sound:
            sound.play()
