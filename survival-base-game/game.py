import math
import random
import pygame

import settings as cfg
from settings import *
from objects import (
    Player,
    Enemy,
    Boss,
    Bullet,
    Loot,
    Chest,
    Turret,
    roll_enemy_drop,
    spawn_enemy,
    spawn_boss,
    spawn_bullet,
)
from textures import create_textures, WEAPON_NAMES
from perks import roll_perk_choices, apply_perk
from shop import buy, SHOP_ITEMS
from save_data import (
    load_config,
    save_config,
    save_game,
    load_game,
    has_save,
    delete_save,
)
from audio import SoundManager


# Разметка карты под BASE_WIDTH x BASE_HEIGHT (масштабируется на весь экран)
BUILDINGS_LAYOUT = [
    (95, 115, 125, 80),
    (335, 90, 105, 115),
    (615, 125, 140, 78),
    (715, 340, 110, 95),
    (465, 385, 120, 68),
    (165, 405, 105, 88),
    (295, 235, 88, 58),
]

# Забор по краям (узкий, серый)
FENCE_LAYOUT = [
    (0, 0, BASE_WIDTH, FENCE_THICKNESS),
    (0, BASE_HEIGHT - FENCE_THICKNESS, BASE_WIDTH, FENCE_THICKNESS),
    (0, 0, FENCE_THICKNESS, BASE_HEIGHT),
    (BASE_WIDTH - FENCE_THICKNESS, 0, FENCE_THICKNESS, BASE_HEIGHT),
]

# Деревья у границ (x, y, размер)
TREE_LAYOUT = [
    (55, 55, 30),
    (180, 45, 28),
    (820, 60, 32),
    (880, 200, 28),
    (70, 520, 30),
    (200, 560, 26),
    (750, 530, 32),
    (860, 450, 28),
    (45, 280, 26),
    (900, 320, 30),
]

CHEST_LAYOUT = [
    (195, 305),
    (535, 185),
    (720, 485),
    (415, 505),
    (255, 480),
]


