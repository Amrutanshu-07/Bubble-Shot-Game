import pygame
import math
import random
from collections import deque

SCREEN_WIDTH = 640
SCREEN_HEIGHT = 800
FPS = 60
GRID_TOP = 60            
CELL_RADIUS = 20         
CELL_DIAM = CELL_RADIUS * 2
COLS = 10
ROWS = 12
SHOOTER_Y = SCREEN_HEIGHT - 80
SHOOTER_POS = (SCREEN_WIDTH // 2, SHOOTER_Y)
SHOT_BASE_SPEED = 600    
POP_MIN = 3              


COLORS = [
    (231, 76, 60),   # red
    (46, 204, 113),  # green
    (52, 152, 219),  # blue
    (241, 196, 15),  # yellow
    (155, 89, 182),  # purple
]
BACKGROUND_COLOR = (30, 30, 30)
UI_COLOR = (240, 240, 240)
SHINE_COLOR = (255, 255, 255)
BORDER_COLOR = (20, 20, 20)

# Scoring
HIT_SCORE = 10              
DROP_BONUS_SCORE = 15        
LEVEL_CREDIT_REWARD = 10    
LEVEL_BANNER_TIME = 2.0  

def clamp(v, a, b):
    return max(a, min(b, v))


def grid_to_pixel(col, row):
    """Convert axial grid position to pixel center.
    We use an offset grid where odd rows are shifted right by half a cell.
    """
    x_offset = CELL_RADIUS if (row % 2 == 1) else 0
    x = col * CELL_DIAM + CELL_RADIUS + x_offset + (SCREEN_WIDTH - (COLS * CELL_DIAM + CELL_RADIUS)) // 2
    y = GRID_TOP + row * int(CELL_RADIUS * 1.73)  # ~sqrt(3)
    return int(x), int(y)


def pixel_to_grid_bruteforce(px, py):
    """Slow but simple. Kept as fallback/reference."""
    best = None
    best_dist = float('inf')
    for r in range(ROWS):
        for c in range(COLS):
            gx, gy = grid_to_pixel(c, r)
            d = math.hypot(gx - px, gy - py)
            if d < best_dist:
                best_dist = d
                best = (c, r)
    return best


def pixel_to_grid_fast(px, py):
    """Faster nearest-cell lookup by searching only nearby rows.
    Uses a row hint from the y position to reduce checks significantly.
    """
    row_height = CELL_RADIUS * 1.73
    approx_row = int((py - GRID_TOP) / row_height)
    start_row = max(0, approx_row - 2)
    end_row = min(ROWS - 1, approx_row + 2)

    best = None
    best_dist = float('inf')
    for r in range(start_row, end_row + 1):
        for c in range(COLS):
            gx, gy = grid_to_pixel(c, r)
            d = math.hypot(gx - px, gy - py)
            if d < best_dist:
                best_dist = d
                best = (c, r)
    if best is None:
        return pixel_to_grid_bruteforce(px, py)
    return best


class Bubble:
    def __init__(self, x, y, color_index, radius=CELL_RADIUS):
        self.x = x
        self.y = y
        self.r = radius
        self.color_index = color_index
        self.color = COLORS[color_index]
        self.vx = 0.0
        self.vy = 0.0
        self.moving = False

    def set_velocity(self, vx, vy):
        self.vx = vx
        self.vy = vy
        self.moving = True

    def update(self, dt):
        if not self.moving:
            return
        self.x += self.vx * dt
        self.y += self.vy * dt
    
        if self.x - self.r < 0:
            self.x = self.r
            self.vx *= -1
        if self.x + self.r > SCREEN_WIDTH:
            self.x = SCREEN_WIDTH - self.r
            self.vx *= -1

    def draw(self, surf):
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), self.r)
        
        shine_x = int(self.x - self.r * 0.4)
        shine_y = int(self.y - self.r * 0.4)
        pygame.draw.circle(surf, SHINE_COLOR, (shine_x, shine_y), int(self.r * 0.25))
        pygame.draw.circle(surf, BORDER_COLOR, (int(self.x), int(self.y)), self.r, 2)


