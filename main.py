import os
import math
import random
import array
import pygame

# ------------------------------------------------------------
# 16-bit Side-Scrolling Shooter
# Assets: gfx/gsprites.png
# ------------------------------------------------------------

WIDTH, HEIGHT = 960, 540
FPS = 60

TITLE_LOGO = os.path.join("gfx", "title.png")
GAME_NAME = "Aimer 8"

ASSET_PATH = os.path.join("gfx", "gsprites.png")
GREEN_KEY = (0, 255, 0)

MAIN_MUSIC = os.path.join("audio", "main.mp3")
LEVEL_MUSIC = os.path.join("audio", "level.mp3")

MUSIC_VOLUME = 0.45
_current_music = None

PLAYER_SPEED = 5.0
BULLET_SPEED = 10.0
FIRE_COOLDOWN = 170  # ms

START_LIVES = 3
BASE_ENEMY_SPEED = 3.0
SPEED_INCREASE_EVERY = 90
BIG_ENEMY_EVERY = 30

NORMAL_SCORE = 100
BIG_SCORE = 700

pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.init()

screen = pygame.display.set_mode((WIDTH, HEIGHT))
# pygame.display.set_caption("16-Bit Star Blaster")
clock = pygame.time.Clock()


# ------------------------------------------------------------
# Sound generation: no external files required
# ------------------------------------------------------------

def make_tone(freq=440, duration=0.12, volume=0.35, slide=0.0, noise=False):
    try:
        sample_rate = 44100
        n_samples = int(sample_rate * duration)
        buf = array.array("h")

        for i in range(n_samples):
            t = i / sample_rate
            env = 1.0 - (i / n_samples)
            f = freq + slide * t

            if noise:
                val = random.uniform(-1, 1)
            else:
                val = math.sin(2 * math.pi * f * t)
                val += 0.35 * math.sin(2 * math.pi * f * 2.0 * t)

            sample = int(32767 * volume * env * val)
            buf.append(sample)

        return pygame.mixer.Sound(buffer=buf.tobytes())
    except pygame.error:
        return None


LASER_SOUND = make_tone(freq=920, duration=0.09, volume=0.28, slide=2600)
BOOM_SOUND = make_tone(freq=110, duration=0.22, volume=0.45, noise=True)


def play(sound):
    if sound:
        try:
            sound.play()
        except pygame.error:
            pass

def set_music(track):
    """
    track can be:
    - "main"  -> audio/main.mp3, used on title and game over
    - "level" -> audio/level.mp3, used during gameplay
    """
    global _current_music

    if _current_music == track:
        return

    if track == "main":
        path = MAIN_MUSIC
    elif track == "level":
        path = LEVEL_MUSIC
    else:
        pygame.mixer.music.stop()
        _current_music = None
        return

    try:
        pygame.mixer.music.stop()

        if os.path.exists(path):
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(MUSIC_VOLUME)
            pygame.mixer.music.play(-1)  # loop forever
            _current_music = track
        else:
            print(f"Missing music file: {path}")
            _current_music = None

    except pygame.error as exc:
        print(f"Could not play music {path}: {exc}")
        _current_music = None

# ------------------------------------------------------------
# Asset loading and sprite-sheet slicing
# The generated sheet is not guaranteed to be exactly 512/1024,
# so these rects are proportional to the generated 1254x1254 sheet.
# ------------------------------------------------------------

def transparent_green(surface):
    surf = surface.convert_alpha()
    w, h = surf.get_size()

    surf.lock()
    for y in range(h):
        for x in range(w):
            r, g, b, a = surf.get_at((x, y))
            if g > 160 and r < 90 and b < 90:
                surf.set_at((x, y), (0, 0, 0, 0))
    surf.unlock()

    return surf

def load_title_logo():
    try:
        if os.path.exists(TITLE_LOGO):
            logo = pygame.image.load(TITLE_LOGO).convert_alpha()
            logo = transparent_green(logo)

            # Scale logo to fit nicely on the main screen
            max_w = int(WIDTH * 0.82)
            if logo.get_width() > max_w:
                scale = max_w / logo.get_width()
                new_size = (
                    int(logo.get_width() * scale),
                    int(logo.get_height() * scale),
                )
                logo = pygame.transform.scale(logo, new_size)

            return logo
        else:
            print(f"Missing logo file: {TITLE_LOGO}")
    except pygame.error as exc:
        print(f"Could not load title logo: {exc}")

    return None

