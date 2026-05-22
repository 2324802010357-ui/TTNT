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

# Hằng số
ROWS = 51
COLS = 81
CELL_SIZE = 14
EXIT_COUNT = 6
WAYPOINT_COUNT = 4  # Tạo 4 điểm mốc
START_POSITION = (25, 40)  # Trung tâm mê cung
MAX_GENERATION_ATTEMPTS = 20
VISITED_CELL_DELAY_MS = 5
PATH_CELL_DELAY_MS = 15
ANIMATION_FRAME_SKIP = 6

# Độ phức tạp - Mê cung nhiều tường
ROOM_COUNT = 0
LOOP_CARVE_RATE = 0.15
MIN_START_BRANCHES = 3
BRAID_RATE = 0.30  # Tăng để tạo nhiều ngõ cụt

# Màu sắc
COLOR_WALL = "#0F172A"
COLOR_PATH = "#F8FAFC"
COLOR_VISITED = "#22D3EE"  # Màu ô đã duyệt (mặc định)
COLOR_VISITED_BFS = "#22D3EE"  # Ô đã duyệt GBFS - Xanh lơ
COLOR_VISITED_ASTAR = "#84CC16"  # Ô đã duyệt A* - Xanh lá mạ
COLOR_SOLUTION = "#F97316"
COLOR_START = "#2563EB"
COLOR_EXIT = "#22C55E"
COLOR_GOAL = "#EF4444"
COLOR_WAYPOINT = "#EC4899"  # Hot pink cho điểm mốc
COLOR_BUTTON = "#333333"
COLOR_TEXT = "#FFFFFF"

SANTA_SCALE = 10.0
CHIMNEY_SCALE = 3.0

