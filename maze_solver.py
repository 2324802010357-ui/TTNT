import tkinter as tk
from tkinter import Canvas
import random
from collections import deque
from typing import List, Tuple, Set
import time
import os
import itertools

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

# Constants
ROWS = 51
COLS = 81
CELL_SIZE = 14
EXIT_COUNT = 6
WAYPOINT_COUNT = 4  # Tạo 4 điểm mốc
START_POSITION = (25, 40)  # Center of maze
MAX_GENERATION_ATTEMPTS = 20
VISITED_CELL_DELAY_MS = 5
PATH_CELL_DELAY_MS = 15
ANIMATION_FRAME_SKIP = 6

# Complexity features - Many Walls Maze (Nhiều tường)
ROOM_COUNT = 0
LOOP_CARVE_RATE = 0.15
MIN_START_BRANCHES = 3
ENEMY_COUNT = 3
ENEMY_MIN_DISTANCE = 8
BRAID_RATE = 0.30  # Increased to create more dead ends

# Colors
COLOR_WALL = "#0F172A"
COLOR_PATH = "#F8FAFC"
COLOR_VISITED = "#22D3EE"  # Default visited
COLOR_VISITED_BFS = "#22D3EE"  # BFS visited - Cyan
COLOR_VISITED_ASTAR = "#84CC16"  # A* visited - Lime green
COLOR_SOLUTION = "#F97316"
COLOR_START = "#2563EB"
COLOR_EXIT = "#22C55E"
COLOR_ENEMY = "#A855F7"
COLOR_GOAL = "#EF4444"
COLOR_WAYPOINT = "#EC4899"  # Hot pink cho điểm mốc
COLOR_BUTTON = "#333333"
COLOR_TEXT = "#FFFFFF"

SANTA_SCALE = 10.0

