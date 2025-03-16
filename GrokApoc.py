import pygame
import math
import random
import json
import os
import sys

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH, SCREEN_HEIGHT = pygame.display.Info().current_w, pygame.display.Info().current_h
WHITE, BLACK, GRAY, DARK_GRAY = (255, 255, 255), (0, 0, 0), (50, 50, 50), (20, 20, 20)
RED, PURPLE = (200, 0, 0), (100, 0, 200)
BUTTON_COLOR, HOVER_COLOR, TEXT_COLOR = (100, 100, 100), (150, 150, 150), (255, 255, 255)
INFECTED_COLOR, BULLET_COLOR = (0, 255, 0), (255, 0, 0)
SURVIVOR_COLORS = [(0, 0, 255), (128, 0, 128), (255, 0, 0), (255, 255, 0), (0, 255, 255)]
GROUND_COLOR = (80, 40, 20)
BORDER_WIDTH = 50
PLAYABLE_LEFT, PLAYABLE_RIGHT = BORDER_WIDTH, SCREEN_WIDTH - BORDER_WIDTH
PLAYABLE_TOP, PLAYABLE_BOTTOM = BORDER_WIDTH, SCREEN_HEIGHT - BORDER_WIDTH
INFECTED_ATTACK_RADIUS = 50

# Default Game Settings
DEFAULT_SETTINGS = {
    "player_size": 20,
    "survivor_speed": 5,
    "infected_speed": 7,
    "bullet_speed": 10,
    "action_cooldown": 1.0,
    "ai_difficulty": 1,  # 1=Easy, 2=Medium, 3=Hard
}

# Load settings
SETTINGS_FILE = "game_settings.json"
game_settings = DEFAULT_SETTINGS.copy()
if os.path.exists(SETTINGS_FILE):
    try:
        with open(SETTINGS_FILE, "r") as f:
            loaded_settings = json.load(f)
            game_settings.update(loaded_settings)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Failed to load {SETTINGS_FILE} ({e}). Using defaults.")

# Screen setup
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Apoca")

# Fonts and Resources
font, small_font, name_font = pygame.font.Font(None, 50), pygame.font.Font(None, 36), pygame.font.Font(None, 30)
radius_surface = pygame.Surface((INFECTED_ATTACK_RADIUS * 2, INFECTED_ATTACK_RADIUS * 2), pygame.SRCALPHA)
pygame.draw.circle(radius_surface, (255, 165, 0, 100), (INFECTED_ATTACK_RADIUS, INFECTED_ATTACK_RADIUS), INFECTED_ATTACK_RADIUS)

