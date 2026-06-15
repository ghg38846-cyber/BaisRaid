import math
import random
import pygame

from settings import *


def push_out_of_walls(x, y, size, walls):
    
    half = size / 2
    for _ in range(8):
        rect = pygame.Rect(int(x - half), int(y - half), size, size)
        resolved = False

        for wall in walls:
            if not rect.colliderect(wall):
                continue

            overlap_left = rect.right - wall.left
            overlap_right = wall.right - rect.left
            overlap_top = rect.bottom - wall.top
            overlap_bottom = wall.bottom - rect.top

            if overlap_left <= 0 or overlap_right <= 0 or overlap_top <= 0 or overlap_bottom <= 0:
                continue

            min_overlap = min(overlap_left, overlap_right, overlap_top, overlap_bottom)

            if min_overlap == overlap_left:
                x -= overlap_left
            elif min_overlap == overlap_right:
                x += overlap_right
            elif min_overlap == overlap_top:
                y -= overlap_top
            else:
                y += overlap_bottom

            rect = pygame.Rect(int(x - half), int(y - half), size, size)
            resolved = True
            break

        if not resolved:
            break
    return x, y


def _bullet_hits_tree(x, y, tree_rect):
    cx, cy = tree_rect.centerx, tree_rect.centery
    radius = min(tree_rect.w, tree_rect.h) * TREE_BULLET_RADIUS_FRAC
    return math.hypot(x - cx, y - cy) <= radius


def bullet_blocked(x, y, building_walls, fence_walls, tree_walls):
    for wall in building_walls:
        if wall.collidepoint(x, y):
            return True
    for wall in fence_walls:
        if wall.collidepoint(x, y):
            return True
    for tree in tree_walls:
        if _bullet_hits_tree(x, y, tree):
            return True
    return False


def spawn_bullet(x, y, angle, damage, owner="player", source_size=0):
    offset = max(10, source_size * 0.5 + 6)
    bx = x + math.cos(angle) * offset
    by = y + math.sin(angle) * offset
    return Bullet(bx, by, angle, damage, owner)


class Bullet:
    def __init__(self, x, y, angle, damage, owner="player"):
        self.x = x
        self.y = y
        self.angle = angle
        self.damage = damage
        self.owner = owner
        self.speed = BULLET_SPEED
        self.alive = True
        self.radius = 4

    def update(self, dt, building_walls, fence_walls, tree_walls):
        self.x += math.cos(self.angle) * self.speed * dt
        self.y += math.sin(self.angle) * self.speed * dt
        if bullet_blocked(self.x, self.y, building_walls, fence_walls, tree_walls):
            self.alive = False
            return
        if self.x < 0 or self.y < 0 or self.x > WIDTH or self.y > HEIGHT:
            self.alive = False

    def draw(self, screen, textures=None):
        if textures:
            if self.owner == "turret":
                key = "bullet_turret"
            elif self.owner == "enemy":
                key = "bullet_enemy"
            else:
                key = "bullet"
            img = textures.get(key, textures["bullet"])
            screen.blit(img, (int(self.x) - 4, int(self.y) - 4))
        else:
            color = CYAN if self.owner == "turret" else YELLOW
            if self.owner == "enemy":
                color = RED
            pygame.draw.circle(screen, color, (int(self.x), int(self.y)), self.radius)


class Loot:
    """Предмет на земле после убийства врага."""
    TYPES = ("coin", "key", "medkit", "ammo")

    def __init__(self, x, y, kind):
        self.x = x
        self.y = y
        self.kind = kind
        self.alive = True
        self.radius = 10

    def draw(self, screen, textures=None):
        if textures:
            key = f"loot_{self.kind}"
            img = textures.get(key)
            if img:
                screen.blit(img, (int(self.x) - 11, int(self.y) - 11))
                return
        colors = {"coin": YELLOW, "key": CYAN, "medkit": GREEN, "ammo": GRAY}
        pygame.draw.circle(screen, colors[self.kind], (int(self.x), int(self.y)), self.radius)