class Grid:
    def __init__(self, max_colors=len(COLORS)):
        self.cells = [[None for _ in range(ROWS)] for _ in range(COLS)]
        self.score = 0
        self.max_colors = max_colors
        self.populate_initial_rows(5, max_colors=max_colors)


    def populate_initial_rows(self, num_rows, max_colors=None):
        maxc = max_colors if max_colors is not None else self.max_colors
        for r in range(num_rows):
            for c in range(COLS):
                color_idx = random.randrange(maxc)
                self.cells[c][r] = color_idx

    def add_row_top(self, num_rows=1, max_colors=None):
        maxc = max_colors if max_colors is not None else self.max_colors
        for _ in range(num_rows):
            
            for r in reversed(range(1, ROWS)):
                for c in range(COLS):
                    self.cells[c][r] = self.cells[c][r-1]
          
            for c in range(COLS):
                self.cells[c][0] = random.randrange(maxc)

    def draw(self, surf):
        for r in range(ROWS):
            for c in range(COLS):
                ci = self.cells[c][r]
                if ci is not None:
                    cx, cy = grid_to_pixel(c, r)
                    pygame.draw.circle(surf, COLORS[ci], (cx, cy), CELL_RADIUS)
                    shine_x = cx - int(CELL_RADIUS * 0.4)
                    shine_y = cy - int(CELL_RADIUS * 0.4)
                    pygame.draw.circle(surf, SHINE_COLOR, (shine_x, shine_y), int(CELL_RADIUS * 0.25))
                    pygame.draw.circle(surf, BORDER_COLOR, (cx, cy), CELL_RADIUS, 2)

 
    def active_colors(self):
        s = set()
        for r in range(ROWS):
            for c in range(COLS):
                ci = self.cells[c][r]
                if ci is not None:
                    s.add(ci)
        if not s:
           
            return set(range(self.max_colors))
        return s

    def place_bubble_at_pixel(self, bubble):
   
        c, r = pixel_to_grid_fast(bubble.x, bubble.y)
        c = int(clamp(c, 0, COLS - 1))
        r = int(clamp(r, 0, ROWS - 1))
        if self.cells[c][r] is not None:

            found = False
            for rad in range(1, 3):
                for dc in range(-rad, rad + 1):
                    for dr in range(-rad, rad + 1):
                        nc, nr = c + dc, r + dr
                        if 0 <= nc < COLS and 0 <= nr < ROWS and self.cells[nc][nr] is None:
                            c, r = nc, nr
                            found = True
                            break
                    if found:
                        break
                if found:
                    break
        self.cells[c][r] = bubble.color_index
        return c, r

    def neighbors(self, c, r):
        neigh = []

        for dc, dr in [(-1, 0), (1, 0)]:
            nc, nr = c + dc, r + dr
            if 0 <= nc < COLS and 0 <= nr < ROWS:
                neigh.append((nc, nr))

        if r % 2 == 0:
            deltas = [(-1, -1), (0, -1), (-1, 1), (0, 1)]
        else:

            deltas = [(1, -1), (0, -1), (0, 1), (1, 1)]
        for dc, dr in deltas:
            nc, nr = c + dc, r + dr
            if 0 <= nc < COLS and 0 <= nr < ROWS:
                neigh.append((nc, nr))
        return neigh


    def flood_fill_group(self, start_c, start_r):
        if self.cells[start_c][start_r] is None:
            return []
        color_idx = self.cells[start_c][start_r]
        visited = set([(start_c, start_r)])
        q = deque([(start_c, start_r)])
        while q:
            c, r = q.popleft()
            for nc, nr in self.neighbors(c, r):
                if (nc, nr) not in visited and self.cells[nc][nr] == color_idx:
                    visited.add((nc, nr))
                    q.append((nc, nr))
        return list(visited)

    def remove_cells(self, cell_list):
        for c, r in cell_list:
            self.cells[c][r] = None

    def remove_floating_groups(self):
        """Remove all bubbles not connected to the top row. Return count removed."""
        visited = set()
        q = deque()
     
        for c in range(COLS):
            if self.cells[c][0] is not None:
                visited.add((c, 0))
                q.append((c, 0))

        while q:
            c, r = q.popleft()
            for nc, nr in self.neighbors(c, r):
                if (nc, nr) not in visited and self.cells[nc][nr] is not None:
                    visited.add((nc, nr))
                    q.append((nc, nr))

        floating = []
        for r in range(ROWS):
            for c in range(COLS):
                if self.cells[c][r] is not None and (c, r) not in visited:
                    floating.append((c, r))
        self.remove_cells(floating)
        return len(floating)

    def pop_if_matching(self, c, r):
        """Pop matching group, then drop floating clusters. Returns total removed count."""
        total_removed = 0
        group = self.flood_fill_group(c, r)
        if len(group) >= POP_MIN:
            self.remove_cells(group)
            total_removed += len(group)
            self.score += len(group) * HIT_SCORE

            dropped = self.remove_floating_groups()
            if dropped > 0:
                total_removed += dropped
                self.score += dropped * DROP_BONUS_SCORE
        return total_removed

    def any_bubbles_left(self):
        for r in range(ROWS):
            for c in range(COLS):
                if self.cells[c][r] is not None:
                    return True
        return False

    def bottom_occupied(self):
        for c in range(COLS):
            if self.cells[c][ROWS - 1] is not None:
                return True
        return False