class MazeSolver:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Trình giải mê cung AI")
        self.root.geometry("1200x900")  # Set initial window size
        
        self.width = COLS * CELL_SIZE
        self.height = ROWS * CELL_SIZE
        
        # Main container with grid layout
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Top area: maze canvas (left) + run history (right)
        top_frame = tk.Frame(self.root, bg="black")
        top_frame.grid(row=0, column=0, sticky="nsew")
        top_frame.grid_rowconfigure(0, weight=1)
        top_frame.grid_columnconfigure(0, weight=4)
        top_frame.grid_columnconfigure(1, weight=1)

        # Canvas frame - responsive
        canvas_frame = tk.Frame(top_frame, bg="black")
        canvas_frame.grid(row=0, column=0, sticky="nsew")
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)
        canvas_frame.grid_propagate(True)  # Allow frame to expand
        
        # Canvas
        self.canvas = Canvas(canvas_frame, bg="black", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", self.on_canvas_configure)

        self.santa_image_path = os.path.join(
            os.path.dirname(__file__), "..", "Picture", "anh-ong-gia-noel.png"
        )
        self.santa_base_image = None
        self.santa_tk_image = None
        self.santa_last_size = None
        self.last_santa = None
        self.santa_load_error = None

        # Run history panel on the right side
        history_frame = tk.Frame(top_frame, bg="#0b1020", width=280)
        history_frame.grid(row=0, column=1, sticky="nsew")
        history_frame.grid_propagate(False)
        history_frame.grid_rowconfigure(1, weight=1)
        history_frame.grid_columnconfigure(0, weight=1)

        history_title = tk.Label(history_frame, text="Lịch sử chạy", bg="#111827", fg="#F9FAFB", font=("Arial", 11, "bold"))
        history_title.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 2))

        self.history_text = tk.Text(
            history_frame,
            bg="#0b1020",
            fg="#E5E7EB",
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Consolas", 9),
            borderwidth=0,
            highlightthickness=0,
        )
        self.history_text.grid(row=1, column=0, sticky="nsew", padx=6, pady=(2, 6))

        self.clear_history_btn = tk.Button(
            history_frame,
            text="Xóa lịch sử",
            command=self.clear_history,
            bg="#374151",
            fg="#F9FAFB",
        )
        self.clear_history_btn.grid(row=2, column=0, sticky="ew", padx=6, pady=(0, 6))

        self.history_text.config(state=tk.NORMAL)
        self.history_text.insert(tk.END, "- Bấm Giai me cung de luu ket qua vao lich su.\n")
        self.history_text.config(state=tk.DISABLED)
        
        # Tính kích thước cell dựa trên window geometry
        # Canvas sẽ có width = root width, height = root height - button - status - comparison
        # Tạm thời sử dụng estimate, sẽ được update trong draw_maze()
        self.current_cell_size = CELL_SIZE  # Default cell size, will be updated in draw_maze()
        
        self.original_width = self.width
        self.original_height = self.height
        
        # Button frame
        button_frame = tk.Frame(self.root, bg="#222222")
        button_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        
        self.gen_btn = tk.Button(button_frame, text="Tạo mê cung", command=self.generate_new_maze,
                                bg=COLOR_BUTTON, fg=COLOR_TEXT)
        self.gen_btn.pack(side=tk.LEFT, padx=5)

        self.random_start_btn = tk.Button(button_frame, text="Random điểm bắt đầu", command=self.randomize_start_position,
                         bg="#7c3aed", fg=COLOR_TEXT)
        self.random_start_btn.pack(side=tk.LEFT, padx=5)
        
        self.solve_btn = tk.Button(button_frame, text="Giải mê cung", command=self.solve_maze,
                                  bg=COLOR_BUTTON, fg=COLOR_TEXT)
        self.solve_btn.pack(side=tk.LEFT, padx=5)
        
        self.algo_label = tk.Label(button_frame, text="Thuật toán: BFS", bg="#222222", fg=COLOR_TEXT)
        self.algo_label.pack(side=tk.LEFT, padx=5)

        self.algo_btn = tk.Button(button_frame, text="Chọn thuật toán", command=self.show_algorithm_menu,
                                 bg=COLOR_BUTTON, fg=COLOR_TEXT)
        self.algo_btn.pack(side=tk.LEFT, padx=5)
        
        self.compare_btn = tk.Button(button_frame, text="So sánh BFS vs A*", command=self.compare_algorithms,
                                     bg="#16a34a", fg=COLOR_TEXT)
        self.compare_btn.pack(side=tk.LEFT, padx=5)
        
        self.waypoint_btn = tk.Button(button_frame, text="Chế độ điểm mốc: Tắt", command=self.toggle_waypoint_mode,
                                      bg="#8B0000", fg=COLOR_TEXT)
        self.waypoint_btn.pack(side=tk.LEFT, padx=5)

        self.waypoint_all_btn = tk.Button(
            button_frame,
            text="Chế độ qua tất cả mốc: Tắt",
            command=self.toggle_waypoint_all_mode,
            bg="#8B0000",
            fg=COLOR_TEXT,
            state=tk.DISABLED,
        )
        self.waypoint_all_btn.pack(side=tk.LEFT, padx=5)

        self.random_waypoint_btn = tk.Button(button_frame, text="Random điểm mốc", command=self.randomize_waypoint,
                            bg="#db2777", fg=COLOR_TEXT)
        self.random_waypoint_btn.pack(side=tk.LEFT, padx=5)
        
        # Status frame
        status_frame = tk.Frame(self.root, bg="#1a1a1a")
        status_frame.grid(row=2, column=0, sticky="ew")
        
        self.status_label = tk.Label(status_frame, text="Sẵn sàng.", bg="#1a1a1a", fg=COLOR_TEXT, wraplength=800)
        self.status_label.pack(fill=tk.X, padx=5, pady=2)
        
        self.stats_label = tk.Label(status_frame, text="Bước đi: -, Đã duyệt: -, Thời gian: -, Lối ra: -",
                                   bg="#1a1a1a", fg=COLOR_TEXT, wraplength=800)
        self.stats_label.pack(fill=tk.X, padx=5, pady=2)
        
        # Comparison frame
        comparison_frame = tk.Frame(self.root, bg="#1a1a1a", height=60)
        comparison_frame.grid(row=3, column=0, sticky="ew", padx=5, pady=5)
        comparison_frame.grid_propagate(False)  # Don't shrink
        
        self.comparison_label = tk.Label(comparison_frame, text="Kết quả so sánh sẽ hiển thị ở đây...", font=("Arial", 10),
                                        bg="#1a1a1a", fg="#FFD700", justify=tk.LEFT)
        self.comparison_label.pack(fill=tk.BOTH, padx=5, pady=5, expand=True)
        
        self.maze = []
        self.start = list(START_POSITION)
        self.exits = []
        self.enemies = []
        self.waypoints = []  # Điểm mốc phân tán trong mê cung
        self.waypoint_mode = False  # Bật/tắt chế độ điểm mốc
        self.waypoint_all_mode = False
        self.is_animating = False
        self.algorithm = "BFS"  # BFS or ASTAR
        self.comparison_results = None
        self.run_counter = 0
        self.last_visited: Set[Tuple[int, int]] = set()
        self.last_path: Set[Tuple[int, int]] = set()
        self.last_astar_visited: Set[Tuple[int, int]] = set()
        self.last_goal: Tuple[int, int] | None = None

        self.load_santa_image()
        
        self.generate_new_maze()
        self.draw_maze()
        
        # Force window update and trigger on_canvas_configure
        self.root.update()
        self.root.update_idletasks()
    
    def on_canvas_configure(self, event):
        """Handle canvas resize - scale maze to fit"""
        if self.is_animating:
            return

        # Recalculate cell size based on actual event dimensions
        if event.width > 100 and event.height > 100:
            cell_width = event.width / COLS
            cell_height = event.height / ROWS
            self.current_cell_size = min(cell_width, cell_height)
            
            # Redraw maze với kích thước mới
            if hasattr(self, 'maze') and len(self.maze) > 0:
                self.update_santa_image()
                self.draw_maze(
                    visited=self.last_visited,
                    path=self.last_path,
                    goal=self.last_goal,
                    astar_visited=self.last_astar_visited,
                    santa=self.last_santa,
                )

    def load_santa_image(self):
        if not os.path.exists(self.santa_image_path):
            self.santa_base_image = None
            self.santa_load_error = f"Khong tim thay anh: {self.santa_image_path}"
            return

        if PIL_AVAILABLE:
            try:
                self.santa_base_image = Image.open(self.santa_image_path).convert("RGBA")
                self.santa_load_error = None
            except Exception as exc:
                self.santa_base_image = None
                self.santa_load_error = f"Loi Pillow: {exc}"
        else:
            try:
                self.santa_base_image = tk.PhotoImage(file=self.santa_image_path)
                self.santa_load_error = None
            except Exception as exc:
                self.santa_base_image = None
                self.santa_load_error = f"Loi PhotoImage: {exc}"

    def update_santa_image(self):
        if not self.santa_base_image:
            return
        target_size = max(1, int(round(self.current_cell_size * SANTA_SCALE)))
        if self.santa_last_size == target_size and self.santa_tk_image is not None:
            return

        if PIL_AVAILABLE and isinstance(self.santa_base_image, Image.Image):
            resized = self.santa_base_image.resize((target_size, target_size), Image.LANCZOS)
            self.santa_tk_image = ImageTk.PhotoImage(resized)
        else:
            base = self.santa_base_image
            width = base.width()
            height = base.height()
            if width <= 0 or height <= 0:
                return

            scale = min(width / target_size, height / target_size)
            if scale >= 1:
                factor = max(1, int(round(scale)))
                self.santa_tk_image = base.subsample(factor, factor)
            else:
                factor = max(1, int(round(1 / scale)))
                self.santa_tk_image = base.zoom(factor, factor)

        self.santa_last_size = target_size

    def draw_santa_at(self, r: int, c: int):
        x, y = c * self.current_cell_size, r * self.current_cell_size
        size = self.current_cell_size * SANTA_SCALE
        offset = (size - self.current_cell_size) / 2
        draw_x = x - offset
        draw_y = y - offset
        if self.santa_tk_image:
            self.canvas.create_image(draw_x, draw_y, image=self.santa_tk_image, anchor="nw")
            return

        self.canvas.create_rectangle(draw_x, draw_y, draw_x + size, draw_y + size, fill="#ef4444", outline="")
        self.canvas.create_text(
            draw_x + size / 2,
            draw_y + size / 2,
            text="S",
            fill="#ffffff",
            font=("Arial", int(max(8, size / 2)), "bold"),
        )

    def ui_pump(self, delay_ms: int = 0):
        if delay_ms > 0:
            self.root.after(delay_ms)
        self.root.update_idletasks()
        self.root.update()

    def should_render_frame(self, index: int, total: int) -> bool:
        if total <= 0:
            return False
        return (index % ANIMATION_FRAME_SKIP == 0) or (index == total - 1)

    def append_run_history(self, mode: str, start_pos: Tuple[int, int], success: bool,
                           steps: int, visited: int, elapsed_ms: float,
                           target: Tuple[int, int] | None = None,
                           waypoint: Tuple[int, int] | None = None,
                           detail: str | None = None):
        self.run_counter += 1
        status = "OK" if success else "FAIL"
        waypoint_text = f", WP={waypoint}" if waypoint else ""
        target_text = f", DICH={target}" if target else ""
        detail_text = f" | {detail}" if detail else ""
        line = (
            f"#{self.run_counter} [{status}] {mode} | Algo={self.algorithm}"
            f" | Start={start_pos}{waypoint_text}{target_text}"
            f" | Buoc={steps} | Duyet={visited} | {elapsed_ms:.2f}ms{detail_text}\n"
        )

        self.history_text.config(state=tk.NORMAL)
        self.history_text.insert("1.0", line)
        self.history_text.config(state=tk.DISABLED)

    def append_compare_history(self, start_pos: Tuple[int, int],
                               bfs_steps: int, bfs_visited: int, bfs_time: float,
                               astar_steps: int, astar_visited: int, astar_time: float,
                               efficiency: float,
                               waypoint: Tuple[int, int] | None = None,
                               detail: str | None = None):
        self.run_counter += 1
        waypoint_text = f", WP={waypoint}" if waypoint else ""
        detail_text = f" | {detail}" if detail else ""
        line = (
            f"#{self.run_counter} [COMPARE] Algo=BFS_vs_A* | Start={start_pos}{waypoint_text}"
            f" | BFS: buoc={bfs_steps}, duyet={bfs_visited}, {bfs_time:.2f}ms"
            f" | A*: buoc={astar_steps}, duyet={astar_visited}, {astar_time:.2f}ms"
            f" | TIET_KIEM={efficiency:.1f}%{detail_text}\n"
        )

        self.history_text.config(state=tk.NORMAL)
        self.history_text.insert("1.0", line)
        self.history_text.config(state=tk.DISABLED)

    def clear_history(self):
        self.run_counter = 0
        self.history_text.config(state=tk.NORMAL)
        self.history_text.delete("1.0", tk.END)
        self.history_text.insert(tk.END, "- Lich su da duoc xoa.\n")
        self.history_text.config(state=tk.DISABLED)

    def in_bounds(self, r: int, c: int) -> bool:
        return 0 <= r < ROWS and 0 <= c < COLS

    def neighbors4(self, r: int, c: int) -> List[Tuple[int, int]]:
        neighbors = [(r-1, c), (r+1, c), (r, c-1), (r, c+1)]
        return [(nr, nc) for nr, nc in neighbors if self.in_bounds(nr, nc)]

    def create_grid(self, fill_value: int = 1) -> List[List[int]]:
        return [[fill_value] * COLS for _ in range(ROWS)]

    def generate_maze_base(self) -> List[List[int]]:
        grid = self.create_grid(1)
        stack = [list(START_POSITION)]
        grid[START_POSITION[0]][START_POSITION[1]] = 0

        while stack:
            r, c = stack[-1]
            candidates = [
                (r - 2, c),
                (r + 2, c),
                (r, c - 2),
                (r, c + 2),
            ]
            candidates = [(nr, nc) for nr, nc in candidates 
                         if 0 < nr < ROWS - 1 and 0 < nc < COLS - 1 and grid[nr][nc] == 1]

            if not candidates:
                stack.pop()
                continue

            nr, nc = random.choice(candidates)
            wall_r, wall_c = (r + nr) // 2, (c + nc) // 2
            grid[wall_r][wall_c] = 0
            grid[nr][nc] = 0
            stack.append((nr, nc))

        return grid

    def bfs_distances(self, grid: List[List[int]], source: Tuple[int, int]) -> List[List[int]]:
        dist = [[-1] * COLS for _ in range(ROWS)]
        q = deque([source])
        dist[source[0]][source[1]] = 0

        while q:
            r, c = q.popleft()
            for nr, nc in self.neighbors4(r, c):
                if grid[nr][nc] == 0 and dist[nr][nc] == -1:
                    dist[nr][nc] = dist[r][c] + 1
                    q.append((nr, nc))

        return dist

    def place_distinct_exits(self, grid: List[List[int]], source: Tuple[int, int], 
                            desired: int = EXIT_COUNT) -> List[Tuple[int, int]]:
        dist = self.bfs_distances(grid, source)
        candidates = []
        
        # Find cells inside the maze at various distances from source
        for r in range(5, ROWS - 5):  # Avoid edges
            for c in range(5, COLS - 5):
                if grid[r][c] == 0 and dist[r][c] > 0:  # Must be a path
                    candidates.append(((r, c), dist[r][c]))
        
        # Sort by distance and select diverse positions
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        selected = []
        used_positions = {source}  # Don't place exit at start
        MIN_EXIT_DISTANCE = 15  # Minimum distance between exits
        
        for exit_pos, distance in candidates:
            if len(selected) >= desired:
                break
            
            # Check if this exit is far enough from all selected exits
            is_far_enough = True
            for selected_exit in selected:
                manhattan_dist = abs(exit_pos[0] - selected_exit[0]) + abs(exit_pos[1] - selected_exit[1])
                if manhattan_dist < MIN_EXIT_DISTANCE:
                    is_far_enough = False
                    break
            
            if is_far_enough and exit_pos not in used_positions:
                selected.append(exit_pos)
                used_positions.add(exit_pos)
        
        # If not enough exits, relax the distance requirement
        if len(selected) < desired:
            candidates.sort(key=lambda x: x[1], reverse=True)
            MIN_EXIT_DISTANCE = 10  # Relax requirement
            
            for exit_pos, distance in candidates:
                if len(selected) >= desired:
                    break
                if exit_pos in used_positions:
                    continue
                
                is_far_enough = True
                for selected_exit in selected:
                    manhattan_dist = abs(exit_pos[0] - selected_exit[0]) + abs(exit_pos[1] - selected_exit[1])
                    if manhattan_dist < MIN_EXIT_DISTANCE:
                        is_far_enough = False
                        break
                
                if is_far_enough:
                    selected.append(exit_pos)
                    used_positions.add(exit_pos)
        
        return selected

    def carve_loops(self, grid: List[List[int]]):
        wall_cells = []
        for r in range(1, ROWS - 1):
            for c in range(1, COLS - 1):
                if grid[r][c] != 1:
                    continue
                ns = [(nr, nc) for nr, nc in self.neighbors4(r, c) if grid[nr][nc] == 0]
                if len(ns) >= 2:
                    vert = [n for n in ns if n[0] != r]
                    horiz = [n for n in ns if n[1] != c]
                    if (len(vert) == 2 and len(horiz) == 0) or (len(horiz) == 2 and len(vert) == 0):
                        wall_cells.append((r, c))

        random.shuffle(wall_cells)
        target = int(len(wall_cells) * LOOP_CARVE_RATE)
        for r, c in wall_cells[:target]:
            grid[r][c] = 0

    def braid_maze(self, grid: List[List[int]]):
        dead_ends = []
        for r in range(1, ROWS - 1):
            for c in range(1, COLS - 1):
                if grid[r][c] != 0:
                    continue
                ns = [(nr, nc) for nr, nc in self.neighbors4(r, c) if grid[nr][nc] == 0]
                if len(ns) == 1:
                    dead_ends.append((r, c))

        random.shuffle(dead_ends)
        target = int(len(dead_ends) * BRAID_RATE)
        for r, c in dead_ends[:target]:
            wall_neighbors = []
            for nr, nc in [(r-1, c), (r+1, c), (r, c-1), (r, c+1)]:
                if not self.in_bounds(nr, nc) or grid[nr][nc] != 1:
                    continue
                wall_neighbors2 = [(nnr, nnc) for nnr, nnc in self.neighbors4(nr, nc) if grid[nnr][nnc] == 0]
                if wall_neighbors2:
                    wall_neighbors.append((nr, nc))
            
            if wall_neighbors:
                wr, wc = random.choice(wall_neighbors)
                grid[wr][wc] = 0

    def place_enemies(self, grid: List[List[int]], source: Tuple[int, int], 
                     existing_exits: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        dist = self.bfs_distances(grid, source)
        used_keys = {source, *existing_exits}
        
        candidates = []
        for r in range(1, ROWS - 1):
            for c in range(1, COLS - 1):
                if (r, c) in used_keys or grid[r][c] != 0:
                    continue
                d = dist[r][c]
                if d >= ENEMY_MIN_DISTANCE:
                    candidates.append(((r, c), d))
        
        candidates.sort(key=lambda x: x[1], reverse=True)
        selected = []
        for pos, _ in candidates:
            if len(selected) >= ENEMY_COUNT:
                break
            selected.append(pos)
            used_keys.add(pos)
        
        return selected

    def pick_random_start(self, grid: List[List[int]], blocked: Set[Tuple[int, int]] | None = None) -> Tuple[int, int] | None:
        if blocked is None:
            blocked = set()

        candidates = []
        for r in range(1, ROWS - 1):
            for c in range(1, COLS - 1):
                if grid[r][c] == 0 and (r, c) not in blocked:
                    candidates.append((r, c))

        if not candidates:
            return None

        return random.choice(candidates)

    def randomize_start_position(self):
        if self.is_animating:
            return
        if not self.maze:
            self.status_label.config(text="Chưa có mê cung để random điểm bắt đầu.")
            return

        blocked = set(self.exits) | set(self.enemies) | set(self.waypoints)
        new_start = self.pick_random_start(self.maze, blocked)
        if new_start is None:
            self.status_label.config(text="Không tìm được vị trí bắt đầu hợp lệ.")
            return

        self.start = [new_start[0], new_start[1]]
        self.status_label.config(text=f"Đã random điểm bắt đầu: {new_start}")
        self.stats_label.config(text="Bước đi: -, Đã duyệt: -, Thời gian: -, Lối ra: -")
        self.draw_maze()

    def randomize_waypoint(self):
        if self.is_animating:
            return
        if not self.maze:
            self.status_label.config(text="Chưa có mê cung để random điểm mốc.")
            return

        blocked = list(self.enemies)
        new_waypoints = self.generate_waypoints(self.maze, tuple(self.start), self.exits, blocked)
        if not new_waypoints:
            self.status_label.config(text="Không tìm được vị trí điểm mốc hợp lệ.")
            return

        self.waypoints = new_waypoints
        if self.waypoint_mode:
            self.status_label.config(text=f"Đã random {len(self.waypoints)} điểm mốc.")
        else:
            self.status_label.config(text=f"Đã random {len(self.waypoints)} điểm mốc (bật chế độ để hiển thị)")
        self.draw_maze()

    def generate_new_maze(self):
        for attempt in range(MAX_GENERATION_ATTEMPTS):
            grid = self.generate_maze_base()
            self.carve_loops(grid)
            self.braid_maze(grid)

            source = self.pick_random_start(grid)
            if source is None:
                continue
            exits = self.place_distinct_exits(grid, source, EXIT_COUNT)
            enemies = self.place_enemies(grid, source, exits)
            waypoints = self.generate_waypoints(grid, source, exits, enemies)
            
            if len(exits) >= 2:
                self.maze = grid
                self.start = list(source)
                self.exits = exits
                self.enemies = enemies
                self.waypoints = waypoints
                self.status_label.config(text="Đã tạo mê cung mới.")
                self.stats_label.config(text="Bước đi: -, Đã duyệt: -, Thời gian: -, Lối ra: -")
                self.draw_maze()
                return

        grid = self.generate_maze_base()
        self.carve_loops(grid)
        self.braid_maze(grid)
        source = self.pick_random_start(grid)
        if source is None:
            source = tuple(START_POSITION)
        exits = self.place_distinct_exits(grid, source, 2)
        enemies = self.place_enemies(grid, source, exits)
        waypoints = self.generate_waypoints(grid, source, exits, enemies)
        
        self.maze = grid
        self.start = list(source)
        self.exits = exits
        self.enemies = enemies
        self.waypoints = waypoints
        self.status_label.config(text="Đã tạo mê cung mới.")
        self.stats_label.config(text="Bước đi: -, Đã duyệt: -, Thời gian: -, Lối ra: -")
        self.draw_maze()

    def solve_bfs(self, grid: List[List[int]], source: Tuple[int, int], 
                  goals: List[Tuple[int, int]]) -> Tuple[List[Tuple[int, int]], 
                                                          List[Tuple[int, int]], 
                                                          Tuple[int, int] | None]:
        goal_set = set(goals)
        q = deque([source])
        visited_set = {source}
        parent = {source: None}
        visited_order = []

        while q:
            r, c = q.popleft()
            visited_order.append((r, c))
            
            if (r, c) in goal_set:
                path = []
                current = (r, c)
                while current is not None:
                    path.append(current)
                    current = parent[current]
                path.reverse()
                return visited_order, path, (r, c)

            for nr, nc in self.neighbors4(r, c):
                if grid[nr][nc] == 0 and (nr, nc) not in visited_set:
                    visited_set.add((nr, nc))
                    parent[(nr, nc)] = (r, c)
                    q.append((nr, nc))

        return visited_order, [], None

    def solve_astar(self, grid: List[List[int]], source: Tuple[int, int], 
                    goals: List[Tuple[int, int]]) -> Tuple[List[Tuple[int, int]], 
                                                            List[Tuple[int, int]], 
                                                            Tuple[int, int] | None]:
        goal_set = set(goals)
        
        def heuristic(r: int, c: int) -> int:
            return min(abs(r - gr) + abs(c - gc) for gr, gc in goals)
        
        open_set = [(heuristic(source[0], source[1]), source)]
        g_score = {source: 0}
        parent = {source: None}
        closed = set()
        visited_order = []

        while open_set:
            open_set.sort(key=lambda x: x[0])
            _, current = open_set.pop(0)
            r, c = current
            
            if current in closed:
                continue
            
            closed.add(current)
            visited_order.append(current)

            if current in goal_set:
                path = []
                node = current
                while node is not None:
                    path.append(node)
                    node = parent[node]
                path.reverse()
                return visited_order, path, current

            current_g = g_score[current]
            for nr, nc in self.neighbors4(r, c):
                if grid[nr][nc] == 0 and (nr, nc) not in closed:
                    tentative_g = current_g + 1
                    if (nr, nc) not in g_score or tentative_g < g_score[(nr, nc)]:
                        g_score[(nr, nc)] = tentative_g
                        parent[(nr, nc)] = current
                        h = heuristic(nr, nc)
                        open_set.append((tentative_g + h, (nr, nc)))

        return visited_order, [], None

    def draw_maze(self, visited: Set[Tuple[int, int]] = None, 
                  path: Set[Tuple[int, int]] = None,
                  goal: Tuple[int, int] = None,
                  astar_visited: Set[Tuple[int, int]] = None,
                  santa: Tuple[int, int] | None = None):
        if visited is None:
            visited = set()
        if path is None:
            path = set()
        if astar_visited is None:
            astar_visited = set()

        # Keep last rendered state so resize/configure redraw does not wipe animation result.
        self.last_visited = set(visited)
        self.last_path = set(path)
        self.last_astar_visited = set(astar_visited)
        self.last_goal = goal
        self.last_santa = santa

        # Get canvas dimensions using update_idletasks to ensure valid values
        self.canvas.update_idletasks()
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width > 100 and canvas_height > 100:
            # Calculate cell size to fill available space
            cell_width = canvas_width / COLS
            cell_height = canvas_height / ROWS
            
            # Use min to keep aspect ratio square and fit in canvas
            self.current_cell_size = min(cell_width, cell_height)

        self.update_santa_image()

        self.canvas.delete("all")

        for r in range(ROWS):
            for c in range(COLS):
                x, y = c * self.current_cell_size, r * self.current_cell_size
                if self.maze[r][c] == 1:
                    color = COLOR_WALL
                elif (r, c) in path:
                    color = COLOR_SOLUTION
                elif (r, c) in astar_visited:
                    color = COLOR_VISITED_ASTAR
                elif (r, c) in visited:
                    color = COLOR_VISITED_BFS
                else:
                    color = COLOR_PATH
                
                self.canvas.create_rectangle(x, y, x + self.current_cell_size, y + self.current_cell_size, fill=color, outline="")

        # Draw exits
        for er, ec in self.exits:
            x, y = ec * self.current_cell_size, er * self.current_cell_size
            self.canvas.create_rectangle(x, y, x + self.current_cell_size, y + self.current_cell_size, fill=COLOR_EXIT, outline="")

        # Draw enemies
        for er, ec in self.enemies:
            x, y = ec * self.current_cell_size, er * self.current_cell_size
            self.canvas.create_rectangle(x, y, x + self.current_cell_size, y + self.current_cell_size, fill=COLOR_ENEMY, outline="")

        # Draw waypoints if mode enabled
        if self.waypoint_mode:
            for wr, wc in self.waypoints:
                x, y = wc * self.current_cell_size, wr * self.current_cell_size
                self.canvas.create_rectangle(x, y, x + self.current_cell_size, y + self.current_cell_size, fill=COLOR_WAYPOINT, outline="")

        # Draw start
        sr, sc = self.start
        x, y = sc * self.current_cell_size, sr * self.current_cell_size
        self.canvas.create_rectangle(x, y, x + self.current_cell_size, y + self.current_cell_size, fill=COLOR_START, outline="")

        # Draw goal
        if goal:
            gr, gc = goal
            x, y = gc * self.current_cell_size, gr * self.current_cell_size
            self.canvas.create_rectangle(x, y, x + self.current_cell_size, y + self.current_cell_size, fill=COLOR_GOAL, outline="")

        if santa:
            self.draw_santa_at(santa[0], santa[1])

        self.root.update_idletasks()

    def set_algorithm(self, algo: str):
        self.algorithm = algo
        self.algo_label.config(text=f"Thuật toán: {self.algorithm}")
        self.status_label.config(text=f"Đã chọn thuật toán: {self.algorithm}")

    def show_algorithm_menu(self):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="BFS", command=lambda: self.set_algorithm("BFS"))
        menu.add_command(label="A*", command=lambda: self.set_algorithm("ASTAR"))

        x = self.algo_btn.winfo_rootx()
        y = self.algo_btn.winfo_rooty() + self.algo_btn.winfo_height()
        menu.tk_popup(x, y)
        menu.grab_release()

    def solve_maze(self):
        if self.is_animating:
            return

        if self.waypoint_all_mode:
            if not self.waypoints:
                self.status_label.config(text="Không có điểm mốc được sinh.")
                return

            targets = self.exits
            if not targets:
                self.status_label.config(text="Không có mục tiêu hợp lệ.")
                return

            self.draw_maze()
            self.status_label.config(text=f"Đang giải mê cung qua tất cả điểm mốc bằng {self.algorithm}...")
            self.is_animating = True
            self.ui_pump()

            result = self.solve_route_all_waypoints(self.algorithm, self.waypoints, targets)
            if not result:
                self.status_label.config(text="Không tìm thấy đường đi qua tất cả điểm mốc.")
                self.draw_maze()
                self.append_run_history(
                    mode="WAYPOINT_ALL",
                    start_pos=tuple(self.start),
                    success=False,
                    steps=0,
                    visited=0,
                    elapsed_ms=0,
                    target=None,
                    waypoint=None,
                    detail="Không có đường hợp lệ qua tất cả điểm mốc.",
                )
                self.is_animating = False
                return

            visited_order = result["visited_order"]
            full_path = result["full_path"]
            exit_pos = result["target"]
            total_time = result["total_time"]
            step_count = result["total_steps"]
            order = result["order"]

            visited_set = set()
            for idx, (r, c) in enumerate(visited_order):
                visited_set.add((r, c))
                if self.should_render_frame(idx, len(visited_order)):
                    self.draw_maze(visited=visited_set, goal=exit_pos)
                    self.ui_pump(VISITED_CELL_DELAY_MS)

            path_set = set()
            for idx, (r, c) in enumerate(full_path):
                path_set.add((r, c))
                if self.should_render_frame(idx, len(full_path)):
                    self.draw_maze(visited=visited_set, path=path_set, goal=exit_pos, santa=(r, c))
                    self.ui_pump(PATH_CELL_DELAY_MS)

            if full_path:
                sr, sc = full_path[-1]
                self.draw_maze(visited=visited_set, path=path_set, goal=exit_pos, santa=(sr, sc))

            self.is_animating = False
            order_text = " -> ".join([f"{wp}" for wp in order])
            self.status_label.config(text=f"Đã đi qua tất cả điểm mốc. Thứ tự: {order_text}")
            self.stats_label.config(
                text=f"Bước đi: {step_count}, Đã duyệt: {len(visited_order)}, Thời gian: {total_time:.2f} ms, Đích: {exit_pos}"
            )
            self.append_run_history(
                mode="WAYPOINT_ALL",
                start_pos=tuple(self.start),
                success=True,
                steps=step_count,
                visited=len(visited_order),
                elapsed_ms=total_time,
                target=exit_pos,
                waypoint=None,
                detail=f"Thu tu: {order_text}",
            )
            return

        if self.waypoint_mode:
            # Chế độ điểm mốc: bắt buộc đi qua 1 waypoint rồi mới tới đích
            if not self.waypoints:
                self.status_label.config(text="Không có điểm mốc được sinh.")
                return
            
            self.draw_maze()
            self.status_label.config(text=f"Đang giải mê cung qua điểm mốc bằng {self.algorithm}...")
            self.is_animating = True
            self.ui_pump()

            targets = self.exits + self.enemies

            candidate_results = []
            for waypoint in self.waypoints:
                start_time = time.time()
                if self.algorithm == "BFS":
                    visited_1, path_1, reached_wp = self.solve_bfs(self.maze, tuple(self.start), [waypoint])
                    visited_2, path_2, exit_pos = self.solve_bfs(self.maze, waypoint, targets)
                else:
                    visited_1, path_1, reached_wp = self.solve_astar(self.maze, tuple(self.start), [waypoint])
                    visited_2, path_2, exit_pos = self.solve_astar(self.maze, waypoint, targets)
                elapsed_total = (time.time() - start_time) * 1000

                if not path_1 or not reached_wp or not path_2 or not exit_pos:
                    continue

                total_steps = len(path_1) + len(path_2) - 1
                candidate_results.append({
                    "waypoint": waypoint,
                    "visited_1": visited_1,
                    "path_1": path_1,
                    "visited_2": visited_2,
                    "path_2": path_2,
                    "exit_pos": exit_pos,
                    "total_steps": total_steps,
                    "elapsed_ms": elapsed_total,
                })

            if not candidate_results:
                self.status_label.config(text="Không tìm thấy đường đi qua bất kỳ điểm mốc nào.")
                self.draw_maze()
                self.append_run_history(
                    mode="WAYPOINT",
                    start_pos=tuple(self.start),
                    success=False,
                    steps=0,
                    visited=0,
                    elapsed_ms=0,
                    target=None,
                    waypoint=None,
                    detail="Không có waypoint nào nối được start tới đích.",
                )
                self.is_animating = False
                return

            candidate_results.sort(key=lambda item: item["total_steps"])
            best = candidate_results[0]
            second_best_steps = candidate_results[1]["total_steps"] if len(candidate_results) > 1 else None
            waypoint = best["waypoint"]
            visited_1 = best["visited_1"]
            path_1 = best["path_1"]
            visited_2 = best["visited_2"]
            path_2 = best["path_2"]
            exit_pos = best["exit_pos"]
            total_time = best["elapsed_ms"]
            visited_order = list(dict.fromkeys(visited_1 + visited_2))
            full_path = path_1 + path_2[1:]

            if second_best_steps is None:
                reason_text = f"Chọn waypoint {waypoint} vì đây là waypoint duy nhất đi tới đích."
                saving_text = "không có waypoint khác để so sánh"
            else:
                saving_steps = second_best_steps - best["total_steps"]
                reason_text = (
                    f"Chọn waypoint {waypoint} vì tổng đường đi ngắn nhất ({best['total_steps']} bước), "
                    f"ngắn hơn waypoint tốt thứ 2 {saving_steps} bước."
                )
                saving_text = f"ngắn hơn waypoint tốt thứ 2 {saving_steps} bước"

            # Animate visited cells trước
            visited_set = set()
            for idx, (r, c) in enumerate(visited_order):
                visited_set.add((r, c))
                if self.should_render_frame(idx, len(visited_order)):
                    self.draw_maze(visited=visited_set, goal=exit_pos)
                    self.ui_pump(VISITED_CELL_DELAY_MS)
            
            # Animate path sau
            path_set = set()
            for idx, (r, c) in enumerate(full_path):
                path_set.add((r, c))
                if self.should_render_frame(idx, len(full_path)):
                    self.draw_maze(visited=visited_set, path=path_set, goal=exit_pos, santa=(r, c))
                    self.ui_pump(PATH_CELL_DELAY_MS)

            if full_path:
                sr, sc = full_path[-1]
                self.draw_maze(visited=visited_set, path=path_set, goal=exit_pos, santa=(sr, sc))

            self.is_animating = False
            
            step_count = max(len(full_path) - 1, 0)
            self.status_label.config(text=f"Đã đi qua điểm mốc {waypoint}. {reason_text}")
            self.stats_label.config(text=f"Bước đi: {step_count}, Đã duyệt: {len(visited_order)}, Thời gian: {total_time:.2f} ms, Đích: {exit_pos}")
            self.append_run_history(
                mode="WAYPOINT",
                start_pos=tuple(self.start),
                success=True,
                steps=step_count,
                visited=len(visited_order),
                elapsed_ms=total_time,
                target=exit_pos,
                waypoint=waypoint,
                detail=f"{reason_text} | {saving_text}",
            )
            return
        
        # Chế độ bình thường
        targets = self.exits + self.enemies
        if not targets:
            self.status_label.config(text="Không có mục tiêu hợp lệ.")
            return
        
        self.draw_maze()
        self.status_label.config(text=f"Đang giải mê cung bằng {self.algorithm}...")
        self.is_animating = True
        self.ui_pump()
        
        start_time = time.time()
        
        if self.algorithm == "BFS":
            visited_order, path, exit_pos = self.solve_bfs(self.maze, tuple(self.start), targets)
        else:
            visited_order, path, exit_pos = self.solve_astar(self.maze, tuple(self.start), targets)
        
        elapsed = (time.time() - start_time) * 1000

        if not path or not exit_pos:
            self.status_label.config(text="Không tìm thấy đường đi.")
            self.stats_label.config(text=f"Bước đi: -, Đã duyệt: {len(visited_order)}, Thời gian: {elapsed:.2f} ms, Lối ra: -")
            self.draw_maze()
            self.append_run_history(
                mode="NORMAL",
                start_pos=tuple(self.start),
                success=False,
                steps=0,
                visited=len(visited_order),
                elapsed_ms=elapsed,
            )
            self.is_animating = False
            return

        # Animate visited cells
        visited_set = set()
        for idx, (r, c) in enumerate(visited_order):
            visited_set.add((r, c))
            if self.should_render_frame(idx, len(visited_order)):
                self.draw_maze(visited=visited_set, goal=exit_pos)
                self.ui_pump(VISITED_CELL_DELAY_MS)

        # Animate path
        path_set = set()
        for idx, (r, c) in enumerate(path):
            path_set.add((r, c))
            if self.should_render_frame(idx, len(path)):
                self.draw_maze(visited=visited_set, path=path_set, goal=exit_pos, santa=(r, c))
                self.ui_pump(PATH_CELL_DELAY_MS)

        if path:
            sr, sc = path[-1]
            self.draw_maze(visited=visited_set, path=path_set, goal=exit_pos, santa=(sr, sc))

        self.is_animating = False

        step_count = max(len(path) - 1, 0)
        is_exit = exit_pos in self.exits
        goal_type = "Lối ra" if is_exit else "Địch"
        self.status_label.config(text=f"Hoàn thành bằng {self.algorithm}.")
        self.stats_label.config(text=f"Bước đi: {step_count}, Đã duyệt: {len(visited_order)}, Thời gian: {elapsed:.2f} ms, {goal_type}: {exit_pos}")
        self.append_run_history(
            mode="NORMAL",
            start_pos=tuple(self.start),
            success=True,
            steps=step_count,
            visited=len(visited_order),
            elapsed_ms=elapsed,
            target=exit_pos,
        )

    def compare_algorithms(self):
        """So sánh BFS và A* trên cùng một mê cung"""
        if self.is_animating:
            return

        targets = self.exits + self.enemies
        if not targets:
            self.status_label.config(text="Không có mục tiêu hợp lệ.")
            return

        self.draw_maze()
        self.status_label.config(text="Đang so sánh BFS và A*...")
        self.comparison_label.config(text="Dang tinh toan...")
        self.is_animating = True
        self.ui_pump()

        compare_detail = None
        if self.waypoint_mode and self.waypoints:
            bfs_result = self.solve_route_through_waypoints("BFS", self.waypoints, targets)
            astar_result = self.solve_route_through_waypoints("ASTAR", self.waypoints, targets)

            if bfs_result:
                bfs_visited = bfs_result["visited_order"]
                bfs_path = bfs_result["full_path"]
                bfs_exit = bfs_result["target"]
                bfs_steps = bfs_result["total_steps"]
                bfs_time = bfs_result["total_time"]
                bfs_waypoint = bfs_result["waypoint"]
                bfs_saved = bfs_result.get("saved_steps")
            else:
                bfs_visited = []
                bfs_path = []
                bfs_exit = None
                bfs_steps = 0
                bfs_time = 0.0
                bfs_waypoint = None
                bfs_saved = None

            if astar_result:
                astar_visited = astar_result["visited_order"]
                astar_path = astar_result["full_path"]
                astar_exit = astar_result["target"]
                astar_steps = astar_result["total_steps"]
                astar_time = astar_result["total_time"]
                astar_waypoint = astar_result["waypoint"]
                astar_saved = astar_result.get("saved_steps")
            else:
                astar_visited = []
                astar_path = []
                astar_exit = None
                astar_steps = 0
                astar_time = 0.0
                astar_waypoint = None
                astar_saved = None

            bfs_saved_text = f"{bfs_saved} bước" if bfs_saved is not None else "không có mốc so sánh"
            astar_saved_text = f"{astar_saved} bước" if astar_saved is not None else "không có mốc so sánh"
            compare_detail = (
                f"BFS duyệt {len(self.waypoints)} waypoint, chọn WP={bfs_waypoint}, tiết kiệm={bfs_saved_text} | "
                f"A* duyệt {len(self.waypoints)} waypoint, chọn WP={astar_waypoint}, tiết kiệm={astar_saved_text}"
            )
            self.status_label.config(text="Đang duyệt 1 lần qua toàn bộ waypoint cho BFS/A* trước khi chọn mốc tối ưu...")
            if bfs_result:
                self.animate_waypoint_scan(bfs_result.get("scan_visited", []), "BFS")
            if astar_result:
                self.animate_waypoint_scan(astar_result.get("scan_visited", []), "ASTAR")
        else:
            start_time = time.time()
            bfs_visited, bfs_path, bfs_exit = self.solve_bfs(self.maze, tuple(self.start), targets)
            bfs_time = (time.time() - start_time) * 1000
            bfs_steps = max(len(bfs_path) - 1, 0) if bfs_path else 0

            start_time = time.time()
            astar_visited, astar_path, astar_exit = self.solve_astar(self.maze, tuple(self.start), targets)
            astar_time = (time.time() - start_time) * 1000
            astar_steps = max(len(astar_path) - 1, 0) if astar_path else 0
            self.status_label.config(text="Dang so sanh... Xem ket qua phia duoi")

        if len(bfs_visited) > 0:
            astar_efficiency = (len(bfs_visited) - len(astar_visited)) / len(bfs_visited) * 100
        else:
            astar_efficiency = 0

        self.comparison_results = {
            'bfs_steps': bfs_steps,
            'bfs_visited': len(bfs_visited),
            'bfs_time': bfs_time,
            'bfs_path': bfs_path,
            'astar_steps': astar_steps,
            'astar_visited': len(astar_visited),
            'astar_time': astar_time,
            'astar_path': astar_path,
            'efficiency': astar_efficiency
        }

        compare_waypoint = bfs_waypoint if (self.waypoint_mode and self.waypoints) else None
        self.append_compare_history(
            start_pos=tuple(self.start),
            bfs_steps=bfs_steps,
            bfs_visited=len(bfs_visited),
            bfs_time=bfs_time,
            astar_steps=astar_steps,
            astar_visited=len(astar_visited),
            astar_time=astar_time,
            efficiency=astar_efficiency,
            waypoint=compare_waypoint,
            detail=compare_detail,
        )

        self.display_comparison()
        self.ui_pump()

        if self.waypoint_mode and self.waypoints:
            bfs_visited_set = set(bfs_result.get("scan_visited", []) if bfs_result else [])
            bfs_path_set = set()
            for idx, (r, c) in enumerate(bfs_path):
                bfs_path_set.add((r, c))
                if self.should_render_frame(idx, len(bfs_path)):
                    self.draw_maze(visited=bfs_visited_set, path=bfs_path_set, goal=bfs_exit)
                    self.ui_pump(3)

            self.ui_pump(200)

            astar_visited_set = set(astar_result.get("scan_visited", []) if astar_result else [])
            astar_path_set = set()
            for idx, (r, c) in enumerate(astar_path):
                astar_path_set.add((r, c))
                if self.should_render_frame(idx, len(astar_path)):
                    self.draw_maze(astar_visited=astar_visited_set, path=astar_path_set, goal=astar_exit)
                    self.ui_pump(3)
        else:
            bfs_visited_set = set()
            for idx, (r, c) in enumerate(bfs_visited):
                bfs_visited_set.add((r, c))
                if self.should_render_frame(idx, len(bfs_visited)):
                    self.draw_maze(visited=bfs_visited_set, goal=bfs_exit)
                    self.ui_pump(1)

            self.ui_pump(200)

            astar_visited_set = set()
            for idx, (r, c) in enumerate(astar_visited):
                astar_visited_set.add((r, c))
                if self.should_render_frame(idx, len(astar_visited)):
                    self.draw_maze(visited=bfs_visited_set, astar_visited=astar_visited_set, goal=astar_exit)
                    self.ui_pump(1)

            astar_path_set = set()
            for idx, (r, c) in enumerate(astar_path):
                astar_path_set.add((r, c))
                if self.should_render_frame(idx, len(astar_path)):
                    self.draw_maze(visited=bfs_visited_set, astar_visited=astar_visited_set, path=astar_path_set, goal=astar_exit)
                    self.ui_pump(5)

        self.is_animating = False
        self.status_label.config(text="Hoan thanh so sanh. Xem ket qua phia duoi.")

    def display_comparison(self):
        """Hiển thị kết quả so sánh BFS vs A*"""
        if self.comparison_results is None:
            text = "Khong co du lieu so sanh"
            self.comparison_label.config(text=text, fg="#FF6B6B")
            self.root.update_idletasks()
            return
        
        r = self.comparison_results
        # Create readable comparison text
        comparison_text = (
            f"BFS(Cyan):  {r['bfs_steps']} buoc | {r['bfs_visited']} o duyet | {r['bfs_time']:.2f}ms  |  "
            f"A*(Lime):  {r['astar_steps']} buoc | {r['astar_visited']} o duyet | {r['astar_time']:.2f}ms  |  "
            f"A* TIET KIEM {r['efficiency']:.1f}%"
        )
        
        self.comparison_label.config(text=comparison_text, fg="#FFD700")
        self.root.update_idletasks()

    def generate_waypoints(self, grid: List[List[int]], source: Tuple[int, int], 
                          exits: List[Tuple[int, int]],
                          blocked: List[Tuple[int, int]] | None = None) -> List[Tuple[int, int]]:
        """Sinh ra 4 điểm mốc ngẫu nhiên, không trùng start/exit/enemy"""
        used_positions = {source}
        used_positions.update(exits)
        if blocked:
            used_positions.update(blocked)
        all_paths = []
        for r in range(1, ROWS - 1):
            for c in range(1, COLS - 1):
                if grid[r][c] == 0 and (r, c) not in used_positions:
                    all_paths.append((r, c))
        if len(all_paths) < WAYPOINT_COUNT:
            return all_paths
        return random.sample(all_paths, WAYPOINT_COUNT)

    def toggle_waypoint_mode(self):
        """Bật/tắt chế độ điểm mốc"""
        self.waypoint_mode = not self.waypoint_mode
        if not self.waypoint_mode and self.waypoint_all_mode:
            self.waypoint_all_mode = False
            self.waypoint_all_btn.config(text="Chế độ qua tất cả mốc: Tắt", bg="#8B0000")
        mode_text = "Bật" if self.waypoint_mode else "Tắt"
        self.waypoint_btn.config(text=f"Chế độ điểm mốc: {mode_text}",
                                bg="#228B22" if self.waypoint_mode else "#8B0000")
        if self.waypoint_mode:
            status = f"Chế độ điểm mốc: {mode_text} ({len(self.waypoints)} điểm mốc)"
        else:
            self.waypoint_all_mode = False
            self.waypoint_all_btn.config(text="Chế độ qua tất cả mốc: Tắt", bg="#8B0000")
            status = "Chế độ bình thường"
        self.waypoint_all_btn.config(state=tk.NORMAL if self.waypoint_mode else tk.DISABLED)
        self.status_label.config(text=status)
        self.draw_maze()

    def toggle_waypoint_all_mode(self):
        """Bật/tắt chế độ đi qua tất cả điểm mốc"""
        if not self.waypoint_mode:
            self.status_label.config(text="Bật chế độ điểm mốc trước khi dùng chế độ qua tất cả mốc.")
            return
        self.waypoint_all_mode = not self.waypoint_all_mode
        mode_text = "Bật" if self.waypoint_all_mode else "Tắt"
        self.waypoint_all_btn.config(
            text=f"Chế độ qua tất cả mốc: {mode_text}",
            bg="#228B22" if self.waypoint_all_mode else "#8B0000",
        )
        if self.waypoint_all_mode:
            status = f"Chế độ qua tất cả mốc: {mode_text} ({len(self.waypoints)} điểm mốc)"
        else:
            status = f"Chế độ điểm mốc: Bật ({len(self.waypoints)} điểm mốc)"
        self.status_label.config(text=status)
        self.draw_maze()

    def nearest_neighbor_order(self, points: List[Tuple[int, int]], 
                              start: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Tìm thứ tự tối ưu các điểm bằng nearest neighbor heuristic"""
        if not points:
            return []
        
        ordered = []
        remaining = set(points)
        current = start
        
        while remaining:
            # Tìm điểm gần nhất từ vị trí hiện tại
            nearest = min(remaining, key=lambda p: abs(p[0] - current[0]) + abs(p[1] - current[1]))
            ordered.append(nearest)
            remaining.remove(nearest)
            current = nearest
        
        return ordered

    def solve_segment(self, algorithm: str, source: Tuple[int, int], goals: List[Tuple[int, int]]):
        if algorithm == "BFS":
            return self.solve_bfs(self.maze, source, goals)
        return self.solve_astar(self.maze, source, goals)

    def bfs_scan_from_source(self, source: Tuple[int, int], waypoints: List[Tuple[int, int]] | None = None):
        dist = [[-1] * COLS for _ in range(ROWS)]
        parent: dict[Tuple[int, int], Tuple[int, int] | None] = {source: None}
        q = deque([source])
        dist[source[0]][source[1]] = 0
        visited_order = []
        waypoint_set = set(waypoints or [])
        found_waypoints = set()

        while q:
            r, c = q.popleft()
            visited_order.append((r, c))
            if waypoint_set and (r, c) in waypoint_set:
                found_waypoints.add((r, c))
                if len(found_waypoints) == len(waypoint_set):
                    break
            for nr, nc in self.neighbors4(r, c):
                if self.maze[nr][nc] == 0 and dist[nr][nc] == -1:
                    dist[nr][nc] = dist[r][c] + 1
                    parent[(nr, nc)] = (r, c)
                    q.append((nr, nc))

        return visited_order, dist, parent

    def bfs_scan_from_targets(self, targets: List[Tuple[int, int]]):
        dist = [[-1] * COLS for _ in range(ROWS)]
        parent: dict[Tuple[int, int], Tuple[int, int] | None] = {}
        q = deque()

        for tr, tc in targets:
            dist[tr][tc] = 0
            parent[(tr, tc)] = None
            q.append((tr, tc))

        while q:
            r, c = q.popleft()
            for nr, nc in self.neighbors4(r, c):
                if self.maze[nr][nc] == 0 and dist[nr][nc] == -1:
                    dist[nr][nc] = dist[r][c] + 1
                    parent[(nr, nc)] = (r, c)
                    q.append((nr, nc))

        return dist, parent

    def reconstruct_path_from_parent(self, parent: dict, start: Tuple[int, int], target: Tuple[int, int]):
        if target not in parent:
            return []

        path = []
        current = target
        while current is not None:
            path.append(current)
            current = parent.get(current)
        path.reverse()

        if not path or path[0] != start:
            return []
        return path

    def reconstruct_path_to_target(self, parent_to_target: dict, source: Tuple[int, int]):
        if source not in parent_to_target:
            return []

        path = []
        current = source
        while current is not None:
            path.append(current)
            current = parent_to_target.get(current)
        return path

    def solve_route_through_waypoints(self, algorithm: str, waypoints: List[Tuple[int, int]],
                                      targets: List[Tuple[int, int]]):
        if not waypoints or not targets:
            return None

        start_time = time.time()
        scan_visited, dist_start, parent_start = self.bfs_scan_from_source(tuple(self.start), waypoints)
        dist_to_target, parent_to_target = self.bfs_scan_from_targets(targets)

        candidates = []
        for waypoint in waypoints:
            wr, wc = waypoint
            if dist_start[wr][wc] == -1 or dist_to_target[wr][wc] == -1:
                continue

            path_1 = self.reconstruct_path_from_parent(parent_start, tuple(self.start), waypoint)
            path_2 = self.reconstruct_path_to_target(parent_to_target, waypoint)
            if not path_1 or not path_2:
                continue

            full_path = path_1 + path_2[1:]
            candidates.append({
                "waypoint": waypoint,
                "order": (waypoint,),
                "visited_order": scan_visited,
                "full_path": full_path,
                "target": path_2[-1],
                "total_steps": max(len(full_path) - 1, 0),
                "total_time": 0.0,
            })

        if not candidates:
            return None

        candidates.sort(key=lambda item: item["total_steps"])
        best = candidates[0]
        elapsed_total = (time.time() - start_time) * 1000
        best["total_time"] = elapsed_total

        second_best_steps = candidates[1]["total_steps"] if len(candidates) > 1 else None
        best["second_best_steps"] = second_best_steps
        best["saved_steps"] = (second_best_steps - best["total_steps"]) if second_best_steps is not None else None
        best["evaluated_count"] = len(candidates)
        best["total_waypoints"] = len(waypoints)
        best["scan_visited"] = scan_visited
        return best

    def solve_route_all_waypoints(self, algorithm: str, waypoints: List[Tuple[int, int]],
                                  targets: List[Tuple[int, int]]):
        if not waypoints or not targets:
            return None

        start_time = time.time()
        start_pos = tuple(self.start)
        dist_maps = {start_pos: self.bfs_distances(self.maze, start_pos)}
        for wp in waypoints:
            dist_maps[wp] = self.bfs_distances(self.maze, wp)

        best = None
        for order in itertools.permutations(waypoints):
            total_steps = 0
            current = start_pos
            valid = True
            for wp in order:
                dist = dist_maps[current][wp[0]][wp[1]]
                if dist < 0:
                    valid = False
                    break
                total_steps += dist
                current = wp

            if not valid:
                continue

            best_target = None
            best_target_dist = None
            dist_map = dist_maps[current]
            for tr, tc in targets:
                d = dist_map[tr][tc]
                if d < 0:
                    continue
                if best_target_dist is None or d < best_target_dist:
                    best_target_dist = d
                    best_target = (tr, tc)

            if best_target is None:
                continue

            total_steps += best_target_dist
            if best is None or total_steps < best["total_steps"]:
                best = {
                    "order": order,
                    "target": best_target,
                    "total_steps": total_steps,
                }

        if best is None:
            return None

        visited_order: List[Tuple[int, int]] = []
        full_path: List[Tuple[int, int]] = []
        current = start_pos
        solve_segment = self.solve_bfs if algorithm == "BFS" else self.solve_astar

        for wp in best["order"]:
            visited, path, _ = solve_segment(self.maze, current, [wp])
            if not path:
                return None
            visited_order.extend(visited)
            full_path = path if not full_path else full_path + path[1:]
            current = wp

        visited, path, exit_pos = solve_segment(self.maze, current, [best["target"]])
        if not path or exit_pos is None:
            return None
        visited_order.extend(visited)
        full_path = full_path + path[1:] if full_path else path

        elapsed_ms = (time.time() - start_time) * 1000
        return {
            "order": best["order"],
            "target": exit_pos,
            "visited_order": list(dict.fromkeys(visited_order)),
            "full_path": full_path,
            "total_steps": max(len(full_path) - 1, 0),
            "total_time": elapsed_ms,
        }

    def animate_waypoint_scan(self, scan_visited: List[Tuple[int, int]], algorithm: str):
        if not scan_visited:
            return

        total_waypoints = len(self.waypoints)
        seen_waypoints = set()
        waypoint_set = set(self.waypoints)
        visit_delay = max(1, VISITED_CELL_DELAY_MS // 3)
        if algorithm == "ASTAR":
            astar_visited_set = set()
            for idx, cell in enumerate(scan_visited):
                astar_visited_set.add(cell)
                if cell in waypoint_set:
                    seen_waypoints.add(cell)
                self.status_label.config(
                    text=f"{algorithm}: duyệt 1 lần qua bản đồ, đã đi qua {len(seen_waypoints)}/{total_waypoints} waypoint..."
                )
                if self.should_render_frame(idx, len(scan_visited)):
                    self.draw_maze(astar_visited=astar_visited_set)
                    self.ui_pump(visit_delay)
        else:
            visited_set = set()
            for idx, cell in enumerate(scan_visited):
                visited_set.add(cell)
                if cell in waypoint_set:
                    seen_waypoints.add(cell)
                self.status_label.config(
                    text=f"{algorithm}: duyệt 1 lần qua bản đồ, đã đi qua {len(seen_waypoints)}/{total_waypoints} waypoint..."
                )
                if self.should_render_frame(idx, len(scan_visited)):
                    self.draw_maze(visited=visited_set)
                    self.ui_pump(visit_delay)

    def solve_maze(self):
        if self.is_animating:
            return

        if self.waypoint_all_mode:
            if not self.waypoints:
                self.status_label.config(text="Không có điểm mốc được sinh.")
                return

            targets = self.exits
            if not targets:
                self.status_label.config(text="Không có mục tiêu hợp lệ.")
                return

            self.draw_maze()
            self.status_label.config(text=f"Đang giải mê cung qua tất cả điểm mốc bằng {self.algorithm}...")
            self.is_animating = True
            self.ui_pump()

            result = self.solve_route_all_waypoints(self.algorithm, self.waypoints, targets)
            if not result:
                self.status_label.config(text="Không tìm thấy đường đi qua tất cả điểm mốc.")
                self.draw_maze()
                self.append_run_history(
                    mode="WAYPOINT_ALL",
                    start_pos=tuple(self.start),
                    success=False,
                    steps=0,
                    visited=0,
                    elapsed_ms=0,
                    target=None,
                    waypoint=None,
                    detail="Không có đường hợp lệ qua tất cả điểm mốc.",
                )
                self.is_animating = False
                return

            visited_order = result["visited_order"]
            full_path = result["full_path"]
            exit_pos = result["target"]
            total_time = result["total_time"]
            step_count = result["total_steps"]
            order = result["order"]

            visited_set = set()
            for idx, (r, c) in enumerate(visited_order):
                visited_set.add((r, c))
                if self.should_render_frame(idx, len(visited_order)):
                    self.draw_maze(visited=visited_set, goal=exit_pos)
                    self.ui_pump(VISITED_CELL_DELAY_MS)

            path_set = set()
            for idx, (r, c) in enumerate(full_path):
                path_set.add((r, c))
                if self.should_render_frame(idx, len(full_path)):
                    self.draw_maze(visited=visited_set, path=path_set, goal=exit_pos, santa=(r, c))
                    self.ui_pump(PATH_CELL_DELAY_MS)

            if full_path:
                sr, sc = full_path[-1]
                self.draw_maze(visited=visited_set, path=path_set, goal=exit_pos, santa=(sr, sc))

            self.is_animating = False
            order_text = " -> ".join([f"{wp}" for wp in order])
            self.status_label.config(text=f"Đã đi qua tất cả điểm mốc. Thứ tự: {order_text}")
            self.stats_label.config(
                text=f"Bước đi: {step_count}, Đã duyệt: {len(visited_order)}, Thời gian: {total_time:.2f} ms, Đích: {exit_pos}"
            )
            self.append_run_history(
                mode="WAYPOINT_ALL",
                start_pos=tuple(self.start),
                success=True,
                steps=step_count,
                visited=len(visited_order),
                elapsed_ms=total_time,
                target=exit_pos,
                waypoint=None,
                detail=f"Thu tu: {order_text}",
            )
            return

        if self.waypoint_mode:
            if not self.waypoints:
                self.status_label.config(text="Không có điểm mốc được sinh.")
                return

            self.status_label.config(text=f"Đang giải mê cung qua 1 điểm mốc tối ưu bằng {self.algorithm}...")
            self.is_animating = True
            self.ui_pump()

            best_result = self.solve_route_through_waypoints(self.algorithm, self.waypoints, targets)
            if not best_result:
                self.status_label.config(text="Không tìm thấy đường đi qua bất kỳ điểm mốc nào.")
                self.draw_maze()
                self.append_run_history(
                    mode="WAYPOINT",
                    start_pos=tuple(self.start),
                    success=False,
                    steps=0,
                    visited=0,
                    elapsed_ms=0,
                    target=None,
                    waypoint=None,
                    detail="Không có waypoint nào nối được start tới đích.",
                )
                self.is_animating = False
                return

            self.animate_waypoint_scan(best_result.get("scan_visited", []), self.algorithm)

            waypoint = best_result["waypoint"]
            scan_visited = best_result.get("scan_visited", [])
            full_path = best_result["full_path"]
            exit_pos = best_result["target"]
            total_time = best_result["total_time"]
            step_count = best_result["total_steps"]
            saved_steps = best_result.get("saved_steps")
            evaluated_count = best_result.get("evaluated_count", 0)
            total_waypoints = best_result.get("total_waypoints", len(self.waypoints))
            if saved_steps is None:
                detail_text = (
                    f"Đã duyệt {evaluated_count}/{total_waypoints} waypoint hợp lệ | "
                    f"Waypoint chọn: {waypoint} | Tổng bước ngắn nhất: {step_count} | "
                    f"Không có waypoint khác để so sánh"
                )
            else:
                detail_text = (
                    f"Đã duyệt {evaluated_count}/{total_waypoints} waypoint hợp lệ | "
                    f"Waypoint chọn: {waypoint} | Tổng bước ngắn nhất: {step_count} | "
                    f"Ngắn hơn waypoint tốt thứ 2: {saved_steps} bước"
                )

            # Giữ nguyên màu từ lượt quét waypoint, sau đó vẽ luôn đường đi tối ưu.
            visited_set = set(scan_visited)

            path_set = set()
            for idx, (r, c) in enumerate(full_path):
                path_set.add((r, c))
                if self.should_render_frame(idx, len(full_path)):
                    self.draw_maze(visited=visited_set, path=path_set, goal=exit_pos, santa=(r, c))
                    self.ui_pump(PATH_CELL_DELAY_MS)

            if full_path:
                sr, sc = full_path[-1]
                self.draw_maze(visited=visited_set, path=path_set, goal=exit_pos, santa=(sr, sc))

            self.is_animating = False
            self.status_label.config(text=f"Đã đi qua điểm mốc tối ưu {waypoint}. {detail_text}")
            self.stats_label.config(text=f"Bước đi: {step_count}, Đã duyệt: {len(scan_visited)}, Thời gian: {total_time:.2f} ms, Đích: {exit_pos}")
            self.append_run_history(
                mode="WAYPOINT",
                start_pos=tuple(self.start),
                success=True,
                steps=step_count,
                visited=len(scan_visited),
                elapsed_ms=total_time,
                target=exit_pos,
                waypoint=waypoint,
                detail=detail_text,
            )
            return

        targets = self.exits + self.enemies
        if not targets:
            self.status_label.config(text="Không có mục tiêu hợp lệ.")
            return

        self.status_label.config(text=f"Đang giải mê cung bằng {self.algorithm}...")
        self.is_animating = True
        self.ui_pump()

        start_time = time.time()
        if self.algorithm == "BFS":
            visited_order, path, exit_pos = self.solve_bfs(self.maze, tuple(self.start), targets)
        else:
            visited_order, path, exit_pos = self.solve_astar(self.maze, tuple(self.start), targets)
        elapsed = (time.time() - start_time) * 1000

        if not path or not exit_pos:
            self.status_label.config(text="Không tìm thấy đường đi.")
            self.stats_label.config(text=f"Bước đi: -, Đã duyệt: {len(visited_order)}, Thời gian: {elapsed:.2f} ms, Lối ra: -")
            self.draw_maze()
            self.append_run_history(
                mode="NORMAL",
                start_pos=tuple(self.start),
                success=False,
                steps=0,
                visited=len(visited_order),
                elapsed_ms=elapsed,
            )
            self.is_animating = False
            return

        visited_set = set()
        for idx, (r, c) in enumerate(visited_order):
            visited_set.add((r, c))
            if self.should_render_frame(idx, len(visited_order)):
                self.draw_maze(visited=visited_set, goal=exit_pos)
                self.ui_pump(VISITED_CELL_DELAY_MS)

        path_set = set()
        for idx, (r, c) in enumerate(path):
            path_set.add((r, c))
            if self.should_render_frame(idx, len(path)):
                self.draw_maze(visited=visited_set, path=path_set, goal=exit_pos, santa=(r, c))
                self.ui_pump(PATH_CELL_DELAY_MS)

        if path:
            sr, sc = path[-1]
            self.draw_maze(visited=visited_set, path=path_set, goal=exit_pos, santa=(sr, sc))

        self.is_animating = False
        step_count = max(len(path) - 1, 0)
        is_exit = exit_pos in self.exits
        goal_type = "Lối ra" if is_exit else "Địch"
        self.status_label.config(text=f"Hoàn thành bằng {self.algorithm}.")
        self.stats_label.config(text=f"Bước đi: {step_count}, Đã duyệt: {len(visited_order)}, Thời gian: {elapsed:.2f} ms, {goal_type}: {exit_pos}")
        self.append_run_history(
            mode="NORMAL",
            start_pos=tuple(self.start),
            success=True,
            steps=step_count,
            visited=len(visited_order),
            elapsed_ms=elapsed,
            target=exit_pos,
        )

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    solver = MazeSolver()
    solver.run()