class MazeSolver:
    def __init__(self):
        # Khoi tao giao dien, trang thai, va sinh me cung ban dau.
        self.root = tk.Tk()
        self.root.title("Trình giải mê cung AI")
        self.root.geometry("1200x900")  # Đặt kích thước cửa sổ ban đầu
        
        self.width = COLS * CELL_SIZE
        self.height = ROWS * CELL_SIZE
        
        # Khung chính với bố cục lưới
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Khu vực trên: vùng vẽ mê cung (trái) + lịch sử chạy (phải)
        top_frame = tk.Frame(self.root, bg="black")
        top_frame.grid(row=0, column=0, sticky="nsew")
        top_frame.grid_rowconfigure(0, weight=1)
        top_frame.grid_columnconfigure(0, weight=4)
        top_frame.grid_columnconfigure(1, weight=1)

        # Khung vùng vẽ co giãn theo kích thước
        canvas_frame = tk.Frame(top_frame, bg="black")
        canvas_frame.grid(row=0, column=0, sticky="nsew")
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)
        canvas_frame.grid_propagate(True)  # Cho phép khung tự giãn
        
        # Vùng vẽ
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

        self.chimney_image_path = os.path.join(
            os.path.dirname(__file__), "..", "Picture",
            "pngtree-red-chimney-cartoon-chimney-snow-falling-chimney-hand-drawn-chimney-png-image_3865345.jpg",
        )
        self.chimney_base_image = None
        self.chimney_tk_image = None
        self.chimney_last_size = None
        self.chimney_load_error = None

        # Bảng lịch sử chạy bên phải
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
        
        # Tính kích thước ô dựa trên kích thước cửa sổ
        # Vùng vẽ có chiều rộng = chiều rộng root, chiều cao = chiều cao root - nút - trạng thái - so sánh
        # Tạm thời dùng giá trị ước lượng, sẽ cập nhật trong draw_maze()
        self.current_cell_size = CELL_SIZE  # Kích thước ô mặc định, sẽ cập nhật trong draw_maze()
        
        self.original_width = self.width
        self.original_height = self.height
        
        # Khung nút bấm
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
        
        self.algo_label = tk.Label(button_frame, text="Thuật toán: GBFS", bg="#222222", fg=COLOR_TEXT)
        self.algo_label.pack(side=tk.LEFT, padx=5)

        self.algo_btn = tk.Button(button_frame, text="Chọn thuật toán", command=self.show_algorithm_menu,
                                 bg=COLOR_BUTTON, fg=COLOR_TEXT)
        self.algo_btn.pack(side=tk.LEFT, padx=5)
        
        self.compare_btn = tk.Button(button_frame, text="So sánh GBFS vs A*", command=self.compare_algorithms,
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
        
        # Khung trạng thái
        status_frame = tk.Frame(self.root, bg="#1a1a1a")
        status_frame.grid(row=2, column=0, sticky="ew")
        
        self.status_label = tk.Label(status_frame, text="Sẵn sàng.", bg="#1a1a1a", fg=COLOR_TEXT, wraplength=800)
        self.status_label.pack(fill=tk.X, padx=5, pady=2)
        
        self.stats_label = tk.Label(status_frame, text="Bước đi: -, Đã duyệt: -, Thời gian: -, Lối ra: -",
                                   bg="#1a1a1a", fg=COLOR_TEXT, wraplength=800)
        self.stats_label.pack(fill=tk.X, padx=5, pady=2)
        
        # Khung so sánh
        comparison_frame = tk.Frame(self.root, bg="#1a1a1a", height=60)
        comparison_frame.grid(row=3, column=0, sticky="ew", padx=5, pady=5)
        comparison_frame.grid_propagate(False)  # Không tự co
        
        self.comparison_label = tk.Label(comparison_frame, text="Kết quả so sánh sẽ hiển thị ở đây...", font=("Arial", 10),
                                        bg="#1a1a1a", fg="#FFD700", justify=tk.LEFT)
        self.comparison_label.pack(fill=tk.BOTH, padx=5, pady=5, expand=True)
        
        # Trang thai me cung va che do hien tai
        self.maze = []
        self.start = list(START_POSITION)
        self.exits = []
        self.waypoints = []  # Điểm mốc phân tán trong mê cung
        self.waypoint_mode = False  # Bật/tắt chế độ điểm mốc
        self.waypoint_all_mode = False
        self.is_animating = False
        self.algorithm = "GBFS"  # GBFS hoặc ASTAR
        self.comparison_results = None
        self.run_counter = 0
        self.last_visited: Set[Tuple[int, int]] = set()
        self.last_path: Set[Tuple[int, int]] = set()
        self.last_astar_visited: Set[Tuple[int, int]] = set()
        self.last_goal: Tuple[int, int] | None = None

        # Tai tai nguyen hinh anh
        self.load_santa_image()
        self.load_chimney_image()
        
        # Tao me cung moi va ve lan dau
        self.generate_new_maze()
        self.draw_maze()
        
        # Ép cập nhật cửa sổ và kích hoạt on_canvas_configure
        self.root.update()
        self.root.update_idletasks()
    
    def on_canvas_configure(self, event):
        # Xu ly thay doi kich thuoc canvas - co gian me cung vua khung
        if self.is_animating:
            # Dang animate thi khong ve lai de tranh giat
            return

        # Tính lại kích thước ô dựa trên kích thước thật
        if event.width > 100 and event.height > 100:
            # Tinh kich thuoc o theo chieu rong/cao moi
            cell_width = event.width / COLS
            cell_height = event.height / ROWS
            self.current_cell_size = min(cell_width, cell_height)
            
            # Ve lai me cung voi kich thuoc moi
            if hasattr(self, 'maze') and len(self.maze) > 0:
                # Cap nhat anh theo ti le moi truoc khi ve
                self.update_santa_image()
                self.update_chimney_image()
                self.draw_maze(
                    visited=self.last_visited,
                    path=self.last_path,
                    goal=self.last_goal,
                    astar_visited=self.last_astar_visited,
                    santa=self.last_santa,
                )

    def load_santa_image(self):
        # Tai anh ong gia Noel va xu ly truong hop loi.
        # Kiem tra duong dan co ton tai hay khong
        if not os.path.exists(self.santa_image_path):
            # Khong tim thay tep anh
            self.santa_base_image = None
            self.santa_load_error = f"Khong tim thay anh: {self.santa_image_path}"
            return

        if PIL_AVAILABLE:
            # Doc anh bang Pillow neu co
            try:
                # Chuyen ve RGBA de ve trong suot
                self.santa_base_image = Image.open(self.santa_image_path).convert("RGBA")
                self.santa_load_error = None
            except Exception as exc:
                self.santa_base_image = None
                self.santa_load_error = f"Loi Pillow: {exc}"
        else:
            # Dung PhotoImage neu khong co Pillow
            try:
                # PhotoImage chi ho tro mot so dinh dang co ban
                self.santa_base_image = tk.PhotoImage(file=self.santa_image_path)
                self.santa_load_error = None
            except Exception as exc:
                self.santa_base_image = None
                self.santa_load_error = f"Loi PhotoImage: {exc}"

    def load_chimney_image(self):
        # Tai anh ong khoi va xu ly truong hop loi.
        # Kiem tra duong dan co ton tai hay khong
        if not os.path.exists(self.chimney_image_path):
            # Khong tim thay tep anh
            self.chimney_base_image = None
            self.chimney_load_error = f"Khong tim thay anh: {self.chimney_image_path}"
            return

        if PIL_AVAILABLE:
            # Doc anh bang Pillow neu co
            try:
                # Chuyen ve RGBA de ve trong suot
                self.chimney_base_image = Image.open(self.chimney_image_path).convert("RGBA")
                self.chimney_load_error = None
            except Exception as exc:
                self.chimney_base_image = None
                self.chimney_load_error = f"Loi Pillow: {exc}"
        else:
            # Dung PhotoImage neu khong co Pillow
            try:
                # PhotoImage chi ho tro mot so dinh dang co ban
                self.chimney_base_image = tk.PhotoImage(file=self.chimney_image_path)
                self.chimney_load_error = None
            except Exception as exc:
                self.chimney_base_image = None
                self.chimney_load_error = f"Loi PhotoImage: {exc}"

    def update_santa_image(self):
        # Cap nhat kich thuoc anh Noel theo ti le o hien tai.
        if not self.santa_base_image:
            # Khong co anh nen bo qua
            return
        # Tinh kich thuoc anh theo tile va he so scale
        target_size = max(1, int(round(self.current_cell_size * SANTA_SCALE)))
        if self.santa_last_size == target_size and self.santa_tk_image is not None:
            # Khong doi kich thuoc thi khong can resize
            return

        if PIL_AVAILABLE and isinstance(self.santa_base_image, Image.Image):
            # Resize bang Pillow
            resized = self.santa_base_image.resize((target_size, target_size), Image.LANCZOS)
            self.santa_tk_image = ImageTk.PhotoImage(resized)
        else:
            # Resize bang PhotoImage (subsample/zoom)
            base = self.santa_base_image
            width = base.width()
            height = base.height()
            if width <= 0 or height <= 0:
                return

            # Tinh ti le so voi kich thuoc muc tieu
            scale = min(width / target_size, height / target_size)
            if scale >= 1:
                # Anh lon hon, can giam ti le
                factor = max(1, int(round(scale)))
                self.santa_tk_image = base.subsample(factor, factor)
            else:
                # Anh nho hon, can phong to
                factor = max(1, int(round(1 / scale)))
                self.santa_tk_image = base.zoom(factor, factor)

        self.santa_last_size = target_size

    def update_chimney_image(self):
        # Cap nhat kich thuoc anh ong khoi theo ti le o hien tai.
        if not self.chimney_base_image:
            # Khong co anh nen bo qua
            return
        # Tinh kich thuoc anh theo tile va he so scale
        target_size = max(1, int(round(self.current_cell_size * CHIMNEY_SCALE)))
        if self.chimney_last_size == target_size and self.chimney_tk_image is not None:
            # Khong doi kich thuoc thi khong can resize
            return

        if PIL_AVAILABLE and isinstance(self.chimney_base_image, Image.Image):
            # Resize bang Pillow
            resized = self.chimney_base_image.resize((target_size, target_size), Image.LANCZOS)
            self.chimney_tk_image = ImageTk.PhotoImage(resized)
        else:
            # Resize bang PhotoImage (subsample/zoom)
            base = self.chimney_base_image
            width = base.width()
            height = base.height()
            if width <= 0 or height <= 0:
                return

            # Tinh ti le so voi kich thuoc muc tieu
            scale = min(width / target_size, height / target_size)
            if scale >= 1:
                # Anh lon hon, can giam ti le
                factor = max(1, int(round(scale)))
                self.chimney_tk_image = base.subsample(factor, factor)
            else:
                # Anh nho hon, can phong to
                factor = max(1, int(round(1 / scale)))
                self.chimney_tk_image = base.zoom(factor, factor)

        self.chimney_last_size = target_size

    def draw_santa_at(self, r: int, c: int):
        # Ve Noel tai toa do o (r, c).
        # Tinh toa do ve theo tile va scale
        x, y = c * self.current_cell_size, r * self.current_cell_size
        size = self.current_cell_size * SANTA_SCALE
        offset = (size - self.current_cell_size) / 2
        draw_x = x - offset
        draw_y = y - offset
        if self.santa_tk_image:
            # Ve anh Noel neu da co anh
            self.canvas.create_image(draw_x, draw_y, image=self.santa_tk_image, anchor="nw")
            return

        # Neu khong co anh, ve hinh thay the
        self.canvas.create_rectangle(draw_x, draw_y, draw_x + size, draw_y + size, fill="#ef4444", outline="")
        self.canvas.create_text(
            draw_x + size / 2,
            draw_y + size / 2,
            text="S",
            fill="#ffffff",
            font=("Arial", int(max(8, size / 2)), "bold"),
        )

    def draw_chimney_at(self, r: int, c: int) -> bool:
        # Ve ong khoi tai toa do o, tra ve True neu ve thanh cong.
        # Tinh toa do ve theo tile va scale
        x, y = c * self.current_cell_size, r * self.current_cell_size
        size = self.current_cell_size * CHIMNEY_SCALE
        offset = (size - self.current_cell_size) / 2
        draw_x = x - offset
        draw_y = y - offset
        if self.chimney_tk_image:
            # Ve anh ong khoi neu da co anh
            self.canvas.create_image(draw_x, draw_y, image=self.chimney_tk_image, anchor="nw")
            return True
        return False

    def ui_pump(self, delay_ms: int = 0):
        # Cap nhat giao dien va tao tre nhe cho animation.
        if delay_ms > 0:
            # Tao do tre ngat nho
            self.root.after(delay_ms)
        # Cap nhat giao dien ngay
        self.root.update_idletasks()
        self.root.update()

    def should_render_frame(self, index: int, total: int) -> bool:
        # Quyet dinh co ve khung hinh nay hay bo qua.
        if total <= 0:
            # Khong co gi de ve
            return False
        return (index % ANIMATION_FRAME_SKIP == 0) or (index == total - 1)

    def append_run_history(self, mode: str, start_pos: Tuple[int, int], success: bool,
                           steps: int, visited: int, elapsed_ms: float,
                           target: Tuple[int, int] | None = None,
                           waypoint: Tuple[int, int] | None = None,
                           detail: str | None = None):
        # Ghi lai ket qua mot lan chay vao lich su.
        self.run_counter += 1
        # Tao dong thong tin hien thi
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
                               gbfs_steps: int, gbfs_visited: int, gbfs_time: float,
                               astar_steps: int, astar_visited: int, astar_time: float,
                               efficiency: float,
                               waypoint: Tuple[int, int] | None = None,
                               detail: str | None = None):
        # Ghi lai ket qua so sanh GBFS va A*.
        self.run_counter += 1
        # Tao dong thong tin so sanh
        waypoint_text = f", WP={waypoint}" if waypoint else ""
        detail_text = f" | {detail}" if detail else ""
        line = (
            f"#{self.run_counter} [COMPARE] Algo=GBFS_vs_A* | Start={start_pos}{waypoint_text}"
            f" | GBFS: buoc={gbfs_steps}, duyet={gbfs_visited}, {gbfs_time:.2f}ms"
            f" | A*: buoc={astar_steps}, duyet={astar_visited}, {astar_time:.2f}ms"
            f" | TIET_KIEM={efficiency:.1f}%{detail_text}\n"
        )

        self.history_text.config(state=tk.NORMAL)
        self.history_text.insert("1.0", line)
        self.history_text.config(state=tk.DISABLED)

    def clear_history(self):
        # Xoa noi dung lich su chay.
        self.run_counter = 0
        # Xoa text va ghi thong bao trang
        self.history_text.config(state=tk.NORMAL)
        self.history_text.delete("1.0", tk.END)
        self.history_text.insert(tk.END, "- Lich su da duoc xoa.\n")
        self.history_text.config(state=tk.DISABLED)

    def in_bounds(self, r: int, c: int) -> bool:
        # Kiem tra toa do co nam trong bien me cung khong.
        return 0 <= r < ROWS and 0 <= c < COLS

    def neighbors4(self, r: int, c: int) -> List[Tuple[int, int]]:
        # Lay cac hang xom 4 huong (len/xuong/trai/phai).
        neighbors = [(r-1, c), (r+1, c), (r, c-1), (r, c+1)]
        # Loc cac hang xom nam trong bien
        return [(nr, nc) for nr, nc in neighbors if self.in_bounds(nr, nc)]

    def create_grid(self, fill_value: int = 1) -> List[List[int]]:
        # Tao luoi me cung voi gia tri khoi tao.
        # Fill_value: 1 la tuong, 0 la duong
        return [[fill_value] * COLS for _ in range(ROWS)]

    def generate_maze_base(self) -> List[List[int]]:
        # Sinh me cung nen bang DFS tren luoi.
        grid = self.create_grid(1)
        stack = [list(START_POSITION)]
        grid[START_POSITION[0]][START_POSITION[1]] = 0

        while stack:
            # Lay o cuoi cung trong stack
            r, c = stack[-1]
            # Ung vien cach 2 o theo 4 huong
            candidates = [
                (r - 2, c),
                (r + 2, c),
                (r, c - 2),
                (r, c + 2),
            ]
            candidates = [(nr, nc) for nr, nc in candidates 
                         if 0 < nr < ROWS - 1 and 0 < nc < COLS - 1 and grid[nr][nc] == 1]

            if not candidates:
                # Khong con duong mo rong thi lui lai
                stack.pop()
                continue

            # Chon ngau nhien 1 huong va duc tuong
            nr, nc = random.choice(candidates)
            wall_r, wall_c = (r + nr) // 2, (c + nc) // 2
            grid[wall_r][wall_c] = 0
            grid[nr][nc] = 0
            stack.append((nr, nc))

        return grid

    def bfs_distances(self, grid: List[List[int]], source: Tuple[int, int]) -> List[List[int]]:
        # Tinh khoang cach BFS tu mot nguon den moi o.
        dist = [[-1] * COLS for _ in range(ROWS)]
        q = deque([source])
        dist[source[0]][source[1]] = 0

        while q:
            # Lay o dau tien trong hang doi
            r, c = q.popleft()
            for nr, nc in self.neighbors4(r, c):
                if grid[nr][nc] == 0 and dist[nr][nc] == -1:
                    # Cap nhat khoang cach va them vao hang doi
                    dist[nr][nc] = dist[r][c] + 1
                    q.append((nr, nc))

        return dist

    def place_distinct_exits(self, grid: List[List[int]], source: Tuple[int, int], 
                            desired: int = EXIT_COUNT) -> List[Tuple[int, int]]:
        # Chon cac loi ra cach nhau mot khoang toi thieu.
        dist = self.bfs_distances(grid, source)
        candidates = []
        
        # Tìm các ô trong mê cung ở nhiều khoảng cách từ điểm bắt đầu
        for r in range(5, ROWS - 5):  # Tránh sát mép
            for c in range(5, COLS - 5):
                if grid[r][c] == 0 and dist[r][c] > 0:  # Phải là đường đi
                    candidates.append(((r, c), dist[r][c]))
        
        # Sắp xếp theo khoảng cách và chọn vị trí đa dạng
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        selected = []
        used_positions = {source}  # Không đặt lối ra tại điểm bắt đầu
        MIN_EXIT_DISTANCE = 15  # Khoảng cách tối thiểu giữa các lối ra
        
        for exit_pos, distance in candidates:
            # Dung khi du so luong loi ra
            if len(selected) >= desired:
                break
            
            # Kiểm tra lối ra này có đủ xa các lối ra đã chọn hay không
            is_far_enough = True
            for selected_exit in selected:
                # Dung Manhattan distance de do do xa
                manhattan_dist = abs(exit_pos[0] - selected_exit[0]) + abs(exit_pos[1] - selected_exit[1])
                if manhattan_dist < MIN_EXIT_DISTANCE:
                    is_far_enough = False
                    break
            
            if is_far_enough and exit_pos not in used_positions:
                # Luu lai loi ra hop le
                selected.append(exit_pos)
                used_positions.add(exit_pos)
        
        # Nếu chưa đủ lối ra, giảm yêu cầu khoảng cách
        if len(selected) < desired:
            # Thu lai voi khoang cach nho hon
            candidates.sort(key=lambda x: x[1], reverse=True)
            MIN_EXIT_DISTANCE = 10  # Giảm yêu cầu
            
            for exit_pos, distance in candidates:
                if len(selected) >= desired:
                    break
                if exit_pos in used_positions:
                    continue
                
                is_far_enough = True
                for selected_exit in selected:
                    # Dung Manhattan distance de do do xa
                    manhattan_dist = abs(exit_pos[0] - selected_exit[0]) + abs(exit_pos[1] - selected_exit[1])
                    if manhattan_dist < MIN_EXIT_DISTANCE:
                        is_far_enough = False
                        break
                
                if is_far_enough:
                    # Them loi ra neu thoa dieu kien
                    selected.append(exit_pos)
                    used_positions.add(exit_pos)
        
        return selected

    def carve_loops(self, grid: List[List[int]]):
        # Tao them vong lap de me cung it bi cua.
        wall_cells = []
        for r in range(1, ROWS - 1):
            for c in range(1, COLS - 1):
                if grid[r][c] != 1:
                    continue
                # Tim cac tuong co the duc tao vong
                ns = [(nr, nc) for nr, nc in self.neighbors4(r, c) if grid[nr][nc] == 0]
                if len(ns) >= 2:
                    vert = [n for n in ns if n[0] != r]
                    horiz = [n for n in ns if n[1] != c]
                    if (len(vert) == 2 and len(horiz) == 0) or (len(horiz) == 2 and len(vert) == 0):
                        wall_cells.append((r, c))

        # Tron danh sach tuong va duc theo ti le
        random.shuffle(wall_cells)
        target = int(len(wall_cells) * LOOP_CARVE_RATE)
        for r, c in wall_cells[:target]:
            grid[r][c] = 0

    def braid_maze(self, grid: List[List[int]]):
        # Giam so ngo cut bang cach mo them loi noi.
        dead_ends = []
        for r in range(1, ROWS - 1):
            for c in range(1, COLS - 1):
                if grid[r][c] != 0:
                    continue
                # Dem so hang xom duong di
                ns = [(nr, nc) for nr, nc in self.neighbors4(r, c) if grid[nr][nc] == 0]
                if len(ns) == 1:
                    dead_ends.append((r, c))

        # Tron va mo them loi noi ngau nhien
        random.shuffle(dead_ends)
        target = int(len(dead_ends) * BRAID_RATE)
        for r, c in dead_ends[:target]:
            wall_neighbors = []
            for nr, nc in [(r-1, c), (r+1, c), (r, c-1), (r, c+1)]:
                if not self.in_bounds(nr, nc) or grid[nr][nc] != 1:
                    continue
                # Tim tuong co tiep giap voi duong
                wall_neighbors2 = [(nnr, nnc) for nnr, nnc in self.neighbors4(nr, nc) if grid[nnr][nnc] == 0]
                if wall_neighbors2:
                    wall_neighbors.append((nr, nc))
            
            if wall_neighbors:
                # Mo 1 tuong de noi thong
                wr, wc = random.choice(wall_neighbors)
                grid[wr][wc] = 0

    def pick_random_start(self, grid: List[List[int]], blocked: Set[Tuple[int, int]] | None = None) -> Tuple[int, int] | None:
        # Chon mot diem bat dau ngau nhien khong bi chan.
        if blocked is None:
            blocked = set()

        # Thu thap cac o duong hop le
        candidates = []
        for r in range(1, ROWS - 1):
            for c in range(1, COLS - 1):
                if grid[r][c] == 0 and (r, c) not in blocked:
                    candidates.append((r, c))

        if not candidates:
            return None

        return random.choice(candidates)

    def randomize_start_position(self):
        # Ngau nhien lai diem bat dau trong me cung.
        if self.is_animating:
            return
        if not self.maze:
            self.status_label.config(text="Chưa có mê cung để random điểm bắt đầu.")
            return

        # Khong chon trung exit hay waypoint
        blocked = set(self.exits) | set(self.waypoints)
        new_start = self.pick_random_start(self.maze, blocked)
        if new_start is None:
            self.status_label.config(text="Không tìm được vị trí bắt đầu hợp lệ.")
            return

        # Cap nhat trang thai va ve lai
        self.start = [new_start[0], new_start[1]]
        self.status_label.config(text=f"Đã random điểm bắt đầu: {new_start}")
        self.stats_label.config(text="Bước đi: -, Đã duyệt: -, Thời gian: -, Lối ra: -")
        self.draw_maze()

    def randomize_waypoint(self):
        # Ngau nhien lai cac diem moc.
        if self.is_animating:
            return
        if not self.maze:
            self.status_label.config(text="Chưa có mê cung để random điểm mốc.")
            return

        # Sinh lai danh sach waypoint
        new_waypoints = self.generate_waypoints(self.maze, tuple(self.start), self.exits)
        if not new_waypoints:
            self.status_label.config(text="Không tìm được vị trí điểm mốc hợp lệ.")
            return

        # Cap nhat va ve lai neu can
        self.waypoints = new_waypoints
        if self.waypoint_mode:
            self.status_label.config(text=f"Đã random {len(self.waypoints)} điểm mốc.")
        else:
            self.status_label.config(text=f"Đã random {len(self.waypoints)} điểm mốc (bật chế độ để hiển thị)")
        self.draw_maze()

    def generate_new_maze(self):
        # Sinh me cung moi va cap nhat trang thai hien thi.
        for attempt in range(MAX_GENERATION_ATTEMPTS):
            # Tao me cung nen va them do phuc tap
            grid = self.generate_maze_base()
            self.carve_loops(grid)
            self.braid_maze(grid)

            # Chon start, exit, waypoint
            source = self.pick_random_start(grid)
            if source is None:
                continue
            exits = self.place_distinct_exits(grid, source, EXIT_COUNT)
            waypoints = self.generate_waypoints(grid, source, exits)
            
            if len(exits) >= 2:
                # Luu trang thai me cung hop le
                self.maze = grid
                self.start = list(source)
                self.exits = exits
                self.waypoints = waypoints
                self.status_label.config(text="Đã tạo mê cung mới.")
                self.stats_label.config(text="Bước đi: -, Đã duyệt: -, Thời gian: -, Lối ra: -")
                self.draw_maze()
                return

        # Neu qua nhieu lan khong du exit, tao me cung toi thieu
        grid = self.generate_maze_base()
        self.carve_loops(grid)
        self.braid_maze(grid)
        source = self.pick_random_start(grid)
        if source is None:
            source = tuple(START_POSITION)
        exits = self.place_distinct_exits(grid, source, 2)
        waypoints = self.generate_waypoints(grid, source, exits)
        
        self.maze = grid
        self.start = list(source)
        self.exits = exits
        self.waypoints = waypoints
        self.status_label.config(text="Đã tạo mê cung mới.")
        self.stats_label.config(text="Bước đi: -, Đã duyệt: -, Thời gian: -, Lối ra: -")
        self.draw_maze()

    def solve_gbfs(self, grid: List[List[int]], source: Tuple[int, int],
                   goals: List[Tuple[int, int]]) -> Tuple[List[Tuple[int, int]],
                                                           List[Tuple[int, int]],
                                                           Tuple[int, int] | None]:
        # Giai me cung bang GBFS theo heuristic Manhattan.
        goal_set = set(goals)

        def heuristic(r: int, c: int) -> int:
            # Tinh heuristic Manhattan toi diem dich gan nhat.
            return min(abs(r - gr) + abs(c - gc) for gr, gc in goals)

        open_set = [(heuristic(source[0], source[1]), source)]
        parent = {source: None}
        visited_set = set()
        visited_order = []

        while open_set:
            open_set.sort(key=lambda item: item[0])
            _, current = open_set.pop(0)
            if current in visited_set:
                continue

            visited_set.add(current)
            visited_order.append(current)

            if current in goal_set:
                path = []
                node = current
                while node is not None:
                    path.append(node)
                    node = parent[node]
                path.reverse()
                return visited_order, path, current

            r, c = current
            for nr, nc in self.neighbors4(r, c):
                if grid[nr][nc] == 0 and (nr, nc) not in visited_set and (nr, nc) not in parent:
                    parent[(nr, nc)] = current
                    open_set.append((heuristic(nr, nc), (nr, nc)))

        return visited_order, [], None

    def solve_astar(self, grid: List[List[int]], source: Tuple[int, int], 
                    goals: List[Tuple[int, int]]) -> Tuple[List[Tuple[int, int]], 
                                                            List[Tuple[int, int]], 
                                                            Tuple[int, int] | None]:
        # Giai me cung bang A* voi f = g + h.
        goal_set = set(goals)
        
        def heuristic(r: int, c: int) -> int:
            # Tinh heuristic Manhattan toi diem dich gan nhat.
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
        # Ve me cung va cac lop duyet/duong di len canvas.
        if visited is None:
            visited = set()
        if path is None:
            path = set()
        if astar_visited is None:
            astar_visited = set()

        # Lưu trạng thái vẽ gần nhất để resize/refresh không xóa kết quả animation.
        self.last_visited = set(visited)
        self.last_path = set(path)
        self.last_astar_visited = set(astar_visited)
        self.last_goal = goal
        self.last_santa = santa

        # Lấy kích thước vùng vẽ sau update_idletasks để đảm bảo giá trị đúng
        # Cap nhat kich thuoc canvas thuc te
        self.canvas.update_idletasks()
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width > 100 and canvas_height > 100:
            # Tính kích thước ô để lấp đầy không gian
            cell_width = canvas_width / COLS
            cell_height = canvas_height / ROWS
            
            # Dùng min để giữ tỉ lệ vuông và vừa vùng vẽ
            self.current_cell_size = min(cell_width, cell_height)

        # Cap nhat anh theo kich thuoc moi
        self.update_santa_image()
        self.update_chimney_image()

        # Xoa toan bo khung truoc khi ve lai
        self.canvas.delete("all")

        for r in range(ROWS):
            for c in range(COLS):
                # Tinh toa do ve cho o hien tai
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
                
                # Ve o vuong theo mau tuong/duong/duyet
                self.canvas.create_rectangle(x, y, x + self.current_cell_size, y + self.current_cell_size, fill=color, outline="")

        # Vẽ lối ra
        for er, ec in self.exits:
            # Ve o exit tren canvas
            x, y = ec * self.current_cell_size, er * self.current_cell_size
            self.canvas.create_rectangle(x, y, x + self.current_cell_size, y + self.current_cell_size, fill=COLOR_EXIT, outline="")

        # Vẽ điểm mốc nếu đang bật chế độ
        if self.waypoint_mode:
            for wr, wc in self.waypoints:
                # Uu tien ve anh ong khoi neu co
                if not self.draw_chimney_at(wr, wc):
                    x, y = wc * self.current_cell_size, wr * self.current_cell_size
                    self.canvas.create_rectangle(x, y, x + self.current_cell_size, y + self.current_cell_size, fill=COLOR_WAYPOINT, outline="")

        # Vẽ điểm bắt đầu
        sr, sc = self.start
        # Ve o bat dau
        x, y = sc * self.current_cell_size, sr * self.current_cell_size
        self.canvas.create_rectangle(x, y, x + self.current_cell_size, y + self.current_cell_size, fill=COLOR_START, outline="")

        # Vẽ đích
        if goal:
            # Ve o dich
            gr, gc = goal
            x, y = gc * self.current_cell_size, gr * self.current_cell_size
            self.canvas.create_rectangle(x, y, x + self.current_cell_size, y + self.current_cell_size, fill=COLOR_GOAL, outline="")

        if santa:
            # Ve Santa di chuyen theo duong
            self.draw_santa_at(santa[0], santa[1])

        self.root.update_idletasks()

    def set_algorithm(self, algo: str):
        # Cap nhat thuat toan dang su dung.
        self.algorithm = algo
        self.algo_label.config(text=f"Thuật toán: {self.algorithm}")
        self.status_label.config(text=f"Đã chọn thuật toán: {self.algorithm}")

    def show_algorithm_menu(self):
        # Hien menu chon thuat toan.
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="GBFS", command=lambda: self.set_algorithm("GBFS"))
        menu.add_command(label="A*", command=lambda: self.set_algorithm("ASTAR"))

        x = self.algo_btn.winfo_rootx()
        y = self.algo_btn.winfo_rooty() + self.algo_btn.winfo_height()
        menu.tk_popup(x, y)
        menu.grab_release()

    def solve_maze(self):
        # Giai me cung theo che do hien tai va animate ket qua.
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

            targets = self.exits

            candidate_results = []
            for waypoint in self.waypoints:
                start_time = time.time()
                if self.algorithm == "GBFS":
                    visited_1, path_1, reached_wp = self.solve_gbfs(self.maze, tuple(self.start), [waypoint])
                    visited_2, path_2, exit_pos = self.solve_gbfs(self.maze, waypoint, targets)
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

            # Mô phỏng các ô đã duyệt trước
            visited_set = set()
            for idx, (r, c) in enumerate(visited_order):
                visited_set.add((r, c))
                if self.should_render_frame(idx, len(visited_order)):
                    self.draw_maze(visited=visited_set, goal=exit_pos)
                    self.ui_pump(VISITED_CELL_DELAY_MS)
            
            # Mô phỏng đường đi sau
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
        targets = self.exits
        if not targets:
            self.status_label.config(text="Không có mục tiêu hợp lệ.")
            return
        
        self.draw_maze()
        self.status_label.config(text=f"Đang giải mê cung bằng {self.algorithm}...")
        self.is_animating = True
        self.ui_pump()
        
        start_time = time.time()
        
        if self.algorithm == "GBFS":
            visited_order, path, exit_pos = self.solve_gbfs(self.maze, tuple(self.start), targets)
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

        # Mô phỏng các ô đã duyệt
        visited_set = set()
        for idx, (r, c) in enumerate(visited_order):
            visited_set.add((r, c))
            if self.should_render_frame(idx, len(visited_order)):
                self.draw_maze(visited=visited_set, goal=exit_pos)
                self.ui_pump(VISITED_CELL_DELAY_MS)

        # Mô phỏng đường đi
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
        goal_type = "Lối ra"
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
        # So sanh GBFS va A* tren cung mot me cung
        if self.is_animating:
            return

        # Lay danh sach dich (loi ra)
        targets = self.exits
        if not targets:
            self.status_label.config(text="Không có mục tiêu hợp lệ.")
            return

        # Chuan bi giao dien truoc khi chay so sanh
        self.draw_maze()
        self.status_label.config(text="Đang so sánh GBFS và A*...")
        self.comparison_label.config(text="Dang tinh toan...")
        self.is_animating = True
        self.ui_pump()

        compare_detail = None
        if self.waypoint_mode and self.waypoints:
            # Che do waypoint: can tinh ket qua theo waypoint
            if self.waypoint_all_mode:
                # Di qua tat ca waypoint
                gbfs_result = self.solve_route_all_waypoints("GBFS", self.waypoints, targets)
                astar_result = self.solve_route_all_waypoints("ASTAR", self.waypoints, targets)
                if gbfs_result:
                    gbfs_result = {
                        **gbfs_result,
                        "waypoint": None,
                        "scan_visited": gbfs_result.get("visited_order", []),
                    }
                if astar_result:
                    astar_result = {
                        **astar_result,
                        "waypoint": None,
                        "scan_visited": astar_result.get("visited_order", []),
                    }
                compare_detail = "Che do qua tat ca diem moc"
            else:
                # Chon 1 waypoint toi uu
                gbfs_result = self.solve_route_through_waypoints("GBFS", self.waypoints, targets)
                astar_result = self.solve_route_through_waypoints("ASTAR", self.waypoints, targets)

            if gbfs_result:
                gbfs_visited = gbfs_result["visited_order"]
                gbfs_path = gbfs_result["full_path"]
                gbfs_exit = gbfs_result["target"]
                gbfs_steps = gbfs_result["total_steps"]
                gbfs_time = gbfs_result["total_time"]
                gbfs_waypoint = gbfs_result["waypoint"]
                gbfs_saved = gbfs_result.get("saved_steps")
            else:
                gbfs_visited = []
                gbfs_path = []
                gbfs_exit = None
                gbfs_steps = 0
                gbfs_time = 0.0
                gbfs_waypoint = None
                gbfs_saved = None

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

            if not self.waypoint_all_mode:
                # Ghi chu ly do chon waypoint
                gbfs_saved_text = f"{gbfs_saved} buoc" if gbfs_saved is not None else "khong co moc so sanh"
                astar_saved_text = f"{astar_saved} buoc" if astar_saved is not None else "khong co moc so sanh"
                compare_detail = (
                    f"GBFS duyet {len(self.waypoints)} waypoint, chon WP={gbfs_waypoint}, tiet kiem={gbfs_saved_text} | "
                    f"A* duyet {len(self.waypoints)} waypoint, chon WP={astar_waypoint}, tiet kiem={astar_saved_text}"
                )
                self.status_label.config(text="Dang danh gia waypoint cho GBFS/A* truoc khi chon moc toi uu...")
                if gbfs_result:
                    # Animate qua trinh danh gia waypoint
                    self.animate_waypoint_scan(gbfs_result.get("scan_visited", []), "GBFS")
                if astar_result:
                    self.animate_waypoint_scan(astar_result.get("scan_visited", []), "ASTAR")
            else:
                # Animate che do qua tat ca waypoint
                self.status_label.config(text="Dang so sanh che do tat ca diem moc...")
                if gbfs_result:
                    self.animate_waypoint_scan(gbfs_result.get("scan_visited", []), "GBFS")
                if astar_result:
                    self.animate_waypoint_scan(astar_result.get("scan_visited", []), "ASTAR")
        else:
            # Che do binh thuong: chay GBFS va A* truc tiep
            start_time = time.time()
            gbfs_visited, gbfs_path, gbfs_exit = self.solve_gbfs(self.maze, tuple(self.start), targets)
            gbfs_time = (time.time() - start_time) * 1000
            gbfs_steps = max(len(gbfs_path) - 1, 0) if gbfs_path else 0

            start_time = time.time()
            astar_visited, astar_path, astar_exit = self.solve_astar(self.maze, tuple(self.start), targets)
            astar_time = (time.time() - start_time) * 1000
            astar_steps = max(len(astar_path) - 1, 0) if astar_path else 0
            self.status_label.config(text="Dang so sanh... Xem ket qua phia duoi")

        # Tinh phan tram tiet kiem so o duyet
        if len(gbfs_visited) > 0:
            astar_efficiency = (len(gbfs_visited) - len(astar_visited)) / len(gbfs_visited) * 100
        else:
            astar_efficiency = 0

        # Luu ket qua so sanh de hien thi
        self.comparison_results = {
            'gbfs_steps': gbfs_steps,
            'gbfs_visited': len(gbfs_visited),
            'gbfs_time': gbfs_time,
            'gbfs_path': gbfs_path,
            'astar_steps': astar_steps,
            'astar_visited': len(astar_visited),
            'astar_time': astar_time,
            'astar_path': astar_path,
            'efficiency': astar_efficiency
        }

        compare_waypoint = gbfs_waypoint if (self.waypoint_mode and self.waypoints) else None
        self.append_compare_history(
            start_pos=tuple(self.start),
            gbfs_steps=gbfs_steps,
            gbfs_visited=len(gbfs_visited),
            gbfs_time=gbfs_time,
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
            # Animate lai duong di GBFS
            gbfs_visited_set = set(gbfs_result.get("scan_visited", []) if gbfs_result else [])
            gbfs_path_set = set()
            for idx, (r, c) in enumerate(gbfs_path):
                gbfs_path_set.add((r, c))
                if self.should_render_frame(idx, len(gbfs_path)):
                    self.draw_maze(visited=gbfs_visited_set, path=gbfs_path_set, goal=gbfs_exit, santa=(r, c))
                    self.ui_pump(3)

            if gbfs_path:
                sr, sc = gbfs_path[-1]
                self.draw_maze(visited=gbfs_visited_set, path=gbfs_path_set, goal=gbfs_exit, santa=(sr, sc))

            self.ui_pump(200)

            # Animate lai duong di A*
            astar_visited_set = set(astar_result.get("scan_visited", []) if astar_result else [])
            astar_path_set = set()
            for idx, (r, c) in enumerate(astar_path):
                astar_path_set.add((r, c))
                if self.should_render_frame(idx, len(astar_path)):
                    self.draw_maze(astar_visited=astar_visited_set, path=astar_path_set, goal=astar_exit, santa=(r, c))
                    self.ui_pump(3)

            if astar_path:
                sr, sc = astar_path[-1]
                self.draw_maze(astar_visited=astar_visited_set, path=astar_path_set, goal=astar_exit, santa=(sr, sc))
        else:
            # Animate GBFS truoc
            gbfs_visited_set = set()
            for idx, (r, c) in enumerate(gbfs_visited):
                gbfs_visited_set.add((r, c))
                if self.should_render_frame(idx, len(gbfs_visited)):
                    self.draw_maze(visited=gbfs_visited_set, goal=gbfs_exit)
                    self.ui_pump(1)

            gbfs_path_set = set()
            for idx, (r, c) in enumerate(gbfs_path):
                gbfs_path_set.add((r, c))
                if self.should_render_frame(idx, len(gbfs_path)):
                    self.draw_maze(visited=gbfs_visited_set, path=gbfs_path_set, goal=gbfs_exit, santa=(r, c))
                    self.ui_pump(3)

            if gbfs_path:
                sr, sc = gbfs_path[-1]
                self.draw_maze(visited=gbfs_visited_set, path=gbfs_path_set, goal=gbfs_exit, santa=(sr, sc))

            self.ui_pump(200)

            # Sau do animate A*
            astar_visited_set = set()
            for idx, (r, c) in enumerate(astar_visited):
                astar_visited_set.add((r, c))
                if self.should_render_frame(idx, len(astar_visited)):
                    self.draw_maze(visited=gbfs_visited_set, astar_visited=astar_visited_set, goal=astar_exit)
                    self.ui_pump(1)

            astar_path_set = set()
            for idx, (r, c) in enumerate(astar_path):
                astar_path_set.add((r, c))
                if self.should_render_frame(idx, len(astar_path)):
                    self.draw_maze(
                        visited=gbfs_visited_set,
                        astar_visited=astar_visited_set,
                        path=astar_path_set,
                        goal=astar_exit,
                        santa=(r, c),
                    )
                    self.ui_pump(5)

            if astar_path:
                sr, sc = astar_path[-1]
                self.draw_maze(
                    visited=gbfs_visited_set,
                    astar_visited=astar_visited_set,
                    path=astar_path_set,
                    goal=astar_exit,
                    santa=(sr, sc),
                )

        self.is_animating = False
        self.status_label.config(text="Hoan thanh so sanh. Xem ket qua phia duoi.")

    def display_comparison(self):
        # Hien thi ket qua so sanh GBFS vs A*
        if self.comparison_results is None:
            text = "Khong co du lieu so sanh"
            self.comparison_label.config(text=text, fg="#FF6B6B")
            self.root.update_idletasks()
            return
        
        # Doc ket qua da luu
        r = self.comparison_results
        # Tạo chuỗi so sánh dễ đọc
        comparison_text = (
            f"GBFS(Cyan):  {r['gbfs_steps']} buoc | {r['gbfs_visited']} o duyet | {r['gbfs_time']:.2f}ms  |  "
            f"A*(Lime):  {r['astar_steps']} buoc | {r['astar_visited']} o duyet | {r['astar_time']:.2f}ms  |  "
            f"A* TIET KIEM {r['efficiency']:.1f}%"
        )
        
        self.comparison_label.config(text=comparison_text, fg="#FFD700")
        self.root.update_idletasks()

    def generate_waypoints(self, grid: List[List[int]], source: Tuple[int, int], 
                          exits: List[Tuple[int, int]],
                          blocked: List[Tuple[int, int]] | None = None) -> List[Tuple[int, int]]:
        # Sinh ra 4 diem moc ngau nhien, khong trung start/exit
        # Tap hop vi tri khong duoc chon
        used_positions = {source}
        used_positions.update(exits)
        if blocked:
            used_positions.update(blocked)
        # Thu thap tat ca o duong hop le
        all_paths = []
        for r in range(1, ROWS - 1):
            for c in range(1, COLS - 1):
                if grid[r][c] == 0 and (r, c) not in used_positions:
                    all_paths.append((r, c))
        # Neu khong du, tra ve toan bo
        if len(all_paths) < WAYPOINT_COUNT:
            return all_paths
        # Lay mau ngau nhien so waypoint can co
        return random.sample(all_paths, WAYPOINT_COUNT)

    def toggle_waypoint_mode(self):
        # Bat/tat che do diem moc
        # Cap nhat co che waypoint va giao dien
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
        # Bat/tat che do di qua tat ca diem moc
        # Chi cho phep neu che do waypoint dang bat
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
        # Tim thu tu toi uu cac diem bang nearest neighbor heuristic
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
        # Giai mot doan duong bang thuat toan chi dinh.
        if algorithm == "GBFS":
            return self.solve_gbfs(self.maze, source, goals)
        return self.solve_astar(self.maze, source, goals)

    def bfs_scan_from_source(self, source: Tuple[int, int], waypoints: List[Tuple[int, int]] | None = None):
        # Quet BFS tu diem bat dau, dung khi da tim het waypoint.
        # Luu khoang cach va parent de truy vet
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
                # Dung neu da tim het waypoint
                if len(found_waypoints) == len(waypoint_set):
                    break
            for nr, nc in self.neighbors4(r, c):
                if self.maze[nr][nc] == 0 and dist[nr][nc] == -1:
                    dist[nr][nc] = dist[r][c] + 1
                    parent[(nr, nc)] = (r, c)
                    q.append((nr, nc))

        return visited_order, dist, parent

    def bfs_scan_from_targets(self, targets: List[Tuple[int, int]]):
        # Quet BFS tu tap dich de lay khoang cach toi moi o.
        # Khoi tao hang doi tu nhieu dich
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
        # Phuc hoi duong di tu bang parent tu start den target.
        # Neu khong co duong di thi tra ve rong
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
        # Phuc hoi duong di tu source den dich theo parent.
        # Neu khong co duong di thi tra ve rong
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
        # Chon waypoint toi uu va giai duong di qua waypoint do.
        if not waypoints or not targets:
            return None

        # Quet BFS de hien thi qua trinh danh gia
        start_time = time.time()
        scan_visited, _, _ = self.bfs_scan_from_source(tuple(self.start), waypoints)
        candidates = []

        for waypoint in waypoints:
            # Tinh duong start -> waypoint -> exit
            visited_1, path_1, reached_wp = self.solve_segment(algorithm, tuple(self.start), [waypoint])
            if not path_1 or not reached_wp:
                continue

            visited_2, path_2, exit_pos = self.solve_segment(algorithm, waypoint, targets)
            if not path_2 or not exit_pos:
                continue

            full_path = path_1 + path_2[1:]
            visited_order = list(dict.fromkeys(visited_1 + visited_2))
            # Luu ung vien hop le
            candidates.append({
                "waypoint": waypoint,
                "order": (waypoint,),
                "visited_order": visited_order,
                "full_path": full_path,
                "target": exit_pos,
                "total_steps": max(len(full_path) - 1, 0),
                "total_time": 0.0,
                "scan_visited": scan_visited,
            })

        if not candidates:
            return None

        # Chon ung vien co tong buoc nho nhat
        candidates.sort(key=lambda item: item["total_steps"])
        best = candidates[0]
        elapsed_total = (time.time() - start_time) * 1000
        best["total_time"] = elapsed_total

        second_best_steps = candidates[1]["total_steps"] if len(candidates) > 1 else None
        best["second_best_steps"] = second_best_steps
        best["saved_steps"] = (second_best_steps - best["total_steps"]) if second_best_steps is not None else None
        best["evaluated_count"] = len(candidates)
        best["total_waypoints"] = len(waypoints)
        return best

    def solve_route_all_waypoints(self, algorithm: str, waypoints: List[Tuple[int, int]],
                                  targets: List[Tuple[int, int]]):
        # Tim thu tu di qua tat ca waypoint voi tong buoc nho nhat.
        if not waypoints or not targets:
            return None

        # Tinh ban do khoang cach tu start va moi waypoint
        start_time = time.time()
        start_pos = tuple(self.start)
        dist_maps = {start_pos: self.bfs_distances(self.maze, start_pos)}
        for wp in waypoints:
            dist_maps[wp] = self.bfs_distances(self.maze, wp)

        best = None
        # Thu tat ca thu tu waypoint
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

        # Dung lai thuat toan de phuc hoi duong di chi tiet
        visited_order: List[Tuple[int, int]] = []
        full_path: List[Tuple[int, int]] = []
        current = start_pos
        solve_segment = self.solve_gbfs if algorithm == "GBFS" else self.solve_astar

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
        # Mo phong qua trinh quet waypoint tren giao dien.
        if not scan_visited:
            return

        # Theo doi so waypoint da duyet
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
                    text=f"{algorithm}: dang danh gia waypoint, da di qua {len(seen_waypoints)}/{total_waypoints} waypoint..."
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
                    text=f"{algorithm}: dang danh gia waypoint, da di qua {len(seen_waypoints)}/{total_waypoints} waypoint..."
                )
                if self.should_render_frame(idx, len(scan_visited)):
                    self.draw_maze(visited=visited_set)
                    self.ui_pump(visit_delay)

    def solve_maze(self):
        # Giai me cung theo che do waypoint va animate ket qua.
        if self.is_animating:
            return

        if self.waypoint_all_mode:
            # Che do bat buoc qua tat ca waypoint
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
            # Che do qua 1 waypoint toi uu
            if not self.waypoints:
                self.status_label.config(text="Không có điểm mốc được sinh.")
                return

            self.status_label.config(text=f"Đang giải mê cung qua 1 điểm mốc tối ưu bằng {self.algorithm}...")
            self.is_animating = True
            self.ui_pump()

            targets = self.exits
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

        # Che do binh thuong
        targets = self.exits
        if not targets:
            self.status_label.config(text="Không có mục tiêu hợp lệ.")
            return

        self.status_label.config(text=f"Đang giải mê cung bằng {self.algorithm}...")
        self.is_animating = True
        self.ui_pump()

        start_time = time.time()
        if self.algorithm == "GBFS":
            visited_order, path, exit_pos = self.solve_gbfs(self.maze, tuple(self.start), targets)
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
        goal_type = "Lối ra"
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
        # Chay vong lap giao dien chinh.
        self.root.mainloop()


if __name__ == "__main__":
    solver = MazeSolver()
    solver.run()