def level_params(level):
    """Return derived parameters for a level number (1-based)."""

    target = 400 + (level - 1) * 450 + max(0, level - 2) * 10
    max_colors = min(2 + level, len(COLORS))  
    shots_to_drop = max(4, 9 - level)          
    initial_rows = min(5 + (level - 1), ROWS - 2)
    shot_speed = SHOT_BASE_SPEED + (level - 1) * 40
    return {
        "target": target,
        "max_colors": max_colors,
        "shots_to_drop": shots_to_drop,  
        "initial_rows": initial_rows,
        "shot_speed": shot_speed,
    }




def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Bubble Shot — Levels & Credits")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 20)
    bigfont = pygame.font.SysFont("Arial", 36, bold=True)


    level = 1
    credits = 0
    params = level_params(level)

    grid = Grid(max_colors=params["max_colors"])  

    grid.cells = [[None for _ in range(ROWS)] for _ in range(COLS)]
    grid.populate_initial_rows(params["initial_rows"], max_colors=params["max_colors"])

 
    current_shot_speed = params["shot_speed"]
    def make_next_color():
        active = list(grid.active_colors())
      
        palette = list(range(params["max_colors"]))
        
        pool = active if active else palette
        return random.choice(pool)

    current_bubble = Bubble(SHOOTER_POS[0], SHOOTER_POS[1], make_next_color())
    current_bubble.moving = False
    next_preview = Bubble(SHOOTER_POS[0] + 60, SHOOTER_POS[1] + 20, make_next_color())
    next_preview.moving = False

    running = True
    paused = False
    game_over = False
    out_of_shots = False  

    shots_fired = 0
    shots_allowed = params["shots_to_drop"] 
    shots_remaining = shots_allowed
    level_banner_timer = 0.0

    
    min_angle = -math.pi * 0.95
    max_angle = -0.05

    def restart_all():
        nonlocal level, credits, params, grid, current_bubble, next_preview
        nonlocal shots_fired, shots_allowed, shots_remaining, level_banner_timer, current_shot_speed
        nonlocal game_over, paused, out_of_shots
        level = 1
        credits = 0
        params = level_params(level)
        grid = Grid(max_colors=params["max_colors"])
        grid.cells = [[None for _ in range(ROWS)] for _ in range(COLS)]
        grid.populate_initial_rows(params["initial_rows"], max_colors=params["max_colors"])
        current_bubble = Bubble(SHOOTER_POS[0], SHOOTER_POS[1], make_next_color())
        current_bubble.moving = False
        next_preview = Bubble(SHOOTER_POS[0] + 60, SHOOTER_POS[1] + 20, make_next_color())
        next_preview.moving = False
        shots_fired = 0
        shots_allowed = params["shots_to_drop"]
        shots_remaining = shots_allowed
        level_banner_timer = 0.0
        current_shot_speed = params["shot_speed"]
        game_over = False
        paused = False
        out_of_shots = False

    def start_next_level():
        nonlocal level, credits, params, grid, current_bubble, next_preview
        nonlocal shots_fired, shots_allowed, shots_remaining, level_banner_timer, current_shot_speed
        nonlocal out_of_shots
        level += 1
        credits += LEVEL_CREDIT_REWARD
        params = level_params(level)
        
        grid = Grid(max_colors=params["max_colors"])
        grid.cells = [[None for _ in range(ROWS)] for _ in range(COLS)]
        grid.populate_initial_rows(params["initial_rows"], max_colors=params["max_colors"])
        current_bubble = Bubble(SHOOTER_POS[0], SHOOTER_POS[1], make_next_color())
        current_bubble.moving = False
        next_preview = Bubble(SHOOTER_POS[0] + 60, SHOOTER_POS[1] + 20, make_next_color())
        next_preview.moving = False
        shots_fired = 0
        shots_allowed = params["shots_to_drop"]
        shots_remaining = shots_allowed
        level_banner_timer = LEVEL_BANNER_TIME
        current_shot_speed = params["shot_speed"]
        out_of_shots = False

    def launch_bubble(bubble, target_x, target_y):
        dx = target_x - SHOOTER_POS[0]
        dy = target_y - SHOOTER_POS[1]
        if dy >= -5:  
            dy = -5
        angle = math.atan2(dy, dx)
        angle = clamp(angle, min_angle, max_angle)
        vx = math.cos(angle) * current_shot_speed
        vy = math.sin(angle) * current_shot_speed
        bubble.set_velocity(vx, vy)

    while running:
        dt = clock.tick(FPS) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    restart_all()
                elif event.key == pygame.K_SPACE:
                    if not current_bubble.moving and not game_over and not paused:
                        mx, my = pygame.mouse.get_pos()
                        launch_bubble(current_bubble, mx, my)
                elif event.key == pygame.K_p:
                    paused = not paused
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and not game_over and not paused:
                    if not current_bubble.moving:
                        mx, my = event.pos
                        launch_bubble(current_bubble, mx, my)

        if paused:
            screen.fill(BACKGROUND_COLOR)
            pygame.draw.rect(screen, (50, 50, 50), (0, GRID_TOP - 10, SCREEN_WIDTH, SCREEN_HEIGHT - GRID_TOP + 10))
            grid.draw(screen)
            current_bubble.draw(screen)
            next_preview.draw(screen)
            pause_surf_shadow = bigfont.render("PAUSED", True, (0, 0, 0))
            pause_surf = bigfont.render("PAUSED", True, UI_COLOR)
            px = SCREEN_WIDTH // 2 - pause_surf.get_width() // 2
            py = SCREEN_HEIGHT // 2 - pause_surf.get_height() // 2
            screen.blit(pause_surf_shadow, (px + 2, py + 2))
            screen.blit(pause_surf, (px, py))
            pygame.display.flip()
            continue

        if level_banner_timer > 0:
            level_banner_timer = max(0.0, level_banner_timer - dt)

        if current_bubble.moving:
            current_bubble.update(dt)

           
            if current_bubble.y - current_bubble.r <= GRID_TOP:
                nc, nr = grid.place_bubble_at_pixel(current_bubble)
                grid.pop_if_matching(nc, nr)
         
                current_bubble = Bubble(SHOOTER_POS[0], SHOOTER_POS[1], next_preview.color_index)
                current_bubble.moving = False
                next_preview = Bubble(SHOOTER_POS[0] + 60, SHOOTER_POS[1] + 20, make_next_color())
                next_preview.moving = False
                shots_fired += 1

                shots_remaining = max(0, shots_remaining - 1)
               
                if shots_remaining == 0 and grid.score < params["target"]:
                    game_over = True
                    out_of_shots = True

            else:
     
                collided = False
                row_height = CELL_RADIUS * 1.73
                approx_row = int((current_bubble.y - GRID_TOP) / row_height)
                start_row = max(0, approx_row - 2)
                end_row = min(ROWS, approx_row + 3)
                for r in range(start_row, end_row):
                    for c in range(COLS):
                        ci = grid.cells[c][r]
                        if ci is not None:
                            gx, gy = grid_to_pixel(c, r)
                            dist = math.hypot(current_bubble.x - gx, current_bubble.y - gy)
                            if dist <= current_bubble.r + CELL_RADIUS - 2:
                                nc, nr = grid.place_bubble_at_pixel(current_bubble)
                                grid.pop_if_matching(nc, nr)
                                current_bubble = Bubble(SHOOTER_POS[0], SHOOTER_POS[1], next_preview.color_index)
                                current_bubble.moving = False
                                next_preview = Bubble(SHOOTER_POS[0] + 60, SHOOTER_POS[1] + 20, make_next_color())
                                next_preview.moving = False
                                shots_fired += 1

                    
                                shots_remaining = max(0, shots_remaining - 1)
                       
                                if shots_remaining == 0 and grid.score < params["target"]:
                                    game_over = True
                                    out_of_shots = True

                                collided = True
                                break
                    if collided:
                        break

       
            

      
        if grid.bottom_occupied():
            game_over = True
            out_of_shots = False  

    
        if grid.score >= params["target"] and not game_over:
            start_next_level()


        screen.fill(BACKGROUND_COLOR)

        pygame.draw.rect(screen, (50, 50, 50), (0, GRID_TOP - 10, SCREEN_WIDTH, SCREEN_HEIGHT - GRID_TOP + 10))
        grid.draw(screen)


        pygame.draw.rect(screen, (60, 60, 60), (SCREEN_WIDTH // 2 - 60, SHOOTER_Y + 35, 120, 8), border_radius=4)


        mx, my = pygame.mouse.get_pos()
        dx = mx - SHOOTER_POS[0]
        dy = my - SHOOTER_POS[1]
        angle = math.atan2(dy, dx)
        angle = clamp(angle, min_angle, max_angle)
        length = 70
        aim_x = SHOOTER_POS[0] + math.cos(angle) * length
        aim_y = SHOOTER_POS[1] + math.sin(angle) * length
        dash_length = 5
        gap_length = 3
        total_length = math.hypot(aim_x - SHOOTER_POS[0], aim_y - SHOOTER_POS[1])
        if total_length > 0:
            num_dashes = int(total_length / (dash_length + gap_length))
            for i in range(num_dashes):
                start_ratio = i * (dash_length + gap_length) / total_length
                end_ratio = start_ratio + dash_length / total_length
                start_x = SHOOTER_POS[0] + (aim_x - SHOOTER_POS[0]) * start_ratio
                start_y = SHOOTER_POS[1] + (aim_y - SHOOTER_POS[1]) * start_ratio
                end_x = SHOOTER_POS[0] + (aim_x - SHOOTER_POS[0]) * end_ratio
                end_y = SHOOTER_POS[1] + (aim_y - SHOOTER_POS[1]) * end_ratio
                pygame.draw.line(screen, UI_COLOR, (start_x, start_y), (end_x, end_y), 2)


        if current_bubble:
            if not current_bubble.moving:
                ang = math.atan2(my - SHOOTER_POS[1], mx - SHOOTER_POS[0])
                ang = clamp(ang, min_angle, max_angle)
                hold_dist = 36
                current_bubble.x = SHOOTER_POS[0] + math.cos(ang) * hold_dist
                current_bubble.y = SHOOTER_POS[1] + math.sin(ang) * hold_dist
            current_bubble.draw(screen)


        if next_preview:
            pygame.draw.circle(screen, (80, 80, 80), (next_preview.x, next_preview.y), next_preview.r + 4)
            next_preview.draw(screen)
            txt_shadow = font.render("Next", True, (0, 0, 0))
            txt = font.render("Next", True, UI_COLOR)
            screen.blit(txt_shadow, (next_preview.x - 19, next_preview.y + 29))
            screen.blit(txt, (next_preview.x - 20, next_preview.y + 28))


        score_surf_shadow = font.render(f"Score: {grid.score}", True, (0, 0, 0))
        score_surf = font.render(f"Score: {grid.score}", True, UI_COLOR)
        screen.blit(score_surf_shadow, (13, 13))
        screen.blit(score_surf, (12, 12))

        level_surf_shadow = font.render(f"Level: {level}", True, (0, 0, 0))
        level_surf = font.render(f"Level: {level}", True, UI_COLOR)
        screen.blit(level_surf_shadow, (200 + 13, 13))
        screen.blit(level_surf, (200 + 12, 12))

        target_surf_shadow = font.render(f"Target: {params['target']}", True, (0, 0, 0))
        target_surf = font.render(f"Target: {params['target']}", True, UI_COLOR)
        screen.blit(target_surf_shadow, (320 + 13, 13))
        screen.blit(target_surf, (320 + 12, 12))

        credits_s_shadow = font.render(f"Credits: {credits}", True, (0, 0, 0))
        credits_s = font.render(f"Credits: {credits}", True, UI_COLOR)
        screen.blit(credits_s_shadow, (13, 38))
        screen.blit(credits_s, (12, 38))

        drop_in_shadow = font.render(f"Shots left: {shots_remaining}", True, (0, 0, 0))
        drop_in = font.render(f"Shots left: {shots_remaining}", True, UI_COLOR)
        screen.blit(drop_in_shadow, (200 + 13, 38))
        screen.blit(drop_in, (200 + 12, 38))

        inst_shadow = font.render("Click or SPACE to shoot. R = restart, P = pause, ESC = quit", True, (0, 0, 0))
        inst = font.render("Click or SPACE to shoot. R = restart, P = pause, ESC = quit", True, UI_COLOR)
        screen.blit(inst_shadow, (13, SCREEN_HEIGHT - 27))
        screen.blit(inst, (12, SCREEN_HEIGHT - 28))

        if level_banner_timer > 0:
            banner = bigfont.render(f"LEVEL {level}! +{LEVEL_CREDIT_REWARD} credits", True, (200, 220, 20))
            shadow = bigfont.render(f"LEVEL {level}! +{LEVEL_CREDIT_REWARD} credits", True, (0, 0, 0))
            bx = SCREEN_WIDTH // 2 - banner.get_width() // 2
            by = SCREEN_HEIGHT // 2 - 20
            screen.blit(shadow, (bx + 2, by + 2))
            screen.blit(banner, (bx, by))

        if game_over:
            if out_of_shots:
                lose_msg_shadow = bigfont.render("OUT OF SHOTS. Press R to restart", True, (0, 0, 0))
                lose_msg = bigfont.render("OUT OF SHOTS. Press R to restart", True, (220, 80, 80))
            else:
                lose_msg_shadow = bigfont.render("GAME OVER. Press R to restart", True, (0, 0, 0))
                lose_msg = bigfont.render("GAME OVER. Press R to restart", True, (220, 80, 80))
            lx = SCREEN_WIDTH // 2 - lose_msg.get_width() // 2
            ly = SCREEN_HEIGHT // 2 - 20
            screen.blit(lose_msg_shadow, (lx + 2, ly + 2))
            screen.blit(lose_msg, (lx, ly))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