# Spawn Points
spawn_points = [
    [PLAYABLE_LEFT + 50, PLAYABLE_TOP + 50], [PLAYABLE_RIGHT - 50, PLAYABLE_TOP + 50],
    [PLAYABLE_LEFT + 50, PLAYABLE_BOTTOM - 50], [PLAYABLE_RIGHT - 50, PLAYABLE_BOTTOM - 50],
    [SCREEN_WIDTH // 2, PLAYABLE_TOP + 50], [SCREEN_WIDTH // 2, PLAYABLE_BOTTOM - 50],
    [PLAYABLE_LEFT + 50, SCREEN_HEIGHT // 2], [PLAYABLE_RIGHT - 50, SCREEN_HEIGHT // 2],
]

# Building Generation
def is_point_in_safe_zone(x, y, spawn_points, safe_radius=100):
    for sp in spawn_points:
        if math.sqrt((x - sp[0])**2 + (y - sp[1])**2) < safe_radius:
            return True
    return False

def flood_fill(grid, start_x, start_y, width, height):
    visited = set()
    stack = [(start_x, start_y)]
    while stack:
        x, y = stack.pop()
        if (x, y) in visited or x < 0 or x >= width or y < 0 or y >= height or grid[y][x]:
            continue
        visited.add((x, y))
        stack.extend([(x+1, y), (x-1, y), (x, y+1), (x, y-1)])
    return visited

def generate_buildings():
    buildings = []
    safe_radius = 100
    for _ in range(8):
        while True:
            x = random.randint(PLAYABLE_LEFT + 50, PLAYABLE_RIGHT - 50)
            y = random.randint(PLAYABLE_TOP + 50, PLAYABLE_BOTTOM - 50)
            width = random.randint(100, 300)
            height = random.randint(100, 300)
            new_wall = pygame.Rect(x, y, width, height)
            if not is_point_in_safe_zone(x, y, spawn_points, safe_radius):
                buildings.append(new_wall)
                break
    for _ in range(15):
        while True:
            x = random.randint(PLAYABLE_LEFT + 50, PLAYABLE_RIGHT - 50)
            y = random.randint(PLAYABLE_TOP + 50, PLAYABLE_BOTTOM - 50)
            width = random.randint(50, 150)
            height = random.randint(50, 150)
            new_wall = pygame.Rect(x, y, width, height)
            if not is_point_in_safe_zone(x, y, spawn_points, safe_radius) and sum(new_wall.colliderect(b) for b in buildings) < 2:
                buildings.append(new_wall)
                break
    grid_width = (PLAYABLE_RIGHT - PLAYABLE_LEFT) // 10
    grid_height = (PLAYABLE_BOTTOM - PLAYABLE_TOP) // 10
    grid = [[0 for _ in range(grid_width)] for _ in range(grid_height)]
    for building in buildings:
        grid_x_start = max(0, (building.x - PLAYABLE_LEFT) // 10)
        grid_x_end = min(grid_width, (building.x + building.width - PLAYABLE_LEFT) // 10)
        grid_y_start = max(0, (building.y - PLAYABLE_TOP) // 10)
        grid_y_end = min(grid_height, (building.y + building.height - PLAYABLE_TOP) // 10)
        for y in range(grid_y_start, grid_y_end):
            for x in range(grid_x_start, grid_x_end):
                grid[y][x] = 1
    center_x, center_y = grid_width // 2, grid_height // 2
    reachable = flood_fill(grid, center_x, center_y, grid_width, grid_height)
    for sp in spawn_points:
        grid_x = (sp[0] - PLAYABLE_LEFT) // 10
        grid_y = (sp[1] - PLAYABLE_TOP) // 10
        if (grid_x, grid_y) not in reachable:
            for i, building in enumerate(buildings[:]):
                if pygame.Rect(sp[0] - 50, sp[1] - 50, 100, 100).colliderect(building):
                    buildings.pop(i)
                    grid = [[0 for _ in range(grid_width)] for _ in range(grid_height)]
                    for b in buildings:
                        gx_start = max(0, (b.x - PLAYABLE_LEFT) // 10)
                        gx_end = min(grid_width, (b.x + b.width - PLAYABLE_LEFT) // 10)
                        gy_start = max(0, (b.y - PLAYABLE_TOP) // 10)
                        gy_end = min(grid_height, (b.y + b.height - PLAYABLE_TOP) // 10)
                        for y in range(gy_start, gy_end):
                            for x in range(gx_start, gx_end):
                                grid[y][x] = 1
                    reachable = flood_fill(grid, center_x, center_y, grid_width, grid_height)
                    break
    return buildings

buildings = generate_buildings()

# Controls and Skins
CONTROLS_FILE = "controls.json"
if os.path.exists(CONTROLS_FILE):
    with open(CONTROLS_FILE, "r") as f:
        control_schemes = json.load(f)
else:
    control_schemes = [
        {"left": pygame.K_LEFT, "right": pygame.K_RIGHT, "up": pygame.K_UP, "down": pygame.K_DOWN, "action": pygame.K_SPACE, "name": "P1"},
        {"left": pygame.K_j, "right": pygame.K_l, "up": pygame.K_i, "down": pygame.K_k, "action": pygame.K_m, "name": "P2"},
        {"left": pygame.K_t, "right": pygame.K_y, "up": pygame.K_g, "down": pygame.K_h, "action": pygame.K_b, "name": "P3"},
        {"left": pygame.K_KP4, "right": pygame.K_KP6, "up": pygame.K_KP8, "down": pygame.K_KP2, "action": pygame.K_KP0, "name": "P4"},
        {"left": pygame.K_a, "right": pygame.K_d, "up": pygame.K_w, "down": pygame.K_s, "action": pygame.K_e, "name": "P5"},
    ]

SKINS_FILE = "skins.json"
player_skins = SURVIVOR_COLORS[:len(control_schemes)]
if os.path.exists(SKINS_FILE):
    with open(SKINS_FILE, "r") as f:
        player_skins = json.load(f)

# UI Functions
def draw_gradient_background(surface, color1, color2):
    for y in range(SCREEN_HEIGHT):
        r = int(color1[0] + (color2[0] - color1[0]) * y / SCREEN_HEIGHT)
        g = int(color1[1] + (color2[1] - color1[1]) * y / SCREEN_HEIGHT)
        b = int(color1[2] + (color2[2] - color1[2]) * y / SCREEN_HEIGHT)
        pygame.draw.line(surface, (r, g, b), (0, y), (SCREEN_WIDTH, y))

def draw_button(surface, text, x, y, width, height, selected=False, hovered=False, border_color=WHITE):
    color = HOVER_COLOR if hovered else (BUTTON_COLOR if not selected else DARK_GRAY)
    pygame.draw.rect(surface, color, (x, y, width, height))
    pygame.draw.rect(surface, border_color, (x, y, width, height), 2)
    label = small_font.render(text, True, TEXT_COLOR)
    surface.blit(label, label.get_rect(center=(x + width // 2, y + height // 2)))

def draw_title(surface, text, x, y):
    glow = font.render(text, True, (255, 100, 100))
    surface.blit(glow, (x - 2, y - 2))
    surface.blit(glow, (x + 2, y + 2))
    title = font.render(text, True, WHITE)
    surface.blit(title, (x, y))

def show_controls():
    global control_schemes
    selected = None
    scroll_offset = 0
    max_offset = max(0, len(control_schemes) * 220 - SCREEN_HEIGHT + 200)
    while True:
        draw_gradient_background(screen, RED, PURPLE)
        draw_title(screen, "Controls", SCREEN_WIDTH // 2 - 100, 50)
        mouse_pos = pygame.mouse.get_pos()
        y = 150 - scroll_offset
        rects = []
        for i, scheme in enumerate(control_schemes):
            for key in ["left", "right", "up", "down", "action"]:
                if y >= 50 and y <= SCREEN_HEIGHT - 40:
                    text = f"{scheme['name']} {key.capitalize()}: {pygame.key.name(scheme[key]).upper()}"
                    label = small_font.render(text, True, WHITE)
                    rect = label.get_rect(topleft=(SCREEN_WIDTH // 4, y))
                    rects.append((rect, i, key))
                    screen.blit(label, rect)
                    if rect.collidepoint(mouse_pos):
                        pygame.draw.rect(screen, HOVER_COLOR, rect, 2)
                        if selected == (i, key):
                            pygame.draw.rect(screen, RED, rect, 2)
                y += 40
            y += 20
        scrollbar_height = SCREEN_HEIGHT * SCREEN_HEIGHT // (max_offset + SCREEN_HEIGHT)
        scrollbar_y = (scroll_offset / max_offset) * (SCREEN_HEIGHT - scrollbar_height) if max_offset > 0 else 0
        pygame.draw.rect(screen, GRAY, (SCREEN_WIDTH - 20, scrollbar_y, 10, scrollbar_height))
        draw_button(screen, "Back", SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT - 100, 300, 60, hovered=(SCREEN_WIDTH // 2 - 150 <= mouse_pos[0] <= SCREEN_WIDTH // 2 + 150 and SCREEN_HEIGHT - 100 <= mouse_pos[1] <= SCREEN_HEIGHT - 40))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                with open(CONTROLS_FILE, "w") as f:
                    json.dump(control_schemes, f)
                return
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    for rect, i, key in rects:
                        if rect.collidepoint(event.pos):
                            selected = (i, key)
                    if SCREEN_WIDTH // 2 - 150 <= event.pos[0] <= SCREEN_WIDTH // 2 + 150 and SCREEN_HEIGHT - 100 <= event.pos[1] <= SCREEN_HEIGHT - 40:
                        with open(CONTROLS_FILE, "w") as f:
                            json.dump(control_schemes, f)
                        return
                elif event.button == 4:  # Scroll up
                    scroll_offset = max(0, scroll_offset - 20)
                elif event.button == 5:  # Scroll down
                    scroll_offset = min(max_offset, scroll_offset + 20)
            if event.type == pygame.KEYDOWN and selected:
                control_schemes[selected[0]][selected[1]] = event.key
                selected = None

def game_parameters_menu():
    global game_settings
    settings = game_settings.copy()  # Work with a copy to modify settings
    scroll_offset = 0
    option_height = 60  # Height of each option
    visible_height = SCREEN_HEIGHT - 200  # Space for title and back button
    max_offset = max(0, len(settings) * option_height - visible_height)  # Max scrollable distance

    while True:
        # Draw background and title
        draw_gradient_background(screen, RED, PURPLE)
        draw_title(screen, "Game Parameters", SCREEN_WIDTH // 2 - 150, 50)
        mouse_pos = pygame.mouse.get_pos()

        # Render visible options with adjustment controls
        y = 150 - scroll_offset
        rects = []
        for key in settings.keys():  # Iterate over keys to avoid duplicates
            if 100 <= y <= SCREEN_HEIGHT - 100:  # Only render if in visible area
                text = f"{key.replace('_', ' ').title()}: {settings[key]}{' (Easy/Med/Hard)' if key == 'ai_difficulty' else ''}"
                label = small_font.render(text, True, WHITE)
                screen.blit(label, (SCREEN_WIDTH // 2 - 250, y))
                minus_rect = pygame.Rect(SCREEN_WIDTH // 2 + 150, y, 30, 30)
                plus_rect = pygame.Rect(SCREEN_WIDTH // 2 + 190, y, 30, 30)
                pygame.draw.rect(screen, BUTTON_COLOR, minus_rect)
                pygame.draw.rect(screen, BUTTON_COLOR, plus_rect)
                screen.blit(small_font.render("-", True, WHITE), minus_rect.move(10, 5))
                screen.blit(small_font.render("+", True, WHITE), plus_rect.move(10, 5))
                rects.append((minus_rect, key, -1 if key == "ai_difficulty" else -0.5 if key == "action_cooldown" else -5 if key == "player_size" else -1))
                rects.append((plus_rect, key, 1 if key == "ai_difficulty" else 0.5 if key == "action_cooldown" else 5 if key == "player_size" else 1))
            y += option_height

        # Draw scrollbar if content exceeds visible area
        if max_offset > 0:
            scrollbar_height = visible_height * visible_height // (len(settings) * option_height)
            scrollbar_y = 100 + (scroll_offset / max_offset) * (visible_height - scrollbar_height)
            pygame.draw.rect(screen, GRAY, (SCREEN_WIDTH - 20, scrollbar_y, 10, scrollbar_height))

        # Draw back button
        draw_button(screen, "Back", SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT - 100, 300, 60,
                    hovered=(SCREEN_WIDTH // 2 - 150 <= mouse_pos[0] <= SCREEN_WIDTH // 2 + 150 and
                             SCREEN_HEIGHT - 100 <= mouse_pos[1] <= SCREEN_HEIGHT - 40))
        pygame.display.flip()

        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                # Save settings on exit
                game_settings.clear()
                game_settings.update(settings)
                try:
                    with open(SETTINGS_FILE, "w") as f:
                        json.dump(game_settings, f)
                    print("Settings saved successfully.")
                except IOError as e:
                    print(f"Error saving settings: {e}")
                return
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    for rect, key, delta in rects:
                        if rect.collidepoint(event.pos):
                            min_val = 1 if key in ["survivor_speed", "infected_speed", "bullet_speed", "ai_difficulty"] else 0 if key == "action_cooldown" else 10
                            max_val = 3 if key == "ai_difficulty" else 2 if key == "action_cooldown" else 200 if key == "player_size" else 20
                            settings[key] = max(min_val, min(max_val, settings[key] + delta))
                    if SCREEN_WIDTH // 2 - 150 <= event.pos[0] <= SCREEN_WIDTH // 2 + 150 and SCREEN_HEIGHT - 100 <= event.pos[1] <= SCREEN_HEIGHT - 40:
                        # Save settings when pressing "Back"
                        game_settings.clear()
                        game_settings.update(settings)
                        try:
                            with open(SETTINGS_FILE, "w") as f:
                                json.dump(game_settings, f)
                            print("Settings saved successfully.")
                        except IOError as e:
                            print(f"Error saving settings: {e}")
                        return
                elif event.button == 4:  # Scroll up
                    scroll_offset = max(0, scroll_offset - 20)
                elif event.button == 5:  # Scroll down
                    scroll_offset = min(max_offset, scroll_offset + 20)

def settings_menu():
    while True:
        draw_gradient_background(screen, RED, PURPLE)
        title_text = "Settings"
        title = font.render(title_text, True, WHITE)
        draw_title(screen, title_text, SCREEN_WIDTH // 2 - title.get_width() // 2, 50)
        mouse_pos = pygame.mouse.get_pos()
        buttons = [
            ("Game Parameters", 250, game_parameters_menu),
            ("Controls", 350, show_controls),
            ("Back", 450, None),
        ]
        for i, (text, y, action) in enumerate(buttons):
            draw_button(screen, text, SCREEN_WIDTH // 2 - 150, y, 300, 60, hovered=(SCREEN_WIDTH // 2 - 150 <= mouse_pos[0] <= SCREEN_WIDTH // 2 + 150 and y <= mouse_pos[1] <= y + 60), border_color=SURVIVOR_COLORS[i % len(SURVIVOR_COLORS)])
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                return
            if event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos
                for text, btn_y, action in buttons:
                    if SCREEN_WIDTH // 2 - 150 <= x <= SCREEN_WIDTH // 2 + 150 and btn_y <= y <= btn_y + 60:
                        if text == "Back":
                            return
                        if action:
                            action()

def skin_customization_menu():
    global player_skins
    skins = player_skins.copy()
    selected = 0
    while True:
        draw_gradient_background(screen, RED, PURPLE)
        draw_title(screen, "Skin Customization", SCREEN_WIDTH // 2 - 150, 50)
        mouse_pos = pygame.mouse.get_pos()
        y = 150
        for i in range(len(control_schemes)):
            draw_button(screen, f"Player {i+1}", SCREEN_WIDTH // 4, y, 200, 50, selected == i, SCREEN_WIDTH // 4 <= mouse_pos[0] <= SCREEN_WIDTH // 4 + 200 and y <= mouse_pos[1] <= y + 50)
            y += 60
        r, g, b = skins[selected]
        pygame.draw.rect(screen, (r, g, b), (SCREEN_WIDTH // 2 + 50, 150, 100, 100))
        for i, (label, delta) in enumerate([("Red", (10, 0, 0)), ("Green", (0, 10, 0)), ("Blue", (0, 0, 10))]):
            minus_rect = pygame.Rect(SCREEN_WIDTH // 2 + 50, 260 + i * 60, 30, 30)
            plus_rect = pygame.Rect(SCREEN_WIDTH // 2 + 120, 260 + i * 60, 30, 30)
            pygame.draw.rect(screen, BUTTON_COLOR, minus_rect)
            pygame.draw.rect(screen, BUTTON_COLOR, plus_rect)
            screen.blit(small_font.render("-", True, WHITE), minus_rect.move(10, 5))
            screen.blit(small_font.render("+", True, WHITE), plus_rect.move(10, 5))
            screen.blit(small_font.render(label, True, WHITE), (SCREEN_WIDTH // 2 + 160, 260 + i * 60))
            if minus_rect.collidepoint(mouse_pos) and pygame.mouse.get_pressed()[0]:
                skins[selected] = (max(0, r - delta[0]), max(0, g - delta[1]), max(0, b - delta[2]))
            if plus_rect.collidepoint(mouse_pos) and pygame.mouse.get_pressed()[0]:
                skins[selected] = (min(255, r + delta[0]), min(255, g + delta[1]), min(255, b + delta[2]))
        draw_button(screen, "Back", SCREEN_WIDTH // 2 - 150, y, 300, 60, hovered=(SCREEN_WIDTH // 2 - 150 <= mouse_pos[0] <= SCREEN_WIDTH // 2 + 150 and y <= mouse_pos[1] <= y + 60))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                return
            if event.type == pygame.MOUSEBUTTONDOWN:
                x, y_pos = event.pos
                for i in range(len(control_schemes)):
                    if SCREEN_WIDTH // 4 <= x <= SCREEN_WIDTH // 4 + 200 and 150 + i * 60 <= y_pos <= 200 + i * 60:
                        selected = i
                if SCREEN_WIDTH // 2 - 150 <= x <= SCREEN_WIDTH // 2 + 150 and y <= y_pos <= y + 60:
                    player_skins = skins
                    with open(SKINS_FILE, "w") as f:
                        json.dump(player_skins, f)
                    return

def pause_menu():
    while True:
        draw_gradient_background(screen, RED, PURPLE)
        draw_title(screen, "Paused", SCREEN_WIDTH // 2 - 100, 100)
        mouse_pos = pygame.mouse.get_pos()
        buttons = [("Continue", 250), ("Exit to Menu", 350), ("Controls", 450)]
        for text, y in buttons:
            draw_button(screen, text, SCREEN_WIDTH // 2 - 150, y, 300, 60, hovered=(SCREEN_WIDTH // 2 - 150 <= mouse_pos[0] <= SCREEN_WIDTH // 2 + 150 and y <= mouse_pos[1] <= y + 60))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return True
            if event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos
                if SCREEN_WIDTH // 2 - 150 <= x <= SCREEN_WIDTH // 2 + 150:
                    if 250 <= y <= 310:
                        return True
                    if 350 <= y <= 410:
                        return False
                    if 450 <= y <= 510:
                        show_controls()

def main_menu():
    while True:
        draw_gradient_background(screen, RED, PURPLE)
        title_text = "Apoca"
        title = font.render(title_text, True, WHITE)
        draw_title(screen, title_text, SCREEN_WIDTH // 2 - title.get_width() // 2, 100)
        mouse_pos = pygame.mouse.get_pos()
        buttons = [
            ("Play", 250, player_menu),
            ("Settings", 350, settings_menu),
            ("Exit", 450, lambda: pygame.quit() or sys.exit()),
        ]
        for i, (text, y, action) in enumerate(buttons):
            draw_button(screen, text, SCREEN_WIDTH // 2 - 150, y, 300, 60, hovered=(SCREEN_WIDTH // 2 - 150 <= mouse_pos[0] <= SCREEN_WIDTH // 2 + 150 and y <= mouse_pos[1] <= y + 60), border_color=SURVIVOR_COLORS[i % len(SURVIVOR_COLORS)])
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos
                for _, btn_y, action in buttons:
                    if SCREEN_WIDTH // 2 - 150 <= x <= SCREEN_WIDTH // 2 + 150 and btn_y <= y <= btn_y + 60:
                        action()

def player_menu():
    while True:
        draw_gradient_background(screen, RED, PURPLE)
        draw_title(screen, "Play", SCREEN_WIDTH // 2 - 50, 100)
        mouse_pos = pygame.mouse.get_pos()
        buttons = [
            ("Local Play", 250, player_selection_menu),
            ("Skins", 350, skin_customization_menu),
        ]
        for i, (text, y, action) in enumerate(buttons):
            draw_button(screen, text, SCREEN_WIDTH // 2 - 150, y, 300, 60, hovered=(SCREEN_WIDTH // 2 - 150 <= mouse_pos[0] <= SCREEN_WIDTH // 2 + 150 and y <= mouse_pos[1] <= y + 60), border_color=SURVIVOR_COLORS[i % len(SURVIVOR_COLORS)])
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                return
            if event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos
                for _, btn_y, action in buttons:
                    if SCREEN_WIDTH // 2 - 150 <= x <= SCREEN_WIDTH // 2 + 150 and btn_y <= y <= btn_y + 60:
                        action()

def player_selection_menu():
    selected_players, selected_timer, selected_ammo, include_ai = 2, 5, -1, False
    while True:
        draw_gradient_background(screen, RED, PURPLE)
        draw_title(screen, "Game Setup", SCREEN_WIDTH // 2 - 100, 50)
        mouse_pos = pygame.mouse.get_pos()
        buttons = [
            ("2 Players", SCREEN_WIDTH // 6, 150, selected_players == 2),
            ("3 Players", SCREEN_WIDTH // 6, 220, selected_players == 3),
            ("4 Players", SCREEN_WIDTH // 6, 290, selected_players == 4),
            ("5 Players", SCREEN_WIDTH // 6, 360, selected_players == 5),
            ("1 min", SCREEN_WIDTH // 2 - 125, 150, selected_timer == 1),
            ("2 min", SCREEN_WIDTH // 2 - 125, 220, selected_timer == 2),
            ("5 min", SCREEN_WIDTH // 2 - 125, 290, selected_timer == 5),
            ("10 min", SCREEN_WIDTH // 2 - 125, 360, selected_timer == 10),
            ("15 min", SCREEN_WIDTH // 2 - 125, 430, selected_timer == 15),
            ("10 Ammo", SCREEN_WIDTH * 5 // 6 - 250, 150, selected_ammo == 10),
            ("20 Ammo", SCREEN_WIDTH * 5 // 6 - 250, 220, selected_ammo == 20),
            ("50 Ammo", SCREEN_WIDTH * 5 // 6 - 250, 290, selected_ammo == 50),
            ("Unlimited", SCREEN_WIDTH * 5 // 6 - 250, 360, selected_ammo == -1),
            (f"AI: {'On' if include_ai else 'Off'}", SCREEN_WIDTH // 2 - 125, 500, include_ai),
            ("Start Game", SCREEN_WIDTH // 2 - 150, 600, False),
        ]
        for text, x, y, selected in buttons:
            draw_button(screen, text, x, y, 250 if "Start" not in text else 300, 50 if "Start" not in text else 60, selected, x <= mouse_pos[0] <= x + (250 if "Start" not in text else 300) and y <= mouse_pos[1] <= y + (50 if "Start" not in text else 60))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                return
            if event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos
                for btn_text, btn_x, btn_y, _ in buttons:
                    w, h = (250, 50) if "Start" not in btn_text else (300, 60)
                    if btn_x <= x <= btn_x + w and btn_y <= y <= btn_y + h:
                        if "Players" in btn_text:
                            selected_players = int(btn_text.split()[0])
                        elif "min" in btn_text:
                            selected_timer = int(btn_text.split()[0])
                        elif "Ammo" in btn_text:
                            selected_ammo = int(btn_text.split()[0])
                        elif btn_text == "Unlimited":
                            selected_ammo = -1
                        elif "AI" in btn_text:
                            include_ai = not include_ai
                        elif "Start" in btn_text:
                            game_world(selected_players, selected_timer, selected_ammo, include_ai)
                            return

def game_world(num_players, timer_duration, max_ammo, include_ai):
    clock = pygame.time.Clock()
    start_time = pygame.time.get_ticks()
    players, bullets = [], []
    action_cooldown_frames = int(game_settings["action_cooldown"] * 60)
    pulse_timer = 0

    # Player Setup
    human_count = num_players - (1 if include_ai else 0)
    infected_idx = random.randint(0, num_players - 1)
    for i in range(human_count):
        pos = spawn_points[i % len(spawn_points)].copy()
        while any(pygame.Rect(pos[0] - game_settings["player_size"], pos[1] - game_settings["player_size"], game_settings["player_size"] * 2, game_settings["player_size"] * 2).colliderect(b) for b in buildings):
            pos = spawn_points[(i + 1) % len(spawn_points)].copy()
        char = {
            "type": "infected" if i == infected_idx else "survivor",
            "pos": pos, "last_dx": 1, "last_dy": 0, "respawn_timer": 0,
            "attack_cooldown": 0, "shoot_cooldown": 0, "name": control_schemes[i]["name"],
            "index": i, "ammo": max_ammo if max_ammo != -1 else float("inf"), "is_ai": False,
        }
        players.append({"control": control_schemes[i], "character": char})

    if include_ai:
        ai_pos = spawn_points[min(human_count, len(spawn_points) - 1)].copy()
        while any(pygame.Rect(ai_pos[0] - game_settings["player_size"], ai_pos[1] - game_settings["player_size"], game_settings["player_size"] * 2, game_settings["player_size"] * 2).colliderect(b) for b in buildings):
            ai_pos = spawn_points[(human_count + 1) % len(spawn_points)].copy()
        ai_type = "infected" if not any(p["character"]["type"] == "infected" for p in players) else "survivor"
        players.append({
            "control": None,
            "character": {
                "type": ai_type, "pos": ai_pos, "last_dx": 1, "last_dy": 0, "respawn_timer": 0,
                "attack_cooldown": 0, "shoot_cooldown": 0, "name": "AI", "index": len(players),
                "ammo": max_ammo if max_ammo != -1 else float("inf"), "is_ai": True,
            }
        })

    def choose_respawn_point():
        valid_points = [sp for sp in spawn_points if not any(pygame.Rect(sp[0] - game_settings["player_size"], sp[1] - game_settings["player_size"], game_settings["player_size"] * 2, game_settings["player_size"] * 2).colliderect(b) for b in buildings)]
        if not valid_points:
            return spawn_points[0].copy()
        if not any(p["character"]["type"] == "survivor" for p in players):
            return valid_points[0].copy()
        return max(valid_points, key=lambda sp: min(math.hypot(sp[0] - p["character"]["pos"][0], sp[1] - p["character"]["pos"][1]) for p in players if p["character"]["type"] == "survivor" and p["character"]["respawn_timer"] == 0)).copy()

    def ai_decision(player, players, bullets):
        char = player["character"]
        if char["respawn_timer"] > 0:
            return
        speed = game_settings["infected_speed"] if char["type"] == "infected" else game_settings["survivor_speed"]
        accuracy = 0.5 + (game_settings["ai_difficulty"] - 1) * 0.25

        def adjust_direction(dx, dy, pos):
            rect = pygame.Rect(pos[0] + dx - game_settings["player_size"], pos[1] + dy - game_settings["player_size"], game_settings["player_size"] * 2, game_settings["player_size"] * 2)
            if any(rect.colliderect(b) for b in buildings):
                if not any(pygame.Rect(pos[0] + dx - game_settings["player_size"], pos[1] - game_settings["player_size"], game_settings["player_size"] * 2, game_settings["player_size"] * 2).colliderect(b) for b in buildings):
                    return dx, 0
                elif not any(pygame.Rect(pos[0] - game_settings["player_size"], pos[1] + dy - game_settings["player_size"], game_settings["player_size"] * 2, game_settings["player_size"] * 2).colliderect(b) for b in buildings):
                    return 0, dy
                else:
                    jitter = random.uniform(-speed * 0.5, speed * 0.5)
                    return jitter, jitter if random.choice([True, False]) else -jitter
            return dx, dy

        if char["type"] == "infected":
            target = min(
                (p for p in players if p["character"]["type"] == "survivor" and p["character"]["respawn_timer"] == 0),
                key=lambda p: math.hypot(p["character"]["pos"][0] - char["pos"][0], p["character"]["pos"][1] - char["pos"][1]),
                default=None)
            if target:
                dx = target["character"]["pos"][0] - char["pos"][0]
                dy = target["character"]["pos"][1] - char["pos"][1]
                dist = max(1, math.hypot(dx, dy))
                dx, dy = dx / dist * speed, dy / dist * speed
                dx, dy = adjust_direction(dx, dy, char["pos"])
                new_pos = [char["pos"][0] + dx, char["pos"][1] + dy]
                if PLAYABLE_LEFT <= new_pos[0] <= PLAYABLE_RIGHT and PLAYABLE_TOP <= new_pos[1] <= PLAYABLE_BOTTOM:
                    char["pos"] = new_pos
                char["last_dx"], char["last_dy"] = dx, dy
                if dist < INFECTED_ATTACK_RADIUS + game_settings["player_size"] and char["attack_cooldown"] <= action_cooldown_frames // 2 and random.random() < accuracy:
                    char["attack_cooldown"] = action_cooldown_frames

        else:  # Survivor AI
            threat = min(
                (p for p in players if p["character"]["type"] == "infected" and p["character"]["respawn_timer"] == 0),
                key=lambda p: math.hypot(p["character"]["pos"][0] - char["pos"][0], p["character"]["pos"][1] - char["pos"][1]),
                default=None)
            if threat:
                dx = threat["character"]["pos"][0] - char["pos"][0]
                dy = threat["character"]["pos"][1] - char["pos"][1]
                dist = max(1, math.hypot(dx, dy))
                if dist < 200 and char["shoot_cooldown"] == 0 and char["ammo"] > 0 and random.random() < accuracy:
                    angle = math.atan2(dy, dx)
                    for offset in [-0.1, 0, 0.1]:
                        bullet = {"x": char["pos"][0], "y": char["pos"][1], "dx": math.cos(angle + offset), "dy": math.sin(angle + offset)}
                        bullets.append(bullet)
                    char["shoot_cooldown"] = action_cooldown_frames
                    char["ammo"] -= 1
                elif dist < 300:
                    dx, dy = -dx / dist * speed, -dy / dist * speed
                    dx, dy = adjust_direction(dx, dy, char["pos"])
                    new_pos = [char["pos"][0] + dx, char["pos"][1] + dy]
                    if PLAYABLE_LEFT <= new_pos[0] <= PLAYABLE_RIGHT and PLAYABLE_TOP <= new_pos[1] <= PLAYABLE_BOTTOM:
                        char["pos"] = new_pos
                    char["last_dx"], char["last_dy"] = dx, dy

    while True:
        screen.fill(BLACK)
        pygame.draw.rect(screen, GROUND_COLOR, (PLAYABLE_LEFT, PLAYABLE_TOP, PLAYABLE_RIGHT - PLAYABLE_LEFT, PLAYABLE_BOTTOM - PLAYABLE_TOP))
        for i, building in enumerate(buildings):
            pygame.draw.rect(screen, (100 + (i % 3) * 50, 100 + ((i + 1) % 3) * 50, 100 + ((i + 2) % 3) * 50), building)

        keys = pygame.key.get_pressed()
        for player in players:
            char = player["character"]
            if char["is_ai"]:
                ai_decision(player, players, bullets)
            else:
                speed = game_settings["survivor_speed"] if char["type"] == "survivor" else game_settings["infected_speed"]
                dx = (keys[player["control"]["right"]] - keys[player["control"]["left"]]) * speed
                dy = (keys[player["control"]["down"]] - keys[player["control"]["up"]]) * speed
                if dx or dy:
                    char["last_dx"], char["last_dy"] = dx, dy
                new_pos_x = [char["pos"][0] + dx, char["pos"][1]]
                new_pos_y = [char["pos"][0], char["pos"][1] + dy]
                rect_x = pygame.Rect(new_pos_x[0] - game_settings["player_size"], new_pos_x[1] - game_settings["player_size"], game_settings["player_size"] * 2, game_settings["player_size"] * 2)
                rect_y = pygame.Rect(new_pos_y[0] - game_settings["player_size"], new_pos_y[1] - game_settings["player_size"], game_settings["player_size"] * 2, game_settings["player_size"] * 2)
                if not any(rect_x.colliderect(b) for b in buildings):
                    char["pos"][0] = new_pos_x[0]
                if not any(rect_y.colliderect(b) for b in buildings):
                    char["pos"][1] = new_pos_y[1]
                char["pos"][0] = max(PLAYABLE_LEFT + game_settings["player_size"], min(PLAYABLE_RIGHT - game_settings["player_size"], char["pos"][0]))
                char["pos"][1] = max(PLAYABLE_TOP + game_settings["player_size"], min(PLAYABLE_BOTTOM - game_settings["player_size"], char["pos"][1]))

            if char["respawn_timer"] > 0:
                char["respawn_timer"] -= 1
                if char["respawn_timer"] == 0:
                    char["pos"] = choose_respawn_point()
            if char["attack_cooldown"] > 0:
                char["attack_cooldown"] -= 1
            if char["shoot_cooldown"] > 0:
                char["shoot_cooldown"] -= 1

        for bullet in bullets[:]:
            bullet["x"] += bullet["dx"] * game_settings["bullet_speed"]
            bullet["y"] += bullet["dy"] * game_settings["bullet_speed"]
            bullet_rect = pygame.Rect(bullet["x"] - 5, bullet["y"] - 5, 10, 10)
            if any(bullet_rect.colliderect(b) for b in buildings) or not (PLAYABLE_LEFT < bullet["x"] < PLAYABLE_RIGHT and PLAYABLE_TOP < bullet["y"] < PLAYABLE_BOTTOM):
                bullets.remove(bullet)
                continue
            for player in players:
                char = player["character"]
                if char["type"] == "infected" and char["respawn_timer"] == 0:
                    char_rect = pygame.Rect(char["pos"][0] - game_settings["player_size"], char["pos"][1] - game_settings["player_size"], game_settings["player_size"] * 2, game_settings["player_size"] * 2)
                    if bullet_rect.colliderect(char_rect):
                        bullets.remove(bullet)
                        char["respawn_timer"] = 300
                        char["pos"] = [-100, -100]
                        break

        pulse_timer = (pulse_timer + 1) % 60
        pulsed_size = int(game_settings["player_size"] * (1 + 0.1 * math.sin(pulse_timer * math.pi / 30)))
        for player in players:
            char = player["character"]
            if char["respawn_timer"] == 0:
                color = INFECTED_COLOR if char["type"] == "infected" else player_skins[char["index"]]
                pygame.draw.circle(screen, color, (int(char["pos"][0]), int(char["pos"][1])), pulsed_size)
                name_text = name_font.render(char["name"], True, WHITE)
                screen.blit(name_text, (char["pos"][0] - name_text.get_width() // 2, char["pos"][1] - pulsed_size - 20))
            if char["type"] == "infected" and char["attack_cooldown"] == 0:
                if (not char["is_ai"] and player["control"] and keys[player["control"]["action"]]) or (char["is_ai"]):
                    screen.blit(radius_surface, (char["pos"][0] - INFECTED_ATTACK_RADIUS, char["pos"][1] - INFECTED_ATTACK_RADIUS))
                    for other in players:
                        if other["character"]["type"] == "survivor" and other["character"]["respawn_timer"] == 0:
                            dist = math.hypot(other["character"]["pos"][0] - char["pos"][0], other["character"]["pos"][1] - char["pos"][1])
                            if dist < INFECTED_ATTACK_RADIUS + game_settings["player_size"]:
                                other["character"]["type"] = "infected"
                    char["attack_cooldown"] = action_cooldown_frames

        for bullet in bullets:
            pygame.draw.circle(screen, BULLET_COLOR, (int(bullet["x"]), int(bullet["y"])), 5)

        elapsed = (pygame.time.get_ticks() - start_time) / 1000
        time_left = max(0, timer_duration * 60 - elapsed)
        screen.blit(font.render(f"Time: {int(time_left)}s", True, WHITE), (10, 10))
        if max_ammo != -1:
            for i, player in enumerate(players):
                if player["character"]["type"] == "survivor":
                    screen.blit(font.render(f"{player['character']['name']} Ammo: {player['character']['ammo']}", True, WHITE), (10, 50 + i * 40))

        if all(p["character"]["type"] == "infected" for p in players):
            screen.blit(font.render("Infected Win!", True, WHITE), (SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2))
            pygame.display.flip()
            pygame.time.wait(2000)
            return
        if time_left <= 0 and any(p["character"]["type"] == "survivor" for p in players):
            screen.blit(font.render("Survivors Win!", True, WHITE), (SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2))
            pygame.display.flip()
            pygame.time.wait(2000)
            return

        pygame.display.flip()
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if not pause_menu():
                        return
                for player in players:
                    char = player["character"]
                    if not char["is_ai"] and event.key == player["control"]["action"] and char["type"] == "survivor" and char["shoot_cooldown"] == 0 and char["ammo"] > 0:
                        angle = math.atan2(char["last_dy"], char["last_dx"])
                        for offset in [-0.2618, 0, 0.2618]:
                            bullet = {"x": char["pos"][0], "y": char["pos"][1], "dx": math.cos(angle + offset), "dy": math.sin(angle + offset)}
                            bullets.append(bullet)
                        char["shoot_cooldown"] = action_cooldown_frames
                        char["ammo"] -= 1

if __name__ == "__main__":
    main_menu()

