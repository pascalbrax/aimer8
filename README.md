# Aimer 8

**Aimer 8** is a simple 16-bit style side-scrolling space shooter built with **Python** and **Pygame**.

Pilot a small pixel-art spaceship, dodge incoming enemies, fire retro laser shots, survive increasingly difficult waves, and fight larger enemies every 30 spawns.

## Features

- 16-bit / Super Nintendo inspired pixel-art visual style
- Side-scrolling shooter gameplay
- Player movement with **WASD** or **Arrow Keys**
- Laser shooting with **Spacebar**
- Procedurally generated retro laser and explosion sound effects
- Background music support:
  - `audio/main.mp3` for the main menu and game-over screen
  - `audio/level.mp3` for gameplay
- Starfield background with parallax scrolling
- Distant planets, nebulae, and space station background elements
- Enemy progression:
  - Normal enemies spawn from the right side of the screen
  - Every 30 spawned enemies, a larger enemy appears
  - Larger enemies require 5 hits to destroy
  - Every 90 spawned enemies, enemy speed increases
- Score, lives, enemies spawned, and enemy speed UI
- Player blink effect after damage
- Screen shake on player collision
- Game-over screen with restart support
- Animated title logo on the main menu

## Screens and Assets

<img width="957" height="527" alt="screenshot_main" src="https://github.com/user-attachments/assets/105ce862-9fc5-4370-b81b-7f82888404ff" />

<img width="951" height="531" alt="screenshot_game" src="https://github.com/user-attachments/assets/acec21dd-593a-4ba2-b1bd-a34801b3b010" />


The game expects the following project structure:

```text
Aimer-8/
  main.py
  README.md
  gfx/
    gsprites.png
    title.png
  audio/
    main.mp3
    level.mp3
```

### Required graphics

Place these files in the `gfx/` folder:

- `gsprites.png` — sprite sheet containing ships, enemies, explosions, projectiles, planets, nebulae, and space station art.
- `title.png` — main logo for the title screen.

Both images should use solid green `#00FF00` as the chroma-key background color so the game can remove it in-game.

### Required audio

Place these files in the `audio/` folder:

- `main.mp3` — loops during the main menu and game-over screen.
- `level.mp3` — loops during gameplay.

Sound effects for lasers and explosions are generated in code, so no external sound-effect files are required.

## Installation

Install Python 3 and Pygame.

```bash
pip install pygame
```

## Running the Game

From the project folder, run:

```bash
python main.py
```

## Controls

| Action | Keys |
|---|---|
| Move | WASD or Arrow Keys |
| Fire | Spacebar |
| Start Game | Enter |
| Restart After Game Over | R |
| Quit | Escape |

## Gameplay Rules

- Destroy enemies to increase your score.
- Normal enemies are destroyed with 1 hit.
- Larger enemies appear every 30 enemies spawned.
- Larger enemies take 5 hits to destroy and award more points.
- Enemy speed increases every 90 enemies spawned.
- Colliding with an enemy removes one life.
- The game ends when lives reach zero.

## Configuration

Most gameplay values can be edited near the top of `main.py`, including:

```python
WIDTH, HEIGHT = 960, 540
FPS = 60

PLAYER_SPEED = 5.0
BULLET_SPEED = 10.0
FIRE_COOLDOWN = 170

START_LIVES = 3
BASE_ENEMY_SPEED = 2.0
SPEED_INCREASE_EVERY = 90
BIG_ENEMY_EVERY = 30
```

## Notes About Generated Assets

The sprite sheet and logo are designed for a retro 16-bit style. The game uses chroma-key removal for green `#00FF00`, so avoid using that exact green color inside visible sprite artwork unless it is meant to become transparent.

## AI-Generated Code and Asset Disclaimer

This project was created with assistance from AI tools. Portions of the source code, game structure, generated sound logic, sprite-sheet planning, and visual asset prompts were produced or refined using AI assistance.

The code and assets should be reviewed, tested, and modified as needed before being used in a production or commercial project. AI-generated output may contain mistakes, inefficient code, unintentional similarities, or licensing concerns depending on how generated assets are created and used.

No warranty is provided. Use this project at your own discretion.

## License

No license has been selected yet.

Before publishing or distributing this repository, choose a license such as MIT, Apache-2.0, GPL, or another license that fits your intended use.

## Credits

- Game concept, implementation direction, and project assembly: Pascal Brax
- Code assistance and asset-generation support:
  - GFX & code: ChatGPT
  - Music: Suno
- Built with Python and Pygame