class Chest:
    TIER_COLORS = [(140, 90, 50), (170, 170, 185), (240, 200, 70), (170, 90, 220)]
    TIER_NAMES = ["I", "II", "III", "IV"]

    def __init__(self, x, y, tier=1):
        self.rect = pygame.Rect(x, y, 36, 28)
        self.opened = False
        self.tier = tier

    def reset(self, tier):
        """Закрыть сундук и поднять tier под новый уровень."""
        self.opened = False
        self.tier = min(tier, 4)

    def _roll_loot(self):
        t = self.tier
        roll = random.randint(1, 100)
        if roll <= max(8, 14 - t):
            return "medkit"
        if roll <= 35 + t * 8:
            return "ammo_pack"
        if roll <= 48 + t * 5:
            return "coins"
        return "weapon"

    def try_open(self, player):
        if self.opened:
            return None
        dist = math.hypot(player.x - self.rect.centerx, player.y - self.rect.centery)
        if dist > 50:
            return "too_far"
        if player.keys < 1:
            return "no_key"
        player.keys -= 1
        self.opened = True
        return self._roll_loot()

    def draw(self, screen, textures=None):
        if textures:
            key = "chest" if not self.opened else "chest_open"
            img = textures[key]
            scaled = pygame.transform.smoothscale(img, (self.rect.w, self.rect.h))
            screen.blit(scaled, self.rect)
            if not self.opened:
                tint = self.TIER_COLORS[min(self.tier - 1, 3)]
                glow = pygame.Surface(scaled.get_size(), pygame.SRCALPHA)
                glow.fill((*tint, 90))
                screen.blit(glow, self.rect)
                font = pygame.font.SysFont("arial", 14, bold=True)
                label = self.TIER_NAMES[min(self.tier - 1, 3)]
                screen.blit(font.render(label, True, WHITE), (self.rect.x + 12, self.rect.y - 2))
            return
        color = BROWN if not self.opened else DARK_GRAY
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, BLACK, self.rect, 2)


