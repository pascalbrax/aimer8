import os
import sys
import math
import random
import array
import pygame

# ------------------------------------------------------------
# 16-bit Side-Scrolling Shooter
# Assets: gfx/sprites.png
# ------------------------------------------------------------

def _asset(path):
    """Resolve asset paths whether running from source or a PyInstaller bundle."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, path)

WIDTH, HEIGHT = 960, 540
FPS = 60

TITLE_LOGO = _asset(os.path.join("gfx", "title.png"))
GAME_NAME = "Aimer 8"

ASSET_PATH = _asset(os.path.join("gfx", "sprites.png"))

MAIN_MUSIC = _asset(os.path.join("audio", "main.mp3"))
LEVEL_MUSIC = _asset(os.path.join("audio", "level.mp3"))

VOL = {"music": 0.45, "sfx": 0.5}
_current_music = None

PLAYER_SPEED = 5.0
BULLET_SPEED = 10.0
FIRE_COOLDOWN = 170  # ms

DIFF_OPTIONS = ["easy", "normal", "hard"]
LIVES_BY_DIFFICULTY = {"easy": 5, "normal": 3, "hard": 1}
START_LIVES = 3  # kept as fallback default

BASE_ENEMY_SPEED = 3.0
SPEED_INCREASE_EVERY = 90

NORMAL_SCORE = 100
BIG_SCORE = 700
TRAIN_SCORE = 150
BOSS_SCORE = 3000

TRAIN_EVERY = 15       # every N spawns a special wave appears (train/big alternating)
TRAIN_SPACING = 52     # pixels between ships in the chain
TRAIN_AMPLITUDE = 85   # vertical sine amplitude in pixels
TRAIN_WAVE_FREQ = 0.020  # horizontal frequency of the sine wave

BOSS_EVERY = 60        # every N spawns a boss monster appears (takes priority over the special wave)
BOSS_HP = 40           # bullets needed to destroy the boss

PLAYER_ANIM_MS = 130   # ms between player engine-animation frames

pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.init()

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption(GAME_NAME)

_icon_path = _asset(os.path.join("gfx", "icon.png"))
if os.path.exists(_icon_path):
    _icon_surf = pygame.image.load(_icon_path).convert_alpha()
    pygame.display.set_icon(_icon_surf)

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
            sound.set_volume(VOL["sfx"])
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
            pygame.mixer.music.set_volume(VOL["music"])
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


def crop_alpha(sheet, rect, out_size):
    """Crop a sprite from an alpha sheet (sprites.png), trim padding, scale to out_size.

    rect is (x, y, w, h) in absolute sheet pixels. The sheet already carries a
    real alpha channel, so no chroma-key removal is needed.
    """
    part = trim_alpha(sheet.subsurface(rect).copy())

    if part.get_width() <= 2 or part.get_height() <= 2:
        raise ValueError("Empty sprite crop")

    return pixel_scale(part, out_size)


def crop_alpha_fit(sheet, rect, box):
    """Like crop_alpha, but preserve aspect ratio and centre the sprite on a
    transparent surface of exactly `box` size. Used where several sprites must
    share a consistent footprint (e.g. the player animation frames)."""
    part = trim_alpha(sheet.subsurface(rect).copy())
    pw, ph = part.get_size()
    if pw <= 2 or ph <= 2:
        raise ValueError("Empty sprite crop")

    bw, bh = box
    scale = min(bw / pw, bh / ph)
    new_size = (max(1, int(pw * scale)), max(1, int(ph * scale)))
    scaled = pygame.transform.scale(part, new_size)

    canvas = pygame.Surface(box, pygame.SRCALPHA)
    canvas.blit(scaled, ((bw - new_size[0]) // 2, (bh - new_size[1]) // 2))
    return canvas


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


# Sprite locations on gfx/sprites.png (1254x1254, real alpha), as (x, y, w, h).
PLAYER_FRAMES_SRC = [(28, 71, 167, 135), (246, 70, 167, 135)]
ENEMY_SRC = [
    (458, 64, 159, 145), (635, 64, 132, 141), (790, 68, 131, 140),
    (941, 74, 118, 128), (1077, 69, 149, 138),
    (30, 321, 154, 131), (207, 314, 129, 147), (354, 321, 177, 138),
]
BIG_ENEMY_SRC = (553, 282, 279, 195)
BOSS_SRC = (851, 234, 384, 290)
BULLET_SRC = [(35, 627, 109, 29), (197, 624, 106, 35)]
EXPLOSION_SRC = [
    (358, 603, 88, 75), (489, 585, 119, 104), (643, 572, 139, 127),
    (816, 559, 160, 146), (1009, 539, 206, 177),
]
PLANET_SRC = [(450, 734, 210, 209), (694, 731, 213, 215)]
STATION_SRC = (938, 731, 267, 231)
NEBULA_SRC = [(76, 974, 506, 236), (623, 975, 556, 236)]

PLAYER_BOX = (54, 40)     # shared footprint for the two animation frames
ENEMY_BOX = (54, 46)      # shared footprint for the enemy roster
EXPLOSION_BOXES = [(46, 46), (56, 56), (68, 68), (80, 80), (96, 96)]


def load_assets():
    assets = {
        "player": [
            make_fallback_ship(),
            make_fallback_ship(accent=(255, 180, 40)),
        ],
        "enemies": [
            make_fallback_enemy(color=(150, 70, 210)),
            make_fallback_enemy(color=(80, 150, 70)),
            make_fallback_enemy(color=(210, 50, 60)),
        ],
        "big_enemy": make_fallback_enemy(size=(92, 70), color=(130, 70, 190)),
        "boss": make_fallback_enemy(size=(180, 140), color=(150, 40, 190)),
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
        sheet = pygame.image.load(ASSET_PATH).convert_alpha()

        assets["player"] = [crop_alpha_fit(sheet, r, PLAYER_BOX) for r in PLAYER_FRAMES_SRC]
        assets["enemies"] = [crop_alpha_fit(sheet, r, ENEMY_BOX) for r in ENEMY_SRC]
        assets["big_enemy"] = crop_alpha_fit(sheet, BIG_ENEMY_SRC, (120, 86))
        assets["boss"] = crop_alpha_fit(sheet, BOSS_SRC, (200, 150))

        assets["bullets"] = [crop_alpha_fit(sheet, r, (40, 14)) for r in BULLET_SRC]
        assets["explosions"] = [
            crop_alpha_fit(sheet, r, box) for r, box in zip(EXPLOSION_SRC, EXPLOSION_BOXES)
        ]

        assets["planets"] = [crop_alpha_fit(sheet, r, (96, 96)) for r in PLANET_SRC]
        assets["station"] = crop_alpha_fit(sheet, STATION_SRC, (120, 100))
        assets["nebulae"] = [crop_alpha_fit(sheet, r, (300, 150)) for r in NEBULA_SRC]

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


BG_RNG = random.Random(8)  # fixed seed: distant objects appear in same order every run


class DistantObject:
    def __init__(self, image, speed):
        self.image = image
        self.speed = speed
        self.x = BG_RNG.randrange(WIDTH + 1000, WIDTH + 9000)
        self.y = BG_RNG.randrange(40, HEIGHT - 180)

    def update(self):
        self.x -= self.speed
        if self.x < -self.image.get_width() - 200:
            self.x = BG_RNG.randrange(WIDTH + 4000, WIDTH + 9000)
            self.y = BG_RNG.randrange(30, HEIGHT - 180)

    def draw(self, surf, ox=0, oy=0):
        surf.blit(self.image, (int(self.x + ox), int(self.y + oy)))


# ------------------------------------------------------------
# Game objects
# ------------------------------------------------------------

class Player:
    def __init__(self, lives=START_LIVES):
        self.frames = ASSETS["player"]
        self.frame_idx = 0
        self.anim_timer = 0
        self.image = self.frames[0]
        self.rect = self.image.get_rect()
        self.rect.x = 55
        self.rect.centery = HEIGHT // 2
        self.lives = lives
        self.blink_timer = 0
        self.invuln_timer = 0

    def update(self, dt):
        # Cycle the engine-flicker animation frames
        self.anim_timer += dt
        if self.anim_timer >= PLAYER_ANIM_MS:
            self.anim_timer -= PLAYER_ANIM_MS
            self.frame_idx = (self.frame_idx + 1) % len(self.frames)
            self.image = self.frames[self.frame_idx]

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
    def __init__(self, speed, big=False):
        self.big = big

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


class TrainEnemy:
    """A ship that travels in a sinusoidal wave, chained in a formation."""

    def __init__(self, index, speed, start_x, center_y):
        self.image = random.choice(ASSETS["enemies"])
        self.speed = speed
        # Each ship is staggered behind the lead by index * spacing
        self.x = float(start_x - index * TRAIN_SPACING)
        self.center_y = center_y
        self.dead = False
        self.hp = 1
        self.score = TRAIN_SCORE
        self.big = False
        self.flash = 0
        self.rect = self.image.get_rect()
        self._sync_rect()

    def _wave_y(self):
        return self.center_y + TRAIN_AMPLITUDE * math.sin(self.x * TRAIN_WAVE_FREQ)

    def _sync_rect(self):
        self.rect.x = int(self.x)
        self.rect.centery = max(
            self.rect.height // 2 + 10,
            min(HEIGHT - self.rect.height // 2 - 10, int(self._wave_y())),
        )

    def update(self, dt):
        self.x -= self.speed
        self.flash = max(0, self.flash - dt)
        self._sync_rect()
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
        if self.flash > 0:
            flash_surf = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            flash_surf.fill((255, 255, 255, 90))
            surf.blit(flash_surf, self.rect)


class Boss:
    """A large monster boss: glides in from the right, hovers and bobs
    vertically, soaks up many hits, and cannot be killed by ramming it."""

    is_boss = True

    def __init__(self, speed):
        self.image = ASSETS["boss"]
        self.rect = self.image.get_rect()
        self.rect.left = WIDTH + 20
        self.base_y = HEIGHT // 2
        self.rect.centery = self.base_y

        self.max_hp = BOSS_HP
        self.hp = BOSS_HP
        self.score = BOSS_SCORE
        self.speed = speed
        self.big = True
        self.dead = False
        self.flash = 0
        self.t = 0
        self.target_x = WIDTH - self.rect.width - 30

    def update(self, dt):
        self.t += dt
        # Glide in, then hold position near the right edge
        if self.rect.left > self.target_x:
            self.rect.x -= max(1, int(self.speed))
        # Vertical bob, clamped on screen
        bob = int(80 * math.sin(self.t * 0.0013))
        self.rect.centery = max(
            self.rect.height // 2,
            min(HEIGHT - self.rect.height // 2, self.base_y + bob),
        )
        self.flash = max(0, self.flash - dt)

    def damage(self):
        self.hp -= 1
        self.flash = 80
        if self.hp <= 0:
            self.dead = True
            return True
        return False

    def draw(self, surf):
        surf.blit(self.image, self.rect)

        # Wide health bar above the boss
        bar_w = self.rect.width
        bar_h = 7
        x = self.rect.x
        y = self.rect.y - 12
        pygame.draw.rect(surf, (50, 20, 30), (x, y, bar_w, bar_h))
        fill = int(bar_w * (self.hp / self.max_hp))
        pygame.draw.rect(surf, (255, 90, 120), (x, y, fill, bar_h))

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
        # Persistent across resets
        self.diff_cursor = 1       # index into DIFF_OPTIONS; 1 = "normal"
        self.options_cursor = 0    # 0 = music slider, 1 = sfx slider
        self.menu_cursor = 0       # 0 = Start Game, 1 = Options
        self.reset(to_menu=True)

    def reset(self, to_menu=False, lives=None):
        if lives is None:
            lives = LIVES_BY_DIFFICULTY[DIFF_OPTIONS[self.diff_cursor]]
        self.player = Player(lives=lives)
        self.bullets = []
        self.enemies = []
        self.explosions = []

        self.score = 0
        self.total_spawned = 0
        self.special_count = 0   # counts special waves; even/odd alternates train vs big
        self.boss_active = False  # True while a boss is on screen
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
        lives = LIVES_BY_DIFFICULTY[DIFF_OPTIONS[self.diff_cursor]]
        self.reset(to_menu=False, lives=lives)

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

        # A boss takes priority over the regular special wave on its frames,
        # and only one boss may be on screen at a time.
        if self.total_spawned % BOSS_EVERY == 0 and not self.boss_active:
            self.boss_active = True
            self.enemies.append(Boss(self.enemy_speed))
        # Every TRAIN_EVERY spawns a special wave appears; trains and big
        # enemies strictly alternate (train, big, train, big, ...).
        elif self.total_spawned % TRAIN_EVERY == 0:
            self.special_count += 1
            if self.special_count % 2 == 1:
                self._spawn_train()
            else:
                self.enemies.append(Enemy(self.enemy_speed, big=True))
        else:
            self.enemies.append(Enemy(self.enemy_speed, big=False))

    def _spawn_train(self):
        count = max(2, int(self.enemy_speed))
        start_x = WIDTH + 60
        center_y = random.randrange(
            int(HEIGHT * 0.25), int(HEIGHT * 0.75)
        )
        train_speed = self.enemy_speed * 0.9
        for i in range(count):
            self.enemies.append(
                TrainEnemy(i, train_speed, start_x, center_y)
            )

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
                        if getattr(enemy, "is_boss", False):
                            self.boss_active = False
                            self._boss_death_fx(enemy)
                        else:
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
                    # Ramming the boss hurts the player but does not kill it.
                    if not getattr(enemy, "is_boss", False):
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

    def _boss_death_fx(self, boss):
        """A burst of explosions and a strong shake when the boss goes down."""
        cx, cy = boss.rect.center
        self.explosions.append(Explosion((cx, cy)))
        for _ in range(8):
            ox = random.randint(-boss.rect.width // 2, boss.rect.width // 2)
            oy = random.randint(-boss.rect.height // 2, boss.rect.height // 2)
            self.explosions.append(Explosion((cx + ox, cy + oy)))
        self.screen_shake = 600

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

        x, y = 14, 10

        # Score line
        for text_str, color in [
            (f"SCORE {self.score:07d}", (120, 255, 160)),
        ]:
            shadow = font.render(text_str, False, (0, 0, 0))
            text = font.render(text_str, False, color)
            surf.blit(shadow, (x + 2, y + 2))
            surf.blit(text, (x, y))
            y += 23

        # Ship icons (one per remaining life)
        icon = pygame.transform.scale(ASSETS["player"][0], (30, 20))
        for i in range(self.player.lives):
            surf.blit(icon, (x + i * 35, y))
        y += 26

        # Remaining HUD lines
        for text_str, color in [
            (f"SPAWNED {self.total_spawned}", (120, 255, 160)),
            (f"ENEMY SPD {self.enemy_speed:.2f}", (120, 255, 160)),
        ]:
            shadow = font.render(text_str, False, (0, 0, 0))
            text = font.render(text_str, False, color)
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

        menu_items = ["START GAME", "OPTIONS"]
        item_gap = 48
        ship_icon = pygame.transform.scale(ASSETS["player"][0], (32, 22))
        icon_gap = 12  # space between ship icon and text

        # Pre-render labels to measure widths
        rendered = [font.render(label, False, (255, 255, 255)) for label in menu_items]
        max_txt_w = max(r.get_width() for r in rendered)

        # Total block width = ship icon + gap + widest text; center the block
        block_w = ship_icon.get_width() + icon_gap + max_txt_w
        block_left = WIDTH // 2 - block_w // 2
        text_left  = block_left + ship_icon.get_width() + icon_gap

        # Place menu below the logo with a fixed gap, never overlapping it
        logo_h = self.title_logo.get_height() if self.title_logo else 80
        item_y_start = target_y + logo_h + 36

        for i, (label, base_surf) in enumerate(zip(menu_items, rendered)):
            item_y = item_y_start + i * item_gap
            selected = (i == self.menu_cursor)
            color = (255, 230, 80) if selected else (130, 150, 180)
            txt = font.render(label, False, color)
            surf.blit(txt, (text_left, item_y - txt.get_height() // 2))

            if selected:
                sy = item_y - ship_icon.get_height() // 2
                surf.blit(ship_icon, (block_left, sy))

        controls = small.render("UP / DOWN  SELECT     ENTER  CONFIRM     ESC  QUIT", False, (120, 130, 160))
        surf.blit(controls, controls.get_rect(center=(WIDTH // 2, HEIGHT - 28)))

    def draw_difficulty(self, surf):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surf.blit(overlay, (0, 0))

        title_font = pygame.font.SysFont("consolas,dejavusansmono,couriernew", 38, bold=True)
        font = pygame.font.SysFont("consolas,dejavusansmono,couriernew", 26)
        small = pygame.font.SysFont("consolas,dejavusansmono,couriernew", 18)

        title = title_font.render("SELECT DIFFICULTY", False, (120, 210, 255))
        surf.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 100)))

        labels = ["EASY", "NORMAL", "HARD"]
        ships  = [5, 3, 1]
        colors_sel   = [(80, 255, 120), (255, 230, 80), (255, 80, 80)]
        colors_unsel = [(60, 120, 70),  (120, 100, 40), (120, 40, 40)]

        col_gap = 210
        base_x = WIDTH // 2 - col_gap
        y_label = HEIGHT // 2 - 10
        y_ships = HEIGHT // 2 + 38

        box_pad_x, box_pad_y = 22, 16
        icon = pygame.transform.scale(ASSETS["player"][0], (24, 16))

        for i, (label, n_ships) in enumerate(zip(labels, ships)):
            cx = base_x + i * col_gap
            selected = (i == self.diff_cursor)
            color = colors_sel[i] if selected else colors_unsel[i]

            txt = font.render(label, False, color)
            surf.blit(txt, txt.get_rect(center=(cx, y_label)))

            # mini ship icons
            total_w = n_ships * 28 - 4  # last gap removed
            ix = cx - total_w // 2
            for _ in range(n_ships):
                surf.blit(icon, (ix, y_ships))
                ix += 28

            if selected:
                # box encompassing label + ship icons
                content_top    = y_label - txt.get_height() // 2 - box_pad_y
                content_bottom = y_ships + icon.get_height() + box_pad_y
                content_left   = cx - max(txt.get_width(), total_w) // 2 - box_pad_x
                content_right  = cx + max(txt.get_width(), total_w) // 2 + box_pad_x
                box_rect = pygame.Rect(
                    content_left, content_top,
                    content_right - content_left,
                    content_bottom - content_top,
                )
                pygame.draw.rect(surf, color, box_rect, 2)

        hint = small.render("LEFT / RIGHT  SELECT     ENTER  CONFIRM     ESC  BACK", False, (150, 150, 180))
        surf.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 110)))

    def draw_options(self, surf):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surf.blit(overlay, (0, 0))

        title_font = pygame.font.SysFont("consolas,dejavusansmono,couriernew", 38, bold=True)
        font = pygame.font.SysFont("consolas,dejavusansmono,couriernew", 20)
        small = pygame.font.SysFont("consolas,dejavusansmono,couriernew", 16)

        title = title_font.render("OPTIONS", False, (120, 210, 255))
        surf.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 110)))

        sliders = [
            ("MUSIC VOLUME", VOL["music"]),
            ("SFX VOLUME",   VOL["sfx"]),
        ]
        bar_w, bar_h = 300, 16
        row_h = 72   # vertical space per slider (label + gap + bar)

        for i, (label, vol) in enumerate(sliders):
            # centre of this slider block
            block_cy = HEIGHT // 2 - 20 + i * row_h
            label_y  = block_cy - 14   # top of label text
            bar_y    = block_cy + 12   # top of bar

            selected = (i == self.options_cursor)
            col = (255, 230, 80) if selected else (150, 150, 180)

            # label centered above the bar
            lbl = font.render(label, False, col)
            surf.blit(lbl, lbl.get_rect(centerx=WIDTH // 2, y=label_y))

            # bar centered on screen
            bar_x = WIDTH // 2 - bar_w // 2
            pygame.draw.rect(surf, (40, 40, 60), (bar_x, bar_y, bar_w, bar_h))
            fill = int(bar_w * vol)
            fill_col = (80, 220, 120) if selected else (60, 130, 80)
            if fill > 0:
                pygame.draw.rect(surf, fill_col, (bar_x, bar_y, fill, bar_h))
            pygame.draw.rect(surf, col, (bar_x, bar_y, bar_w, bar_h), 2)

            # percentage to the right of bar
            pct = small.render(f"{int(vol * 100)}%", False, col)
            surf.blit(pct, (bar_x + bar_w + 10, bar_y + bar_h // 2 - pct.get_height() // 2))

        hint = small.render("UP / DOWN  SELECT SLIDER     LEFT / RIGHT  ADJUST     ESC  BACK", False, (130, 130, 160))
        surf.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 110)))

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
        menu = font.render("PRESS M FOR MENU", False, (180, 210, 255))

        surf.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 80)))
        surf.blit(score, score.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 20)))
        surf.blit(spawned, spawned.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 18)))
        surf.blit(restart, restart.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 70)))
        surf.blit(menu, menu.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 106)))

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

        elif self.state == "difficulty":
            self.draw_difficulty(world)

        elif self.state == "options":
            self.draw_options(world)

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
                if game.state == "menu":
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        game.menu_cursor = (game.menu_cursor - 1) % 2
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        game.menu_cursor = (game.menu_cursor + 1) % 2
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        if game.menu_cursor == 0:
                            game.state = "difficulty"
                        else:
                            game.state = "options"

                elif game.state == "difficulty":
                    if event.key == pygame.K_ESCAPE:
                        game.state = "menu"
                    elif event.key in (pygame.K_LEFT, pygame.K_a):
                        game.diff_cursor = (game.diff_cursor - 1) % len(DIFF_OPTIONS)
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        game.diff_cursor = (game.diff_cursor + 1) % len(DIFF_OPTIONS)
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        game.start_game()

                elif game.state == "options":
                    if event.key == pygame.K_ESCAPE:
                        game.state = "menu"
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        game.options_cursor = (game.options_cursor - 1) % 2
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        game.options_cursor = (game.options_cursor + 1) % 2
                    elif event.key in (pygame.K_LEFT, pygame.K_a):
                        if game.options_cursor == 0:
                            VOL["music"] = max(0.0, round(VOL["music"] - 0.05, 2))
                            pygame.mixer.music.set_volume(VOL["music"])
                        else:
                            VOL["sfx"] = max(0.0, round(VOL["sfx"] - 0.05, 2))
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        if game.options_cursor == 0:
                            VOL["music"] = min(1.0, round(VOL["music"] + 0.05, 2))
                            pygame.mixer.music.set_volume(VOL["music"])
                        else:
                            VOL["sfx"] = min(1.0, round(VOL["sfx"] + 0.05, 2))

                elif game.state == "game_over":
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_r:
                        game.start_game()
                    elif event.key == pygame.K_m:
                        game.reset(to_menu=True)

                elif game.state == "playing":
                    if event.key == pygame.K_ESCAPE:
                        game.reset(to_menu=True)
                    elif event.key == pygame.K_SPACE:
                        game.fire()

        game.update(dt)
        game.draw(screen)
        pygame.display.flip()

    pygame.mixer.music.stop()
    pygame.quit()


if __name__ == "__main__":
    main()