class Game:
    STATE_MENU = "menu"
    STATE_SETTINGS = "settings"
    STATE_PLAY = "play"
    STATE_BREAK = "break"
    STATE_PERK = "perk"
    STATE_OVER = "over"
    STATE_WIN = "win"

    def __init__(self):
        pygame.init()
        self.config = load_config()
        self.fullscreen = self.config.get("fullscreen", FULLSCREEN)
        self._init_screen()
        pygame.display.set_caption("Base Raid - top-down prototype")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 20)
        self.font_big = pygame.font.SysFont("arial", 36, bold=True)
        self.textures = create_textures()
        self.audio = SoundManager()
        try:
            self.audio.init(self.config.get("sfx_volume", 0.7))
        except pygame.error:
            self.audio.enabled = False
        self.running = True
        self.state = self.STATE_MENU
        self.settings_cursor = 0
        self.boss_spawned = False
        self.reset_game()

    def _init_screen(self):
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((BASE_WIDTH, BASE_HEIGHT))
        self.width, self.height = self.screen.get_size()
        cfg.WIDTH = self.width
        cfg.HEIGHT = self.height

    def _toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self.config["fullscreen"] = self.fullscreen
        save_config(self.config)
        self._init_screen()
        self._build_map()

    def _apply_config(self):
        save_config(self.config)
        self.audio.set_sfx_volume(self.config.get("sfx_volume", 0.7))
        if self.config.get("fullscreen") != self.fullscreen:
            self.fullscreen = self.config["fullscreen"]
            self._init_screen()
            self._build_map()

    def _build_map(self):
        sx = self.width / BASE_WIDTH
        sy = self.height / BASE_HEIGHT

        def rect_xywh(x, y, w, h):
            return pygame.Rect(int(x * sx), int(y * sy), int(w * sx), int(h * sy))

        self.building_walls = [rect_xywh(x, y, w, h) for x, y, w, h in BUILDINGS_LAYOUT]
        self.fence_walls = [rect_xywh(x, y, w, h) for x, y, w, h in FENCE_LAYOUT]
        self.tree_walls = [
            rect_xywh(x, y, s, s) for x, y, s in TREE_LAYOUT
        ]
        self.walls = self.building_walls + self.fence_walls + self.tree_walls
        self.player_walls = self.building_walls + self.tree_walls
        ft = FENCE_THICKNESS
        self.play_bounds = pygame.Rect(
            int(ft * sx),
            int(ft * sy),
            int((BASE_WIDTH - ft * 2) * sx),
            int((BASE_HEIGHT - ft * 2) * sy),
        )

        self.chests = [
            Chest(int(x * sx), int(y * sy), tier=1) for x, y in CHEST_LAYOUT
        ]
        base_size = int(BASE_SIZE * min(sx, sy))
        self.base = pygame.Rect(
            self.width // 2 - base_size // 2,
            self.height // 2 - base_size // 2,
            base_size,
            base_size,
        )
        spawn_x = self.base.centerx
        spawn_y = self.base.centery + base_size // 2 + int(28 * min(sx, sy))
        self.player = Player(spawn_x, spawn_y)
        half = self.player.size / 2
        self.player.x = max(
            self.play_bounds.left + half,
            min(self.play_bounds.right - half, self.player.x),
        )
        self.player.y = max(
            self.play_bounds.top + half,
            min(self.play_bounds.bottom - half, self.player.y),
        )
        self.turret = Turret(self.base.centerx, self.base.centery)

        self._cache_draw_surfaces()

    def reset_game(self):
        self._build_map()
        self.base_hp = BASE_HP
        self.is_night = False
        self.enemies = []
        self.bullets = []
        self.loots = []
        self.level = 1
        self.wave = 0
        self.enemies_left_to_spawn = 0
        self.break_timer = 0
        self.message = ""
        self.message_timer = 0
        self.perk_options = []
        self.boss_spawned = False

    def _is_boss_wave(self):
        return self.level == BOSS_LEVEL and self.wave == BOSS_WAVE

    def _try_autosave(self):
        if AUTOSAVE_ON_BREAK and self.state in (self.STATE_BREAK, self.STATE_PERK):
            save_game(self)

    def _cache_draw_surfaces(self):
        ground = self.textures["ground"]
        self.bg_surface = pygame.Surface((self.width, self.height))
        for ty in range(0, self.height, 64):
            for tx in range(0, self.width, 64):
                self.bg_surface.blit(ground, (tx, ty))

        self.base_sprite = pygame.transform.smoothscale(
            self.textures["base"], (self.base.w, self.base.h)
        )

        self.fence_sprites = self._wall_sprites(self.fence_walls, "fence")
        self.building_sprites = self._wall_sprites(self.building_walls, "wall")
        self.tree_sprites = self._wall_sprites(self.tree_walls, "tree")

    def _wall_sprites(self, walls, texture_key):
        tex = self.textures[texture_key]
        return [
            pygame.transform.smoothscale(tex, (max(1, w.w), max(1, w.h)))
            for w in walls
        ]

    def refresh_chests(self):
        for chest in self.chests:
            chest.reset(self.level)
        self.show_msg(f"Сундуки обновлены! Tier {self.level}")

    def _enemies_in_wave(self):
        if self.wave < 1:
            return FIRST_WAVE_ENEMIES
        return (
            FIRST_WAVE_ENEMIES
            + (self.wave - 1) * WAVE_ENEMY_ADD
            + (self.level - 1) * LEVEL_EXTRA_ENEMIES
        )

    def _spawn_all_enemies_for_wave(self):
        if self._is_boss_wave() and not self.boss_spawned:
            self.enemies.append(spawn_boss(self.wave, self.level, self.play_bounds))
            self.boss_spawned = True
            for _ in range(BOSS_MINIONS):
                self.enemies.append(
                    spawn_enemy(self.wave, self.level, self.play_bounds, force_type="swarm")
                )
            self.enemies_left_to_spawn = 0
            return
        while self.enemies_left_to_spawn > 0:
            self.enemies.append(
                spawn_enemy(self.wave, self.level, self.play_bounds)
            )
            self.enemies_left_to_spawn -= 1

    def start_wave(self):
        self.wave += 1
        self.enemies_left_to_spawn = max(1, self._enemies_in_wave())
        if self._is_boss_wave():
            self.enemies_left_to_spawn = 0
            self.boss_spawned = False
        self.enemies.clear()
        self.is_night = self.wave in NIGHT_WAVES
        night_txt = " | НОЧЬ — враги видят дальше!" if self.is_night else ""
        if self._is_boss_wave():
            self.message = f"БОСС! Уровень {self.level} — финальная волна{night_txt}"
            self.audio.play("boss")
        else:
            self.message = f"Уровень {self.level} — волна {self.wave}/{WAVES_PER_LEVEL}{night_txt}"
            self.audio.play("wave")
        self.message_timer = 2.5
        self.state = self.STATE_PLAY
        self.player.shoot_cooldown = 0
        self._spawn_all_enemies_for_wave()

    def start_break(self):
        self.state = self.STATE_BREAK
        self.is_night = False
        self.break_timer = WAVE_BREAK_TIME
        self.message = "Магазин 4-7 | Прокачка 1-3 | E-сундуки"
        self.message_timer = 3.0
        self.base_hp = min(BASE_HP, self.base_hp + 30)
        self._try_autosave()

    def start_perk_choice(self):
        self.state = self.STATE_PERK
        self.perk_options = roll_perk_choices(3)
        self.message = "Уровень пройден! Выбери перк: 1 / 2 / 3"
        self.message_timer = 5.0

    def pick_perk(self, index):
        if index < 0 or index >= len(self.perk_options):
            return
        perk = self.perk_options[index]
        apply_perk(self, perk["id"])
        self.show_msg(f"Перк: {perk['name']}")
        self.audio.play("perk")
        self.start_next_level()

    def start_next_level(self):
        self.level += 1
        self.wave = 0
        self.refresh_chests()
        self.loots.clear()
        self.state = self.STATE_BREAK
        self.break_timer = LEVEL_BREAK_TIME
        self.message = f"Уровень {self.level}! Сундуки tier {self.level}, враги сильнее"
        self.message_timer = 4.0
        self.base_hp = min(BASE_HP + (self.level - 1) * 25, self.base_hp + 50)
        self.player.heal(30)

    def spawn_tick(self):
        if self.enemies_left_to_spawn > 0:
            self._spawn_all_enemies_for_wave()

    def try_shop(self, key_num):
        mapping = {4: "medkit", 5: "key", 6: "base", 7: "turret"}
        item_id = mapping.get(key_num)
        if not item_id:
            return
        msg = buy(self, item_id)
        if msg:
            self.show_msg(msg)

    def _on_enemy_killed(self, enemy):
        enemy.alive = False
        self.audio.play("enemy_die")
        if self.player.lifesteal > 0:
            self.player.heal(self.player.lifesteal)
        drop = roll_enemy_drop()
        if drop:
            self.loots.append(Loot(enemy.x, enemy.y, drop))
        if random.randint(1, 100) <= EXTRA_AMMO_DROP:
            self.loots.append(Loot(enemy.x + 8, enemy.y, "ammo"))

    def try_upgrade(self, choice):
        p = self.player
        if choice == 1 and p.coins >= UPGRADE_HP_COST:
            p.coins -= UPGRADE_HP_COST
            p.max_hp += UPGRADE_HP_BONUS
            p.hp += UPGRADE_HP_BONUS
            self.show_msg("+ HP")
        elif choice == 2 and p.coins >= UPGRADE_SPEED_COST:
            p.coins -= UPGRADE_SPEED_COST
            p.speed += UPGRADE_SPEED_BONUS
            self.show_msg("+ скорость")
        elif choice == 3 and p.coins >= UPGRADE_DAMAGE_COST:
            p.coins -= UPGRADE_DAMAGE_COST
            p.damage += UPGRADE_DAMAGE_BONUS
            self.show_msg("+ урон")

    def show_msg(self, text):
        self.message = text
        self.message_timer = 1.5

    def handle_chest_loot(self, result, chest=None):
        p = self.player
        tier = chest.tier if chest else 1
        if result == "medkit":
            p.heal(35 + tier * 5)
            self.show_msg("Аптечка из сундука")
        elif result == "ammo_pack":
            amount = AMMO_CHEST + tier * 15
            p.ammo += amount
            self.show_msg(f"+{amount} патронов")
        elif result == "coins":
            amount = 25 + tier * 10
            p.coins += amount
            self.show_msg(f"+{amount} монет")
        elif result == "weapon":
            locked = [w for w in CHEST_WEAPONS if w not in p.unlocked_weapons]
            bonus = AMMO_WEAPON_BONUS + tier * 10
            if locked:
                w = random.choice(locked)
                p.unlock_weapon(w)
                p.weapon = w
                p.ammo += bonus
                name = WEAPON_NAMES.get(w, w)
                self.show_msg(f"{name} +{bonus} патронов")
            else:
                p.ammo += bonus
                self.show_msg(f"Патроны +{bonus}")

    def collect_loot(self, loot):
        p = self.player
        if loot.kind == "coin":
            p.coins += random.randint(5, 15)
        elif loot.kind == "key":
            p.keys += 1
        elif loot.kind == "medkit":
            p.heal(35)
        elif loot.kind == "ammo":
            p.ammo += AMMO_PICKUP
        loot.alive = False
        self.audio.play("loot")

    def switch_weapon(self):
        p = self.player
        if p.weapon_switch_cd > 0:
            return
        p.switch_weapon()
        p.weapon_switch_cd = 0.2
        name = WEAPON_NAMES.get(p.weapon, p.weapon)
        self.show_msg(f"Оружие: {name}")

    def player_shoot(self):
        dmg = self.player.shoot()
        if dmg is None:
            return
        if self.player.weapon == "shotgun":
            self.audio.play("shotgun")
        else:
            self.audio.play("shoot")
        angle = self.player.angle
        if self.player.weapon == "shotgun":
            for spread in (-0.2, 0, 0.2):
                self.bullets.append(
                    spawn_bullet(
                        self.player.x,
                        self.player.y,
                        angle + spread,
                        dmg,
                        source_size=self.player.size,
                    )
                )
        else:
            self.bullets.append(
                spawn_bullet(
                    self.player.x,
                    self.player.y,
                    angle,
                    dmg,
                    source_size=self.player.size,
                )
            )

    def update_play(self, dt):
        keys = pygame.key.get_pressed()
        dx = keys[pygame.K_d] - keys[pygame.K_a]
        dy = keys[pygame.K_s] - keys[pygame.K_w]
        self.player.move(dx, dy, dt, self.player_walls, self.play_bounds)
        self.player.update(dt)

        mouse_x, mouse_y = pygame.mouse.get_pos()
        self.player.angle = math.atan2(mouse_y - self.player.y, mouse_x - self.player.x)

        if pygame.mouse.get_pressed()[0]:
            self.player_shoot()

        self.spawn_tick()
        self.turret.x = self.base.centerx
        self.turret.y = self.base.centery
        self.turret.update(dt, self.enemies, self.bullets)

        for enemy in self.enemies:
            base_damage = enemy.update(
                dt, self.player, self.base, self.walls, self.is_night, self.bullets
            )
            if base_damage:
                self.base_hp -= base_damage
                self.audio.play("base_hit")

        for bullet in self.bullets[:]:
            bullet.update(dt, self.building_walls, self.fence_walls, self.tree_walls)
            if not bullet.alive:
                self.bullets.remove(bullet)
                continue
            if bullet.owner in ("player", "turret"):
                for enemy in self.enemies:
                    if enemy.alive and enemy.rect.collidepoint(bullet.x, bullet.y):
                        enemy.hp -= bullet.damage
                        bullet.alive = False
                        self.audio.play("hit")
                        if enemy.hp <= 0:
                            self._on_enemy_killed(enemy)
                        break
            elif bullet.owner == "enemy":
                if self.player.rect.collidepoint(bullet.x, bullet.y):
                    self.player.hp -= bullet.damage
                    bullet.alive = False
                    self.audio.play("player_hurt")
                elif self.base.collidepoint(bullet.x, bullet.y):
                    self.base_hp -= bullet.damage
                    bullet.alive = False
                    self.audio.play("base_hit")

        self.enemies = [e for e in self.enemies if e.alive]

        for loot in self.loots:
            if not loot.alive:
                continue
            dist = math.hypot(loot.x - self.player.x, loot.y - self.player.y)
            if dist < 28:
                self.collect_loot(loot)
        self.loots = [l for l in self.loots if l.alive]

        if self.player.hp <= 0 or self.base_hp <= 0:
            self.state = self.STATE_OVER
            delete_save()

        alive_enemies = len(self.enemies) + self.enemies_left_to_spawn
        if alive_enemies == 0 and self.state == self.STATE_PLAY:
            if self.wave >= WAVES_PER_LEVEL:
                if self.level >= MAX_LEVEL:
                    self.state = self.STATE_WIN
                    delete_save()
                else:
                    self.start_perk_choice()
            else:
                self.start_break()

    def update_perk(self, dt):
        keys = pygame.key.get_pressed()
        dx = keys[pygame.K_d] - keys[pygame.K_a]
        dy = keys[pygame.K_s] - keys[pygame.K_w]
        self.player.move(dx, dy, dt, self.player_walls, self.play_bounds)

    def update_break(self, dt):
        keys = pygame.key.get_pressed()
        dx = keys[pygame.K_d] - keys[pygame.K_a]
        dy = keys[pygame.K_s] - keys[pygame.K_w]
        self.player.move(dx, dy, dt, self.player_walls, self.play_bounds)
        self.break_timer -= dt

        for loot in self.loots:
            dist = math.hypot(loot.x - self.player.x, loot.y - self.player.y)
            if dist < 28:
                self.collect_loot(loot)
        self.loots = [l for l in self.loots if l.alive]

        if self.break_timer <= 0:
            self.enemies.clear()
            self.enemies_left_to_spawn = 0
            self.start_wave()

    def update(self, dt):
        if self.message_timer > 0:
            self.message_timer -= dt

        if self.state == self.STATE_PLAY:
            self.update_play(dt)
        elif self.state == self.STATE_BREAK:
            self.update_break(dt)
        elif self.state == self.STATE_PERK:
            self.update_perk(dt)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state == self.STATE_SETTINGS:
                        save_config(self.config)
                        self.state = self.STATE_MENU
                        self.audio.play("menu")
                    elif self.state == self.STATE_MENU:
                        self.running = False
                    else:
                        self.state = self.STATE_MENU
                        self.audio.play("menu")
                if event.key == pygame.K_F11:
                    self._toggle_fullscreen()
                if event.key == pygame.K_F5:
                    if self.state not in (self.STATE_MENU, self.STATE_SETTINGS, self.STATE_OVER, self.STATE_WIN):
                        save_game(self)
                        self.show_msg("Сохранено (F5)")
                        self.audio.play("save")

                if self.state == self.STATE_MENU:
                    if event.key == pygame.K_RETURN:
                        self.reset_game()
                        self.start_wave()
                        self.audio.play("menu")
                    if event.key == pygame.K_c and has_save():
                        if load_game(self):
                            self.audio.play("save")
                    if event.key == pygame.K_o:
                        self.state = self.STATE_SETTINGS
                        self.settings_cursor = 0
                        self.audio.play("menu")

                if self.state == self.STATE_SETTINGS:
                    if event.key in (pygame.K_UP, pygame.K_w):
                        self.settings_cursor = (self.settings_cursor - 1) % 3
                        self.audio.play("menu")
                    if event.key in (pygame.K_DOWN, pygame.K_s):
                        self.settings_cursor = (self.settings_cursor + 1) % 3
                        self.audio.play("menu")
                    if event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
                        delta = -0.1 if event.key in (pygame.K_LEFT, pygame.K_a) else 0.1
                        if self.settings_cursor == 0:
                            self.config["sfx_volume"] = max(
                                0.0, min(1.0, self.config.get("sfx_volume", 0.7) + delta)
                            )
                            self.audio.set_sfx_volume(self.config["sfx_volume"])
                        elif self.settings_cursor == 1:
                            self.config["music_volume"] = max(
                                0.0, min(1.0, self.config.get("music_volume", 0.5) + delta)
                            )
                        elif self.settings_cursor == 2:
                            self.config["fullscreen"] = not self.config.get("fullscreen", True)
                            self._apply_config()
                        self.audio.play("menu")
                    if event.key == pygame.K_RETURN:
                        self._apply_config()
                        self.state = self.STATE_MENU
                        self.audio.play("menu")

                if self.state == self.STATE_OVER and event.key == pygame.K_RETURN:
                    self.state = self.STATE_MENU
                if self.state == self.STATE_WIN and event.key == pygame.K_RETURN:
                    self.state = self.STATE_MENU
                if self.state == self.STATE_PERK:
                    if event.key == pygame.K_1:
                        self.pick_perk(0)
                    if event.key == pygame.K_2:
                        self.pick_perk(1)
                    if event.key == pygame.K_3:
                        self.pick_perk(2)
                if self.state in (self.STATE_PLAY, self.STATE_BREAK):
                    if event.key == pygame.K_e:
                        for chest in self.chests:
                            result = chest.try_open(self.player)
                            if result in ("too_far", "no_key"):
                                if result == "no_key":
                                    self.show_msg("Нужен ключ (K с врага)")
                                continue
                            if result:
                                self.handle_chest_loot(result, chest)
                                self.audio.play("chest")
                                break
                    if self.state == self.STATE_BREAK:
                        if event.key == pygame.K_1:
                            self.try_upgrade(1)
                        if event.key == pygame.K_2:
                            self.try_upgrade(2)
                        if event.key == pygame.K_3:
                            self.try_upgrade(3)
                        if event.key == pygame.K_4:
                            self.try_shop(4)
                        if event.key == pygame.K_5:
                            self.try_shop(5)
                        if event.key == pygame.K_6:
                            self.try_shop(6)
                        if event.key == pygame.K_7:
                            self.try_shop(7)
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.state in (self.STATE_PLAY, self.STATE_BREAK, self.STATE_PERK) and event.button == 3:
                    self.switch_weapon()

    def draw_map(self):
        self.screen.blit(self.bg_surface, (0, 0))
        self.screen.blit(self.base_sprite, self.base)
        self.turret.draw(self.screen, self.textures)
        for wall, sprite in zip(self.fence_walls, self.fence_sprites):
            self.screen.blit(sprite, wall)
        for wall, sprite in zip(self.building_walls, self.building_sprites):
            self.screen.blit(sprite, wall)
        for wall, sprite in zip(self.tree_walls, self.tree_sprites):
            self.screen.blit(sprite, wall)
        for chest in self.chests:
            chest.draw(self.screen, self.textures)

    def draw_hud(self):
        p = self.player
        weapon_name = WEAPON_NAMES.get(p.weapon, p.weapon)
        lines = [
            f"HP: {int(p.hp)}/{p.max_hp}",
            f"База: {int(self.base_hp)}/{BASE_HP}",
            f"Уровень: {self.level}/{MAX_LEVEL}  Волна: {self.wave}/{WAVES_PER_LEVEL}",
            f"Монеты: {p.coins}  Ключи: {p.keys}",
            f"Оружие: {weapon_name}  Патроны: {p.ammo}",
        ]
        if self.is_night and self.state == self.STATE_PLAY:
            lines.append("НОЧНАЯ ВОЛНА — затемнение, враги агрессивнее")
        if self.turret.level > 0:
            lines.append(f"Турель: ур.{self.turret.level}")
        if any(isinstance(e, Boss) for e in self.enemies):
            lines.append("БОСС на карте!")
        if self.state == self.STATE_BREAK:
            lines.append(f"Перерыв: {int(self.break_timer)} сек")
            lines.append("[1]HP [2]скор [3]урон | [4]аптечка [5]ключ [6]база [7]турель")
            for item in SHOP_ITEMS:
                lines.append(f"  [{item['key']}] {item['name']} — {item['cost']} монет")
        if self.state == self.STATE_PERK:
            lines.append("Выбери перк на новый уровень!")
        if self.player.lifesteal > 0:
            lines.append(f"Вампиризм: +{int(self.player.lifesteal)} HP за kill")
        y = 8
        for line in lines:
            self.screen.blit(self.font.render(line, True, WHITE), (10, y))
            y += 22

        # полоски HP
        pygame.draw.rect(self.screen, RED, (10, self.height - 30, 200, 16))
        hp_w = 200 * max(0, p.hp / p.max_hp)
        pygame.draw.rect(self.screen, GREEN, (10, self.height - 30, hp_w, 16))
        pygame.draw.rect(self.screen, RED, (220, self.height - 30, 200, 16))
        base_w = 200 * max(0, self.base_hp / BASE_HP)
        pygame.draw.rect(self.screen, BLUE, (220, self.height - 30, base_w, 16))

        if self.message_timer > 0:
            self.screen.blit(
                self.font.render(self.message, True, YELLOW),
                (self.width // 2 - 180, 50),
            )

    def draw_entities(self):
        tex = self.textures
        for loot in self.loots:
            loot.draw(self.screen, tex)
        for enemy in self.enemies:
            enemy.draw(self.screen, tex)
        for bullet in self.bullets:
            bullet.draw(self.screen, tex)
        self.player.draw(self.screen, tex)

    def draw_perk_menu(self):
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        self.screen.blit(overlay, (0, 0))
        title = self.font_big.render("Новый уровень — выбери перк", True, YELLOW)
        self.screen.blit(title, (self.width // 2 - title.get_width() // 2, 120))
        y = 200
        for i, perk in enumerate(self.perk_options):
            line = f"[{i + 1}] {perk['name']}: {perk['desc']}"
            self.screen.blit(self.font.render(line, True, WHITE), (self.width // 2 - 260, y))
            y += 36
        sub = self.font.render("После выбора сундуки обновятся (tier выше)", True, CYAN)
        self.screen.blit(sub, (self.width // 2 - sub.get_width() // 2, y + 20))

    def draw_settings(self):
        self.screen.fill(BLACK)
        title = self.font_big.render("Настройки", True, YELLOW)
        self.screen.blit(title, (self.width // 2 - title.get_width() // 2, 120))

        sfx = int(self.config.get("sfx_volume", 0.7) * 100)
        music = int(self.config.get("music_volume", 0.5) * 100)
        fs = "Да" if self.config.get("fullscreen", True) else "Нет"
        options = [
            f"Громкость звуков: {sfx}%",
            f"Громкость музыки: {music}%",
            f"Полный экран: {fs}",
        ]
        y = 220
        for i, line in enumerate(options):
            color = YELLOW if i == self.settings_cursor else WHITE
            prefix = "> " if i == self.settings_cursor else "  "
            self.screen.blit(self.font.render(prefix + line, True, color), (self.width // 2 - 200, y))
            y += 40

        tips = [
            "W/S — выбор строки",
            "A/D — изменить значение",
            "Enter — сохранить и назад",
            "Esc — назад без сохранения",
        ]
        y += 30
        for tip in tips:
            self.screen.blit(self.font.render(tip, True, GRAY), (self.width // 2 - 180, y))
            y += 28

    def draw_menu(self):
        self.screen.fill(BLACK)
        title = self.font_big.render("Base Raid", True, RED)
        self.screen.blit(title, (self.width // 2 - title.get_width() // 2, 180))
        tips = [
            "4 волны = уровень. Босс на 4 уровне, волна 4",
            "Новые враги: стрелок (фиол.), рой (зелёный)",
            "Старт: пистолет. Остальное оружие — в сундуках",
            "WASD - бег, ЛКМ - стрельба, ПКМ - оружие",
            "E - сундук (нужен ключ с врага)",
            "F5 - сохранить | C - продолжить (если есть save)",
            "O - настройки звука и экрана",
            "F11 - окно / полный экран",
            "",
            "Enter - новая игра",
        ]
        if has_save():
            tips.insert(-1, "C - продолжить сохранённую игру")
        y = 260
        for t in tips:
            self.screen.blit(self.font.render(t, True, WHITE), (self.width // 2 - 200, y))
            y += 28

    def draw_overlay(self, text, color):
        self.screen.fill(BLACK)
        t = self.font_big.render(text, True, color)
        self.screen.blit(t, (self.width // 2 - t.get_width() // 2, self.height // 2 - 40))
        sub = self.font.render("Enter - в меню", True, WHITE)
        self.screen.blit(sub, (self.width // 2 - sub.get_width() // 2, self.height // 2 + 20))

    def draw(self):
        if self.state == self.STATE_MENU:
            self.draw_menu()
        elif self.state == self.STATE_SETTINGS:
            self.draw_settings()
        elif self.state in (self.STATE_OVER, self.STATE_WIN):
            self.draw_map()
            self.draw_entities()
            self.draw_hud()
            text = "ПОБЕДА!" if self.state == self.STATE_WIN else "ПОРАЖЕНИЕ"
            color = GREEN if self.state == self.STATE_WIN else RED
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            self.screen.blit(overlay, (0, 0))
            t = self.font_big.render(text, True, color)
            self.screen.blit(t, (self.width // 2 - t.get_width() // 2, self.height // 2))
        else:
            self.draw_map()
            self.draw_entities()
            if self.is_night and self.state == self.STATE_PLAY:
                dark = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
                dark.fill((5, 8, 25, NIGHT_DARKNESS))
                self.screen.blit(dark, (0, 0))
            self.draw_hud()
            if self.state == self.STATE_PERK:
                self.draw_perk_menu()
            hint = self.font.render("E-сундук | F5-сохранить | ЛКМ-стрельба | ПКМ-оружие", True, GRAY)
            self.screen.blit(hint, (self.width - 280, self.height - 28))

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()
            pygame.display.flip()
        pygame.quit()