def trim_alpha(surface):
    rect = surface.get_bounding_rect()
    if rect.width <= 0 or rect.height <= 0:
        return surface
    return surface.subsurface(rect).copy()


def pixel_scale(surface, size):
    return pygame.transform.scale(surface, size)


def crop_from_sheet(sheet, rect, out_size):
    base_w, base_h = 1254, 1254
    sw, sh = sheet.get_size()

    x, y, w, h = rect
    sx = int(x / base_w * sw)
    sy = int(y / base_h * sh)
    ss_w = int(w / base_w * sw)
    ss_h = int(h / base_h * sh)

    sx = max(0, min(sx, sw - 1))
    sy = max(0, min(sy, sh - 1))
    ss_w = max(1, min(ss_w, sw - sx))
    ss_h = max(1, min(ss_h, sh - sy))

    part = sheet.subsurface((sx, sy, ss_w, ss_h)).copy()
    part = transparent_green(part)
    part = trim_alpha(part)

    if part.get_width() <= 2 or part.get_height() <= 2:
        raise ValueError("Empty sprite crop")

    return pixel_scale(part, out_size)


def make_fallback_ship(size=(42, 28), main=(220, 220, 230), accent=(40, 180, 255)):
    surf = pygame.Surface(size, pygame.SRCALPHA)
    w, h = size

    pygame.draw.polygon(
        surf,
        main,
        [(2, h // 2), (w - 8, 3), (w - 2, h // 2), (w - 8, h - 3)]
    )
    pygame.draw.polygon(
        surf,
        (80, 80, 90),
        [(10, h // 2), (w - 12, 8), (w - 8, h // 2), (w - 12, h - 8)]
    )
    pygame.draw.rect(surf, accent, (w // 2, h // 2 - 4, 12, 8))
    pygame.draw.polygon(surf, (255, 70, 70), [(7, 3), (14, 11), (7, 11)])
    pygame.draw.polygon(surf, (255, 70, 70), [(7, h - 3), (14, h - 11), (7, h - 11)])
    pygame.draw.rect(surf, (50, 220, 255), (0, h // 2 - 6, 8, 4))
    pygame.draw.rect(surf, (40, 120, 255), (0, h // 2 + 2, 8, 4))

    return surf


def make_fallback_enemy(size=(44, 34), color=(160, 60, 220)):
    surf = pygame.Surface(size, pygame.SRCALPHA)
    w, h = size

    pygame.draw.polygon(
        surf,
        color,
        [(w - 2, h // 2), (10, 2), (2, h // 2), (10, h - 2)]
    )
    pygame.draw.rect(surf, (45, 45, 55), (10, 9, 24, h - 18))
    pygame.draw.rect(surf, (255, 130, 20), (4, h // 2 - 5, 8, 10))
    pygame.draw.rect(surf, (40, 255, 90), (w - 16, h // 2 - 4, 6, 8))

    return surf


def make_fallback_bullet(size=(20, 8), color=(60, 220, 255)):
    surf = pygame.Surface(size, pygame.SRCALPHA)
    w, h = size
    pygame.draw.rect(surf, color, (4, 2, w - 6, h - 4))
    pygame.draw.rect(surf, (255, 255, 255), (0, 1, 6, h - 2))
    return surf


def make_fallback_explosion(size=(42, 42), frame=0):
    surf = pygame.Surface(size, pygame.SRCALPHA)
    cx, cy = size[0] // 2, size[1] // 2
    r = 8 + frame * 6
    pygame.draw.circle(surf, (150, 20, 0), (cx, cy), r)
    pygame.draw.circle(surf, (255, 100, 0), (cx, cy), max(2, r - 5))
    pygame.draw.circle(surf, (255, 235, 90), (cx, cy), max(2, r - 11))
    pygame.draw.circle(surf, (255, 255, 255), (cx, cy), max(1, r - 17))
    for _ in range(8 + frame * 4):
        px = cx + random.randint(-r - 8, r + 8)
        py = cy + random.randint(-r - 8, r + 8)
        pygame.draw.rect(surf, (80, 50, 40), (px, py, 3, 3))
    return surf


def load_assets():
    assets = {
        "player": make_fallback_ship(),
        "enemies": [
            make_fallback_enemy(color=(150, 70, 210)),
            make_fallback_enemy(color=(80, 150, 70)),
            make_fallback_enemy(color=(210, 50, 60)),
        ],
        "big_enemy": make_fallback_enemy(size=(92, 70), color=(130, 70, 190)),
        "bullets": [
            make_fallback_bullet(color=(60, 220, 255)),
            make_fallback_bullet(color=(255, 180, 40)),
        ],
        "explosions": [make_fallback_explosion(frame=i) for i in range(4)],
        "planets": [],
        "station": None,
        "nebulae": [],
    }

    if not os.path.exists(ASSET_PATH):
        print(f"Could not find {ASSET_PATH}. Using procedural fallback sprites.")
        return assets

    try:
        sheet = pygame.image.load(ASSET_PATH).convert()

        assets["player"] = crop_from_sheet(sheet, (10, 45, 210, 180), (48, 34))

        assets["enemies"] = [
            crop_from_sheet(sheet, (225, 45, 210, 190), (48, 38)),
            crop_from_sheet(sheet, (440, 50, 210, 185), (48, 38)),
            crop_from_sheet(sheet, (655, 45, 220, 190), (52, 42)),
        ]

        assets["big_enemy"] = crop_from_sheet(sheet, (865, 0, 370, 290), (104, 82))

        assets["bullets"] = [
            crop_from_sheet(sheet, (20, 300, 130, 110), (24, 12)),
            crop_from_sheet(sheet, (155, 300, 130, 110), (24, 12)),
        ]

        assets["explosions"] = [
            crop_from_sheet(sheet, (290, 290, 145, 145), (42, 42)),
            crop_from_sheet(sheet, (455, 285, 160, 160), (52, 52)),
            crop_from_sheet(sheet, (645, 280, 190, 170), (64, 58)),
            crop_from_sheet(sheet, (900, 280, 270, 170), (84, 58)),
        ]

        assets["planets"] = [
            crop_from_sheet(sheet, (380, 475, 260, 250), (96, 96)),
            crop_from_sheet(sheet, (650, 470, 260, 250), (96, 96)),
        ]

        assets["station"] = crop_from_sheet(sheet, (905, 490, 300, 235), (112, 88))

        assets["nebulae"] = [
            crop_from_sheet(sheet, (25, 710, 590, 520), (260, 220)),
            crop_from_sheet(sheet, (635, 710, 590, 520), (260, 220)),
        ]

    except Exception as exc:
        print("Sprite sheet loaded, but slicing failed. Using fallback sprites.")
        print(exc)

    return assets


ASSETS = load_assets()


# ------------------------------------------------------------
# Background
# ------------------------------------------------------------

class Star:
    def __init__(self, slow=False):
        self.slow = slow
        self.reset(random.randrange(WIDTH), random.randrange(HEIGHT))

    def reset(self, x=None, y=None):
        self.x = random.randrange(WIDTH) if x is None else x
        self.y = random.randrange(HEIGHT) if y is None else y
        self.size = random.choice([1, 1, 1, 2]) if not self.slow else random.choice([1, 1, 2])
        self.speed = random.uniform(0.25, 0.8) if self.slow else random.uniform(1.3, 3.2)
        self.color = random.choice(
            [(150, 180, 255), (255, 255, 255), (120, 255, 220), (255, 220, 130)]
        )

    def update(self):
        self.x -= self.speed
        if self.x < -4:
            self.reset(WIDTH + random.randrange(20), random.randrange(HEIGHT))

    def draw(self, surf, ox=0, oy=0):
        pygame.draw.rect(
            surf,
            self.color,
            (int(self.x + ox), int(self.y + oy), self.size, self.size),
        )


class DistantObject:
    def __init__(self, image, speed):
        self.image = image
        self.speed = speed
        self.x = random.randrange(WIDTH, WIDTH + 1200)
        self.y = random.randrange(40, HEIGHT - 180)

    def update(self):
        self.x -= self.speed
        if self.x < -self.image.get_width() - 200:
            self.x = random.randrange(WIDTH + 300, WIDTH + 1600)
            self.y = random.randrange(30, HEIGHT - 180)

    def draw(self, surf, ox=0, oy=0):
        surf.blit(self.image, (int(self.x + ox), int(self.y + oy)))


# ------------------------------------------------------------
# Game objects
# ------------------------------------------------------------

class Player:
    def __init__(self):
        self.image = ASSETS["player"]
        self.rect = self.image.get_rect()
        self.rect.x = 55
        self.rect.centery = HEIGHT // 2
        self.lives = START_LIVES
        self.blink_timer = 0
        self.invuln_timer = 0

    def update(self, dt):
        keys = pygame.key.get_pressed()
        dx = dy = 0

        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx -= PLAYER_SPEED
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx += PLAYER_SPEED
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy -= PLAYER_SPEED
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy += PLAYER_SPEED

        if dx and dy:
            dx *= 0.7071
            dy *= 0.7071

        self.rect.x += int(dx)
        self.rect.y += int(dy)
        self.rect.clamp_ip(screen.get_rect())

        self.blink_timer = max(0, self.blink_timer - dt)
        self.invuln_timer = max(0, self.invuln_timer - dt)

    def hit(self):
        self.lives -= 1
        self.blink_timer = 1200
        self.invuln_timer = 900

    def draw(self, surf):
        if self.blink_timer > 0:
            if (pygame.time.get_ticks() // 90) % 2 == 0:
                surf.blit(self.image, self.rect)
        else:
            surf.blit(self.image, self.rect)


class Bullet:
    def __init__(self, x, y):
        self.image = random.choice(ASSETS["bullets"])
        self.rect = self.image.get_rect(midleft=(x, y))
        self.dead = False

    def update(self):
        self.rect.x += int(BULLET_SPEED)
        if self.rect.left > WIDTH:
            self.dead = True

    def draw(self, surf):
        surf.blit(self.image, self.rect)


class Enemy:
    def __init__(self, speed, total_spawned):
        self.big = total_spawned % BIG_ENEMY_EVERY == 0

        if self.big:
            self.image = ASSETS["big_enemy"]
            self.max_hp = 5
            self.hp = 5
            self.score = BIG_SCORE
            self.speed = speed * 0.78
        else:
            self.image = random.choice(ASSETS["enemies"])
            self.max_hp = 1
            self.hp = 1
            self.score = NORMAL_SCORE
            self.speed = speed + random.uniform(-0.2, 0.45)

        self.rect = self.image.get_rect()
        self.rect.left = WIDTH + random.randrange(10, 100)
        self.rect.y = random.randrange(45, HEIGHT - self.rect.height - 25)
        self.dead = False
        self.flash = 0

    def update(self, dt):
        self.rect.x -= int(self.speed)
        self.flash = max(0, self.flash - dt)

        if self.rect.right < -80:
            self.dead = True

    def damage(self):
        self.hp -= 1
        self.flash = 80
        if self.hp <= 0:
            self.dead = True
            return True
        return False

    def draw(self, surf):
        surf.blit(self.image, self.rect)

        if self.big:
            bar_w = self.rect.width
            bar_h = 5
            x = self.rect.x
            y = self.rect.y - 9
            pygame.draw.rect(surf, (50, 20, 30), (x, y, bar_w, bar_h))
            fill = int(bar_w * (self.hp / self.max_hp))
            pygame.draw.rect(surf, (70, 255, 80), (x, y, fill, bar_h))

        if self.flash > 0:
            flash = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            flash.fill((255, 255, 255, 90))
            surf.blit(flash, self.rect)


class Explosion:
    def __init__(self, center):
        self.frames = ASSETS["explosions"]
        self.center = center
        self.timer = 0
        self.frame_time = 70
        self.dead = False

    def update(self, dt):
        self.timer += dt
        if self.timer >= self.frame_time * len(self.frames):
            self.dead = True

    def draw(self, surf):
        idx = min(len(self.frames) - 1, self.timer // self.frame_time)
        img = self.frames[int(idx)]
        rect = img.get_rect(center=self.center)
        surf.blit(img, rect)


# ------------------------------------------------------------
# Game state
# ------------------------------------------------------------

class Game:
    def __init__(self):
        self.reset(to_menu=True)

    def reset(self, to_menu=False):
        self.player = Player()
        self.bullets = []
        self.enemies = []
        self.explosions = []

        self.score = 0
        self.total_spawned = 0
        self.enemy_speed = BASE_ENEMY_SPEED
        self.spawn_timer = 0
        self.spawn_delay = 850

        self.last_fire = 0
        self.screen_shake = 0

        self.state = "menu" if to_menu else "playing"
        self.game_over = False
        self.title_logo = load_title_logo()
        self.menu_timer = 0

        self.bg_slow = [Star(slow=True) for _ in range(70)]
        self.bg_fast = [Star(slow=False) for _ in range(130)]

        bg_assets = []
        bg_assets.extend(ASSETS.get("planets", []))
        if ASSETS.get("station"):
            bg_assets.append(ASSETS["station"])
        bg_assets.extend(ASSETS.get("nebulae", []))

        self.distant = []
        for _ in range(5):
            if bg_assets:
                self.distant.append(
                    DistantObject(random.choice(bg_assets), random.uniform(0.08, 0.35))
                )

        if self.state == "menu":
            set_music("main")
        else:
            set_music("level")

    def start_game(self):
        self.reset(to_menu=False)
        set_music("level")

    def fire(self):
        if self.state != "playing":
            return

        now = pygame.time.get_ticks()
        if now - self.last_fire >= FIRE_COOLDOWN:
            self.last_fire = now
            self.bullets.append(Bullet(self.player.rect.right - 4, self.player.rect.centery))
            play(LASER_SOUND)

    def spawn_enemy(self):
        self.total_spawned += 1

        if self.total_spawned > 1 and self.total_spawned % SPEED_INCREASE_EVERY == 0:
            self.enemy_speed += 1.50
            self.spawn_delay = max(430, self.spawn_delay - 45)

        self.enemies.append(Enemy(self.enemy_speed, self.total_spawned))

    def update(self, dt):
        # Background keeps moving on menu and game over
        for s in self.bg_slow:
            s.update()
        for s in self.bg_fast:
            s.update()
        for obj in self.distant:
            obj.update()

        if self.state == "menu":
            self.menu_timer += dt

        if self.state != "playing":
            self.screen_shake = 0
            return

        self.screen_shake = max(0, self.screen_shake - dt)

        self.player.update(dt)

        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE]:
            self.fire()

        self.spawn_timer += dt
        if self.spawn_timer >= self.spawn_delay:
            self.spawn_timer = 0
            self.spawn_enemy()

        for bullet in self.bullets:
            bullet.update()

        for enemy in self.enemies:
            enemy.update(dt)

        for explosion in self.explosions:
            explosion.update(dt)

        self.handle_collisions()

        self.bullets = [b for b in self.bullets if not b.dead]
        self.enemies = [e for e in self.enemies if not e.dead]
        self.explosions = [e for e in self.explosions if not e.dead]

    def handle_collisions(self):
        for bullet in self.bullets:
            if bullet.dead:
                continue

            for enemy in self.enemies:
                if enemy.dead:
                    continue

                if bullet.rect.colliderect(enemy.rect):
                    bullet.dead = True
                    destroyed = enemy.damage()

                    if destroyed:
                        self.score += enemy.score
                        self.explosions.append(Explosion(enemy.rect.center))
                        play(BOOM_SOUND)
                    else:
                        self.explosions.append(Explosion(bullet.rect.center))
                        play(BOOM_SOUND)

                    break

        if self.player.invuln_timer <= 0:
            for enemy in self.enemies:
                if enemy.dead:
                    continue

                if self.player.rect.colliderect(enemy.rect):
                    enemy.dead = True
                    self.explosions.append(Explosion(enemy.rect.center))
                    self.player.hit()
                    self.screen_shake = 420
                    play(BOOM_SOUND)

                    if self.player.lives <= 0:
                        self.state = "game_over"
                        self.game_over = True
                        self.screen_shake = 0
                        set_music("main")
                    break

    def draw_background(self, surf, ox=0, oy=0):
        surf.fill((2, 4, 18))

        for obj in self.distant:
            obj.draw(surf, ox * 0.25, oy * 0.25)

        for s in self.bg_slow:
            s.draw(surf, ox * 0.3, oy * 0.3)

        for s in self.bg_fast:
            s.draw(surf, ox * 0.7, oy * 0.7)

        for y in range(0, HEIGHT, 4):
            pygame.draw.line(surf, (0, 0, 8), (0, y), (WIDTH, y))

    def draw_ui(self, surf):
        font = pygame.font.SysFont("consolas,dejavusansmono,couriernew", 18)
        small = pygame.font.SysFont("consolas,dejavusansmono,couriernew", 14)

        ui_lines = [
            f"SCORE {self.score:07d}",
            f"LIVES {self.player.lives}",
            f"SPAWNED {self.total_spawned}",
            f"ENEMY SPD {self.enemy_speed:.2f}",
        ]

        x = 14
        y = 10
        for line in ui_lines:
            shadow = font.render(line, False, (0, 0, 0))
            text = font.render(line, False, (120, 255, 160))
            surf.blit(shadow, (x + 2, y + 2))
            surf.blit(text, (x, y))
            y += 23

        hint = small.render("WASD / ARROWS MOVE   SPACE FIRE", False, (110, 170, 210))
        surf.blit(hint, (WIDTH - hint.get_width() - 14, 12))

    def draw_menu(self, surf):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        surf.blit(overlay, (0, 0))

        title_font = pygame.font.SysFont("consolas,dejavusansmono,couriernew", 54, bold=True)
        font = pygame.font.SysFont("consolas,dejavusansmono,couriernew", 24)
        small = pygame.font.SysFont("consolas,dejavusansmono,couriernew", 18)

        # Logo scroll animation: starts above the screen, eases into the middle/top area
        target_y = HEIGHT // 2 - 150
        start_y = -220
        anim_duration = 1600

        t = min(1.0, self.menu_timer / anim_duration)

        # ease-out cubic
        eased = 1.0 - pow(1.0 - t, 3)

        logo_y = int(start_y + (target_y - start_y) * eased)

        if self.title_logo:
            logo_rect = self.title_logo.get_rect(centerx=WIDTH // 2)
            logo_rect.y = logo_y
            surf.blit(self.title_logo, logo_rect)
        else:
            title = title_font.render(GAME_NAME, False, (120, 255, 180))
            surf.blit(title, title.get_rect(center=(WIDTH // 2, logo_y + 80)))

        subtitle = font.render("16-BIT SIDE-SCROLLING SHOOTER", False, (120, 190, 255))
        start = font.render("PRESS ENTER TO START", False, (255, 230, 120))
        controls = small.render("WASD / ARROWS MOVE   SPACE FIRE   ESC QUIT", False, (170, 170, 190))

        # Blink the start prompt
        show_start = (pygame.time.get_ticks() // 500) % 2 == 0

        # surf.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 35)))

        if show_start:
            surf.blit(start, start.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 88)))

        surf.blit(controls, controls.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 138)))

    def draw_game_over(self, surf):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        surf.blit(overlay, (0, 0))

        title_font = pygame.font.SysFont("consolas,dejavusansmono,couriernew", 52, bold=True)
        font = pygame.font.SysFont("consolas,dejavusansmono,couriernew", 24)

        title = title_font.render("GAME OVER", False, (255, 70, 80))
        score = font.render(f"FINAL SCORE: {self.score}", False, (160, 255, 180))
        spawned = font.render(f"ENEMIES SPAWNED: {self.total_spawned}", False, (160, 220, 255))
        restart = font.render("PRESS R TO RESTART", False, (255, 230, 120))

        surf.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 80)))
        surf.blit(score, score.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 20)))
        surf.blit(spawned, spawned.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 18)))
        surf.blit(restart, restart.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 80)))

    def draw(self, target):
        ox = oy = 0

        if self.state == "playing" and self.screen_shake > 0:
            strength = int(7 * (self.screen_shake / 420))
            ox = random.randint(-strength, strength)
            oy = random.randint(-strength, strength)

        world = pygame.Surface((WIDTH, HEIGHT))
        self.draw_background(world, ox, oy)

        if self.state == "playing":
            for bullet in self.bullets:
                bullet.draw(world)

            for enemy in self.enemies:
                enemy.draw(world)

            self.player.draw(world)

            for explosion in self.explosions:
                explosion.draw(world)

            self.draw_ui(world)

        elif self.state == "menu":
            self.draw_menu(world)

        elif self.state == "game_over":
            for explosion in self.explosions:
                explosion.draw(world)

            self.draw_ui(world)
            self.draw_game_over(world)

        target.blit(world, (ox, oy))

# ------------------------------------------------------------
# Main loop
# ------------------------------------------------------------

def main():
    game = Game()
    running = True

    while running:
        dt = clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                elif game.state == "menu":
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        game.start_game()

                elif game.state == "game_over":
                    if event.key == pygame.K_r:
                        game.start_game()

                elif game.state == "playing":
                    if event.key == pygame.K_SPACE:
                        game.fire()

        game.update(dt)
        game.draw(screen)
        pygame.display.flip()

    pygame.mixer.music.stop()
    pygame.quit()


if __name__ == "__main__":
    main()