# Aimer 8

**Aimer 8** is a 16-bit style side-scrolling space shooter built with **Python** and **Pygame**.

Pilot a pixel-art spaceship, blast through increasingly dangerous enemy waves, defeat bosses to advance levels, collect powerups, and survive as long as you can.

## Screenshots

### Main Menu
![Main Menu](screenshot_main.png)

### Difficulty Selection
![Difficulty Selection](screenshot_difficulty.png)

### Options
![Options](screenshot_options.png)

### Gameplay
![Gameplay](screenshot_game.png)

## Features

- 16-bit / Super Nintendo inspired pixel-art visual style
- Side-scrolling shooter gameplay
- **Difficulty selection**: Easy (5 ships), Normal (3 ships), Hard (1 ship)
- **Options menu**: adjustable music and SFX volume sliders, fullscreen toggle
- **Fullscreen mode** — letterbox-scaled to any display resolution
- Two-frame animated player ship
- Player movement with **WASD** or **Arrow Keys**
- Laser shooting with **Spacebar**
- Procedurally generated retro laser and explosion sound effects
- Background music support:
  - `audio/main.mp3` — main menu and game-over screen
  - `audio/levelNN.mp3` — per-level tracks, falls back to `level01.mp3` if not found
  - `audio/level_clear.mp3` — short jingle played on boss defeat
  - `audio/spooling.mp3` — engine spool-up during the launch cutscene
- **Hangar launch cutscene** at game start (skippable with Space/Enter)
- Starfield background with parallax scrolling
- **Per-level scrolling background images** (tiled, alpha-transparent, faster parallax layer):
  - `gfx/backgroundNNbottom.png` — terrain strip anchored to the bottom of the screen
  - `gfx/backgroundNNtop.png` — optional sky strip anchored to the top of the screen
  - Missing images are silently ignored; any level can have zero, one, or both layers
- Distant planets, nebulae, and space station background elements (seeded, deterministic order)
- 8 different enemy ship sprites, picked at random
- Enemy progression:
  - Normal enemies spawn from the right
  - Every **15 spawns** — a special wave: **enemy trains** and **large armored enemies** alternate
  - Sinusoidal **enemy train** formation, up to **6 ships**, count grows with speed
  - **Large armored enemy** takes 5 hits to destroy
  - Every **90 spawns** — enemy speed increases
- **Enemy return fire** (from Level 2 onward):
  - Every enemy ship fires back once every **5 seconds ÷ level number**
  - First shot fires 0.5 seconds after the ship enters the screen
  - Bullet speed is never slower than the ship that fired it
- **Boss monster** every **60 spawns**:
  - All other spawns pause until the boss is destroyed
  - Glides in, hovers and bobs, and takes 40 hits (with a health bar)
  - Attacks with a leftward fan of bullets; the pattern is **seeded and learnable**
  - Cannot be killed by ramming — contact (and its bullets) cost the player a life
  - Destroying it awards **+1 extra life**, a big score bonus, and triggers **Level Clear**
- **Level Clear sequence** on boss defeat:
  - Music stops; the level-clear jingle plays
  - Player ship accelerates off the right edge; **LEVEL X CLEAR!** is displayed
  - Screen fades to black, then fades into the next level
  - Score, lives, active powerup, and enemy speed carry over
  - Space/Enter skips the sequence; ESC returns to the main menu
- **Powerup system** — a powerup spawns every **10 000 points**:
  - **Triple Beam** — fires 3 vertically stacked lasers per shot
  - **Spread** — fires forward + straight up + straight down simultaneously
  - **Missiles** — homing missiles that auto-aim the closest living enemy
  - **Extra Life** — grants +1 life instantly
  - Collecting a new powerup replaces the previous one (extra life is always instant)
  - The active powerup type is never repeated as the next spawn
  - Active powerup shown as icon + label in the top-right HUD
- HUD displays: current **level**, score, remaining lives (ship icons), and active powerup
- Player blink and invulnerability after taking damage
- **2-second death delay** — gameplay continues for 2 seconds after the last life is lost
- Screen shake on collision
- **Game over screen** with `gfx/gameover.png` image and a navigable menu (Restart / Main Menu / Exit Game)

## Screens and Assets

The game expects the following project structure:

```text
Aimer-8/
  main.py
  README.md
  aimer8.spec
  create_icon.py
  gfx/
    sprites.png
    title.png
    gameover.png
    font.otf
    icon.ico
    icon.png
    background01bottom.png   ← optional, level 1 terrain
    background02bottom.png   ← optional, level 2 terrain
    background03bottom.png   ← optional
    background03top.png      ← optional, level 3 sky layer
    ...
  audio/
    main.mp3
    level01.mp3
    level02.mp3              ← optional, falls back to level01
    level_clear.mp3
    spooling.mp3
```

### Required graphics

Place these files in the `gfx/` folder:

