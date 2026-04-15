import tkinter as tk
from tkinter import Canvas
import random
from collections import deque
from typing import List, Tuple, Set
import time

# Constants
ROWS = 51
COLS = 81
CELL_SIZE = 14
EXIT_COUNT = 6
START_POSITION = (25, 40)  # Center of maze
MAX_GENERATION_ATTEMPTS = 20
VISITED_CELL_DELAY_MS = 5
PATH_CELL_DELAY_MS = 15

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
COLOR_BUTTON = "#333333"
COLOR_TEXT = "#FFFFFF"

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
        
        # Canvas frame - responsive
        canvas_frame = tk.Frame(self.root, bg="black")
        canvas_frame.grid(row=0, column=0, sticky="nsew")
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)
        canvas_frame.grid_propagate(True)  # Allow frame to expand
        
        # Canvas
        self.canvas = Canvas(canvas_frame, bg="black", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", self.on_canvas_configure)
        
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
        
        self.solve_btn = tk.Button(button_frame, text="Giải mê cung", command=self.solve_maze,
                                  bg=COLOR_BUTTON, fg=COLOR_TEXT)
        self.solve_btn.pack(side=tk.LEFT, padx=5)
        
        self.algo_label = tk.Label(button_frame, text="Thuật toán: BFS", bg="#222222", fg=COLOR_TEXT)
        self.algo_label.pack(side=tk.LEFT, padx=5)
        
        self.algo_btn = tk.Button(button_frame, text="Đổi (A*)", command=self.toggle_algorithm,
                                 bg=COLOR_BUTTON, fg=COLOR_TEXT)
        self.algo_btn.pack(side=tk.LEFT, padx=5)
        
        self.compare_btn = tk.Button(button_frame, text="So sánh BFS vs A*", command=self.compare_algorithms,
                                     bg="#16a34a", fg=COLOR_TEXT)
        self.compare_btn.pack(side=tk.LEFT, padx=5)
        
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
        self.is_animating = False
        self.algorithm = "BFS"  # BFS or ASTAR
        self.comparison_results = None
        
        self.generate_new_maze()
        self.draw_maze()
        
        # Force window update and trigger on_canvas_configure
        self.root.update()
        self.root.update_idletasks()
    
    def on_canvas_configure(self, event):
        """Handle canvas resize - scale maze to fit"""
        # Recalculate cell size based on actual event dimensions
        if event.width > 100 and event.height > 100:
            cell_width = event.width / COLS
            cell_height = event.height / ROWS
            self.current_cell_size = min(cell_width, cell_height)
            
            # Redraw maze với kích thước mới
            if hasattr(self, 'maze') and len(self.maze) > 0:
                self.draw_maze()

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

    def generate_new_maze(self):
        for attempt in range(MAX_GENERATION_ATTEMPTS):
            grid = self.generate_maze_base()
            self.carve_loops(grid)
            self.braid_maze(grid)
            
            source = tuple(START_POSITION)
            exits = self.place_distinct_exits(grid, source, EXIT_COUNT)
            enemies = self.place_enemies(grid, source, exits)
            
            if len(exits) >= 2:
                self.maze = grid
                self.start = list(source)
                self.exits = exits
                self.enemies = enemies
                self.status_label.config(text="Đã tạo mê cung mới.")
                self.stats_label.config(text="Bước đi: -, Đã duyệt: -, Thời gian: -, Lối ra: -")
                self.draw_maze()
                return

        grid = self.generate_maze_base()
        self.carve_loops(grid)
        self.braid_maze(grid)
        source = tuple(START_POSITION)
        exits = self.place_distinct_exits(grid, source, 2)
        enemies = self.place_enemies(grid, source, exits)
        
        self.maze = grid
        self.start = list(source)
        self.exits = exits
        self.enemies = enemies
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
                  astar_visited: Set[Tuple[int, int]] = None):
        if visited is None:
            visited = set()
        if path is None:
            path = set()
        if astar_visited is None:
            astar_visited = set()

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

        # Draw start
        sr, sc = self.start
        x, y = sc * self.current_cell_size, sr * self.current_cell_size
        self.canvas.create_rectangle(x, y, x + self.current_cell_size, y + self.current_cell_size, fill=COLOR_START, outline="")

        # Draw goal
        if goal:
            gr, gc = goal
            x, y = gc * self.current_cell_size, gr * self.current_cell_size
            self.canvas.create_rectangle(x, y, x + self.current_cell_size, y + self.current_cell_size, fill=COLOR_GOAL, outline="")

        self.root.update_idletasks()

    def toggle_algorithm(self):
        self.algorithm = "ASTAR" if self.algorithm == "BFS" else "BFS"
        self.algo_label.config(text=f"Thuật toán: {self.algorithm}")

    def solve_maze(self):
        if self.is_animating:
            return

        targets = self.exits + self.enemies
        if not targets:
            self.status_label.config(text="Không có mục tiêu hợp lệ.")
            return
        
        self.draw_maze()
        self.status_label.config(text=f"Đang giải mê cung bằng {self.algorithm}...")
        self.is_animating = True
        self.root.update()
        
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
            self.is_animating = False
            return

        # Animate visited cells
        visited_set = set()
        for r, c in visited_order:
            visited_set.add((r, c))
            self.draw_maze(visited=visited_set, goal=exit_pos)
            self.root.after(VISITED_CELL_DELAY_MS)
            self.root.update()

        # Animate path
        path_set = set()
        for r, c in path:
            path_set.add((r, c))
            self.draw_maze(visited=visited_set, path=path_set, goal=exit_pos)
            self.root.after(PATH_CELL_DELAY_MS)
            self.root.update()

        self.is_animating = False

        step_count = max(len(path) - 1, 0)
        is_exit = exit_pos in self.exits
        goal_type = "Lối ra" if is_exit else "Địch"
        self.status_label.config(text=f"Hoàn thành bằng {self.algorithm}.")
        self.stats_label.config(text=f"Bước đi: {step_count}, Đã duyệt: {len(visited_order)}, Thời gian: {elapsed:.2f} ms, {goal_type}: {exit_pos}")

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
        self.root.update()
        
        # Test BFS
        start_time = time.time()
        bfs_visited, bfs_path, bfs_exit = self.solve_bfs(self.maze, tuple(self.start), targets)
        bfs_time = (time.time() - start_time) * 1000
        bfs_steps = max(len(bfs_path) - 1, 0) if bfs_path else 0
        
        # Test A*
        start_time = time.time()
        astar_visited, astar_path, astar_exit = self.solve_astar(self.maze, tuple(self.start), targets)
        astar_time = (time.time() - start_time) * 1000
        astar_steps = max(len(astar_path) - 1, 0) if astar_path else 0
        
        # Tính toán hiệu suất
        if len(bfs_visited) > 0:
            astar_efficiency = (len(bfs_visited) - len(astar_visited)) / len(bfs_visited) * 100
        else:
            astar_efficiency = 0
        
        # Lưu kết quả
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
        
        # Hiển thị so sánh TRƯỚC animation
        self.display_comparison()
        self.status_label.config(text="Dang so sanh... Xem ket qua phia duoi")
        self.root.update()
        
        # Animate BFS solution
        bfs_visited_set = set()
        for r, c in bfs_visited:
            bfs_visited_set.add((r, c))
            self.draw_maze(visited=bfs_visited_set, goal=bfs_exit)
            self.root.after(1)
            self.root.update_idletasks()
        
        # Pause giữa hai animation
        self.root.after(200)
        self.root.update_idletasks()
        
        # Animate A* solution
        astar_visited_set = set()
        for r, c in astar_visited:
            astar_visited_set.add((r, c))
            self.draw_maze(visited=bfs_visited_set, astar_visited=astar_visited_set, goal=astar_exit)
            self.root.after(1)
            self.root.update_idletasks()
        
        # Animate A* path
        astar_path_set = set()
        for r, c in astar_path:
            astar_path_set.add((r, c))
            self.draw_maze(visited=bfs_visited_set, astar_visited=astar_visited_set, path=astar_path_set, goal=astar_exit)
            self.root.after(5)
            self.root.update_idletasks()
        
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

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    solver = MazeSolver()
    solver.run()