class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.size = PLAYER_SIZE
        self.hp = PLAYER_HP
        self.max_hp = PLAYER_HP
        self.speed = PLAYER_SPEED
        self.damage = PLAYER_DAMAGE
        self.coins = 0
        self.keys = 0
        self.weapon = "pistol"
        self.ammo = START_AMMO
        self.shoot_cooldown = 0
        self.angle = 0
        self.unlocked_weapons = {"pistol"}
        self.weapon_switch_cd = 0
        self.lifesteal = 0

    def unlock_weapon(self, name):
        self.unlocked_weapons.add(name)

    def switch_weapon(self):
        from textures import WEAPON_ORDER

        order = [w for w in WEAPON_ORDER if w in self.unlocked_weapons]
        if len(order) <= 1:
            return
        idx = order.index(self.weapon)
        self.weapon = order[(idx + 1) % len(order)]

    @property
    def rect(self):
        return pygame.Rect(int(self.x - self.size / 2), int(self.y - self.size / 2), self.size, self.size)

    def move(self, dx, dy, dt, walls, play_bounds=None):
        if dx == 0 and dy == 0:
            return
        length = math.hypot(dx, dy)
        dx /= length
        dy /= length
        self.x += dx * self.speed * dt
        self.y += dy * self.speed * dt
        self.x, self.y = push_out_of_walls(self.x, self.y, self.size, walls)
        if play_bounds is not None:
            half = self.size / 2
            self.x = max(
                play_bounds.left + half,
                min(play_bounds.right - half, self.x),
            )
            self.y = max(
                play_bounds.top + half,
                min(play_bounds.bottom - half, self.y),
            )

    def can_shoot(self):
        if self.shoot_cooldown > 0:
            return False
        if self.weapon == "pistol":
            return True
        return self.ammo > 0

    def shoot(self):
        if self.shoot_cooldown > 0:
            return None
        if self.weapon != "pistol" and self.ammo <= 0:
            self.weapon = "pistol"
        if self.weapon == "pistol":
            self.shoot_cooldown = 0.36
            dmg = self.damage
        elif self.weapon == "rifle":
            self.ammo -= 1
            self.shoot_cooldown = 0.12
            dmg = self.damage + 10
        elif self.weapon == "auto":
            self.ammo -= 1
            self.shoot_cooldown = 0.08
            dmg = self.damage + 6
        else:  # shotgun
            self.ammo -= 1
            self.shoot_cooldown = 0.5
            dmg = self.damage + 18
        return dmg

    def update(self, dt):
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= dt
        if self.weapon_switch_cd > 0:
            self.weapon_switch_cd -= dt

    def heal(self, amount):
        self.hp = min(self.max_hp, self.hp + amount)

    def draw(self, screen, textures=None):
        if textures:
            img = pygame.transform.rotate(textures["player"], -math.degrees(self.angle))
            rect = img.get_rect(center=(int(self.x), int(self.y)))
            screen.blit(img, rect)
        else:
            pygame.draw.circle(screen, BLUE, (int(self.x), int(self.y)), self.size // 2)
            ex = self.x + math.cos(self.angle) * 18
            ey = self.y + math.sin(self.angle) * 18
            pygame.draw.line(screen, WHITE, (self.x, self.y), (ex, ey), 3)


class Turret:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.level = 0
        self.cooldown = 0
        self.damage = TURRET_DAMAGE
        self.range = TURRET_RANGE
        self.angle = 0.0

    def activate(self):
        self.level = 1

    def upgrade(self):
        self.level += 1
        self.damage += 6
        self.range += 35
        return self.level

    def update(self, dt, enemies, bullets):
        if self.level <= 0:
            return
        self.cooldown -= dt
        if self.cooldown > 0:
            return
        nearest = None
        best_dist = self.range
        for enemy in enemies:
            if not enemy.alive:
                continue
            d = math.hypot(enemy.x - self.x, enemy.y - self.y)
            if d < best_dist:
                best_dist = d
                nearest = enemy
        if nearest is None:
            return
        self.angle = math.atan2(nearest.y - self.y, nearest.x - self.x)
        dmg = self.damage + (self.level - 1) * 5
        bullets.append(spawn_bullet(self.x, self.y, self.angle, dmg, owner="turret", source_size=20))
        self.cooldown = max(0.25, TURRET_COOLDOWN - self.level * 0.06)

    def draw(self, screen, textures=None):
        if self.level <= 0:
            return
        if textures:
            img = textures["turret"]
            rot = pygame.transform.rotate(img, -math.degrees(self.angle))
            rect = rot.get_rect(center=(int(self.x), int(self.y)))
            screen.blit(rot, rect)
            font = pygame.font.SysFont("arial", 12, bold=True)
            screen.blit(font.render(str(self.level), True, WHITE), (self.x - 4, self.y - 22))
        else:
            pygame.draw.circle(screen, CYAN, (int(self.x), int(self.y)), 10)


class Enemy:
    def __init__(self, x, y, wave, level=1, enemy_type="normal"):
        self.x = x
        self.y = y
        self.enemy_type = enemy_type
        lvl_bonus = (level - 1)
        self.hp = ENEMY_HP + wave * WAVE_ENEMY_HP + lvl_bonus * LEVEL_ENEMY_HP
        self.speed = ENEMY_SPEED + wave * 3 + lvl_bonus * LEVEL_ENEMY_SPEED
        self.damage = ENEMY_DAMAGE + wave * WAVE_ENEMY_DAMAGE + lvl_bonus * LEVEL_ENEMY_DAMAGE
        self.size = ENEMY_SIZE
        self.vision = 240

        if enemy_type == "runner":
            self.speed *= RUNNER_SPEED_MULT
            self.hp *= RUNNER_HP_MULT
            self.size = 16
            self.damage *= 0.75
            self.vision = 300
        elif enemy_type == "tank":
            self.speed *= TANK_SPEED_MULT
            self.hp *= TANK_HP_MULT
            self.size = 26
            self.damage *= TANK_DAMAGE_MULT
            self.vision = 220
        elif enemy_type == "shooter":
            self.speed *= SHOOTER_SPEED_MULT
            self.hp *= SHOOTER_HP_MULT
            self.size = 18
            self.damage *= SHOOTER_DAMAGE_MULT
            self.vision = SHOOTER_RANGE
            self.shoot_cd = 0.5
        elif enemy_type == "swarm":
            self.speed *= SWARM_SPEED_MULT
            self.hp *= SWARM_HP_MULT
            self.size = 14
            self.damage *= SWARM_DAMAGE_MULT
            self.vision = 280

        self.shoot_cd = 0.5 if enemy_type == "shooter" else 999.0

        self.alive = True
        self.attack_timer = 0
        self.target = "player"

    @property
    def rect(self):
        return pygame.Rect(int(self.x - self.size / 2), int(self.y - self.size / 2), self.size, self.size)

    def _pick_target(self, player, base_rect, is_night=False):
        vision = self.vision * (NIGHT_VISION_MULT if is_night else 1.0)
        dist_player = math.hypot(self.x - player.x, self.y - player.y)
        dist_base = math.hypot(self.x - base_rect.centerx, self.y - base_rect.centery)

        if self.enemy_type == "runner":
            if dist_player <= vision:
                self.target = "player"
                return player.x, player.y
            if dist_base <= vision:
                self.target = "base"
                return base_rect.centerx, base_rect.centery
            self.target = "player"
            return player.x, player.y

        if self.enemy_type == "tank":
            if dist_base <= vision * 1.1:
                self.target = "base"
                return base_rect.centerx, base_rect.centery
            if dist_player <= vision:
                self.target = "player"
                return player.x, player.y
            self.target = "base"
            return base_rect.centerx, base_rect.centery

        if self.enemy_type == "shooter":
            if dist_player <= vision:
                self.target = "player"
                return player.x, player.y
            if dist_base <= vision:
                self.target = "base"
                return base_rect.centerx, base_rect.centery
            self.target = "player"
            return player.x, player.y

        if self.enemy_type == "swarm":
            if dist_player <= vision:
                self.target = "player"
                return player.x, player.y
            self.target = "base"
            return base_rect.centerx, base_rect.centery

        if dist_player <= dist_base:
            self.target = "player"
            return player.x, player.y
        self.target = "base"
        return base_rect.centerx, base_rect.centery

    def update(self, dt, player, base_rect, walls, is_night=False, bullets=None):
        if not self.alive:
            return 0

        target_x, target_y = self._pick_target(player, base_rect, is_night)
        dx = target_x - self.x
        dy = target_y - self.y
        dist = math.hypot(dx, dy)

        if self.enemy_type == "shooter" and dist < SHOOTER_RANGE * 0.7:
            pass
        elif dist > 1:
            self.x += dx / dist * self.speed * dt
            self.y += dy / dist * self.speed * dt
            self.x, self.y = push_out_of_walls(self.x, self.y, self.size, walls)

        self.shoot_cd -= dt
        if (
            bullets is not None
            and self.enemy_type == "shooter"
            and self.shoot_cd <= 0
            and dist <= SHOOTER_RANGE
        ):
            angle = math.atan2(target_y - self.y, target_x - self.x)
            bullets.append(
                spawn_bullet(self.x, self.y, angle, self.damage, owner="enemy", source_size=self.size)
            )
            self.shoot_cd = SHOOTER_COOLDOWN

        self.attack_timer -= dt
        base_damage = 0
        if self.attack_timer <= 0:
            if self.target == "player" and self.rect.colliderect(player.rect):
                player.hp -= self.damage
                self.attack_timer = 0.8
            elif self.target == "base" and self.rect.colliderect(base_rect):
                base_damage = self.damage
                self.attack_timer = 1.0
        return base_damage

    def draw(self, screen, textures=None):
        if textures:
            tex_key = {
                "normal": "enemy",
                "runner": "enemy_runner",
                "tank": "enemy_tank",
                "shooter": "enemy_shooter",
                "swarm": "enemy_swarm",
            }.get(self.enemy_type, "enemy")
            img = textures[tex_key]
            rect = img.get_rect(center=(int(self.x), int(self.y)))
            screen.blit(img, rect)
        else:
            pygame.draw.rect(screen, RED, self.rect)


class Boss(Enemy):
    def __init__(self, x, y, wave, level=1):
        super().__init__(x, y, wave, level, enemy_type="boss")
        self.enemy_type = "boss"
        self.hp = BOSS_HP + max(0, level - BOSS_LEVEL) * 80
        self.max_hp = self.hp
        self.speed = BOSS_SPEED
        self.damage = BOSS_DAMAGE
        self.size = BOSS_SIZE
        self.vision = 320
        self.attack_timer = 0
        self.phase_timer = 4.0

    def update(self, dt, player, base_rect, walls, is_night=False, bullets=None):
        if not self.alive:
            return 0

        self.phase_timer -= dt
        target_x, target_y = self._pick_target(player, base_rect, is_night)
        dx = target_x - self.x
        dy = target_y - self.y
        dist = math.hypot(dx, dy)
        if dist > 1:
            self.x += dx / dist * self.speed * dt
            self.y += dy / dist * self.speed * dt
            self.x, self.y = push_out_of_walls(self.x, self.y, self.size, walls)

        if bullets is not None and self.phase_timer <= 0:
            for spread in (-0.35, -0.15, 0, 0.15, 0.35):
                angle = math.atan2(target_y - self.y, target_x - self.x) + spread
                bullets.append(
                    spawn_bullet(
                        self.x, self.y, angle, self.damage * 0.6, owner="enemy", source_size=self.size
                    )
                )
            self.phase_timer = 2.2

        self.attack_timer -= dt
        base_damage = 0
        if self.attack_timer <= 0:
            if self.rect.colliderect(player.rect):
                player.hp -= self.damage
                self.attack_timer = 0.7
            elif self.rect.colliderect(base_rect):
                base_damage = self.damage * 1.2
                self.attack_timer = 0.9
        return base_damage

    def draw(self, screen, textures=None):
        if textures:
            img = textures["enemy_boss"]
            rect = img.get_rect(center=(int(self.x), int(self.y)))
            screen.blit(img, rect)
            bar_w = 50
            ratio = max(0, self.hp / self.max_hp)
            pygame.draw.rect(screen, RED, (self.x - bar_w // 2, self.y - self.size, bar_w, 6))
            pygame.draw.rect(
                screen,
                ORANGE,
                (self.x - bar_w // 2, self.y - self.size, int(bar_w * ratio), 6),
            )
        else:
            pygame.draw.rect(screen, RED, self.rect)


def roll_enemy_drop():
    r = random.randint(1, 100)
    if r <= DROP_COIN:
        return "coin"
    if r <= DROP_COIN + DROP_KEY:
        return "key"
    if r <= DROP_COIN + DROP_KEY + DROP_MEDKIT:
        return "medkit"
    if r <= DROP_COIN + DROP_KEY + DROP_MEDKIT + DROP_AMMO:
        return "ammo"
    return None


def _roll_enemy_type(level):
    r = random.randint(1, 100)
    runner_chance = 18 + level * 2
    tank_chance = 16 + level * 2
    shooter_chance = 12 + level * 3
    swarm_chance = 10 + level * 2
    if r <= runner_chance:
        return "runner"
    if r <= runner_chance + tank_chance:
        return "tank"
    if r <= runner_chance + tank_chance + shooter_chance:
        return "shooter"
    if r <= runner_chance + tank_chance + shooter_chance + swarm_chance:
        return "swarm"
    return "normal"


def spawn_boss(wave, level, play_bounds):
    center_x = play_bounds.centerx
    center_y = play_bounds.top + 40
    return Boss(center_x, center_y, wave, level)


def spawn_enemy(wave, level=1, play_bounds=None, force_type=None):
    if play_bounds is None:
        play_bounds = pygame.Rect(40, 40, WIDTH - 80, HEIGHT - 80)

    center_x = play_bounds.centerx
    center_y = play_bounds.centery
    min_dist = SPAWN_MIN_DIST_FROM_CENTER + (level - 1) * 20
    pad = 25
    left = play_bounds.left + pad
    right = play_bounds.right - pad
    top = play_bounds.top + pad
    bottom = play_bounds.bottom - pad
    etype = force_type or _roll_enemy_type(level)

    for _ in range(50):
        side = random.randint(0, 3)
        if side == 0:
            x = random.randint(int(left), int(right))
            y = top
        elif side == 1:
            x = right
            y = random.randint(int(top), int(bottom))
        elif side == 2:
            x = random.randint(int(left), int(right))
            y = bottom
        else:
            x = left
            y = random.randint(int(top), int(bottom))

        if math.hypot(x - center_x, y - center_y) >= min_dist:
            return Enemy(x, y, wave, level, etype)

    angle = random.uniform(0, math.pi * 2)
    x = center_x + math.cos(angle) * min_dist
    y = center_y + math.sin(angle) * min_dist
    x = max(left, min(right, x))
    y = max(top, min(bottom, y))
    return Enemy(x, y, wave, level, etype)