- `sprites.png` — sprite sheet (1254×1554, RGBA) containing player frames, enemy ships, boss, explosions, projectiles, planets, nebulae, space station, and 4 powerup icons.
- `title.png` — main logo for the title screen (chroma-keyed on solid green `#00FF00`).
- `gameover.png` — game over image shown on the game over screen (chroma-keyed on solid green `#00FF00`).
- `font.otf` — custom bitmap/pixel font used for all in-game text; falls back to Consolas/monospace if missing.
- `icon.ico` / `icon.png` — window and taskbar icon (generated by `create_icon.py`).

### Optional per-level backgrounds

Files named `gfx/backgroundNNbottom.png` and `gfx/backgroundNNtop.png` (e.g. `background02bottom.png`) are loaded for the corresponding level. They must be RGBA PNGs — the alpha channel lets the starfield show through. Each image is scaled to 50% of its source size on load and tiled horizontally across the screen.

### Required audio

Place these files in the `audio/` folder:

- `main.mp3` — loops during the main menu and game-over screen.
- `level01.mp3` — loops during gameplay; used as fallback for any level without its own track.
- `level_clear.mp3` — played once when the boss is defeated.
- `spooling.mp3` — one-shot engine spool-up played during the launch cutscene.

Additional level tracks (`level02.mp3`, `level03.mp3`, …) are loaded if present; missing tracks silently fall back to `level01.mp3`.

Sound effects for lasers and explosions are generated in code; no external SFX files are required beyond the above.

## Installation

Install Python 3.10+ and the required packages:

```bash
pip install pygame pillow
```

## Running the Game

```bash
python main.py
```

## Windows Executable

```bash
# Generate the icon (requires Pillow)
python create_icon.py

# Build the executable (requires PyInstaller)
pip install pyinstaller
pyinstaller aimer8.spec
```

The compiled binary will appear in `dist/Aimer8.exe`.

## Controls

| Action | Keys |
|---|---|
| Move | WASD or Arrow Keys |
| Fire | Spacebar |
| Navigate menus | Arrow Keys / WASD |
| Confirm / Select | Enter |
| Back / Quit | Escape |
| Skip cutscene / level clear | Space or Enter |

## Gameplay Rules

- Destroy enemies to increase your score.
- Normal enemies are destroyed with **1 hit** (100 pts).
- Every **15 spawns** a special wave enters, alternating between two types:
  - **Train formation** — up to 6 ships travel in a sinusoidal wave pattern (150 pts each).
  - **Large enemy** — takes **5 hits** (700 pts).
- Every **60 spawns** a **boss monster** appears (3 000 pts):
  - All other spawns pause until the boss is destroyed.
  - Takes **40 hits** and fires a learnable, fixed bullet-fan pattern.
  - Ramming it or being hit by its bullets costs a life; cannot be killed by ramming.
  - Destroying the boss grants **+1 extra life** and starts the **Level Clear** sequence.
- Every **90 enemies**, all enemy speeds increase.
- From **Level 2** onward, enemy ships fire back. Fire rate = one shot every **5 000 ms ÷ level** (e.g. every 2.5 s on level 2, every 1 s on level 5).
- Every **10 000 points** a **powerup** floats in from the right — fly into it to collect it.
- Colliding with an enemy or a boss bullet removes one ship (life).
- When the last life is lost, gameplay continues for **2 seconds** before the game over screen appears.
- The game over screen offers **Restart**, **Main Menu**, or **Exit Game**.

## Powerups

| Icon | Name | Effect |
|------|------|--------|
| Triple Beam | Triple Beam | 3 vertically stacked lasers per shot |
| Spread | Spread Shot | Forward + straight up + straight down |
| Missiles | Missiles | Homing missiles, auto-aim closest enemy |
| 1UP | Extra Life | +1 life instantly |

A new powerup will never be the same type as the one currently active.

## Difficulty

| Difficulty | Starting ships |
|---|---|
| Easy | 5 |
| Normal | 3 |
| Hard | 1 |

## Configuration

Most gameplay values can be edited near the top of `main.py`:

```python
WIDTH, HEIGHT = 960, 540
FPS = 60

PLAYER_SPEED = 5.0
BULLET_SPEED = 10.0
FIRE_COOLDOWN = 170  # ms between shots

BASE_ENEMY_SPEED = 3.0
SPEED_INCREASE_EVERY = 90
TRAIN_EVERY = 15

BOSS_EVERY = 60
BOSS_HP = 40
BOSS_FIRE_MS = 950
BOSS_VOLLEY = 9
BOSS_SPREAD = 72
BOSS_BULLET_SPEED = 4.4
BOSS_SEED = 20250625

VOL = {"music": 0.45, "sfx": 0.5}
```

## AI-Generated Code and Asset Disclaimer

This project was created with assistance from AI tools. Portions of the source code, game structure, generated sound logic, sprite-sheet planning, and visual asset prompts were produced or refined using AI assistance.

The code and assets should be reviewed, tested, and modified as needed before being used in a production or commercial project.

No warranty is provided. Use this project at your own discretion.

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

## Credits

- Game concept, implementation direction, and project assembly: Pascal Brax
- Code assistance and asset-generation support:
  - GFX & code: ChatGPT, Claude
  - Music: Suno
- Built with Python and Pygame
