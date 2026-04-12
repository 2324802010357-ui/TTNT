# TTNT - AI Maze Solver Mini Project

Ứng dụng web nhỏ mô phỏng đồ án trí tuệ nhân tạo:
- Tạo **solid braided maze** — mê cung hoàn toàn liền khối với hành lang dày đặc liên kết
- Có nhiều lối ra với độ dài đường đi khác nhau + thêm các điểm địch bên trong
- AI tìm đường ngắn nhất đến mục tiêu gần nhất (BFS hoặc A*)
- Hiển thị animation quá trình duyệt và đường đi kết quả

## Chạy dự án

Đây là dự án thuần HTML/CSS/JS, không cần cài package.

1. Mở file `index.html` trong thư mục dự án bằng trình duyệt
2. Bấm **Tạo mê cung** để tạo mê cung mới
3. Chọn thuật toán (**BFS** hoặc **A***)
4. Bấm **Giải mê cung** để AI tìm đường đến mục tiêu gần nhất

## Tính năng

### Sinh solid braided maze (mê cung liền khối xoắn)
- Sinh mê cung cơ bản bằng DFS backtracking
- **Carve loops (90%)**: Mở ~90% các bức tường để tạo chu trình, giúp hành lang **liền khối** với nhau
- **Braid dead ends (98%)**: Kết nối ~98% cụt ngõ thành những vòng liên kết — gần như loại bỏ hoàn toàn dead ends
- **Đảm bảo 4 nhánh từ start**: Nếu start chỉ có ≤3 cửa, sẽ mở thêm nhánh để có >=4 lựa chọn

**Kết quả**: Một khối hành lang dày đặc, liên thông, với hầu như không có cụt ngõ mù

### Exits (Lối ra)
- Tạo nhiều lối ra ở biên mê cung
- Cố gắng đảm bảo các lối ra có khoảng cách khác nhau từ điểm bắt đầu
- **Màu xanh lục** trên canvas

### Enemies (Điểm địch)
- Đặt các điểm địch bên trong mê cung ở vị trí xa từ start (>= `ENEMY_MIN_DISTANCE`)
- Ưu tiên các vị trí ở các vùng sâu
- **Màu tím** trên canvas

### Giải mê cung
- **BFS**: Tìm kiếm rộng trước, đảm bảo đường ngắn nhất (số bước ít nhất)
- **A***: Tìm kiếm có thông tin với heuristic Manhattan distance, thường nhanh hơn BFS
- Cả hai đều tìm đến **mục tiêu gần nhất** từ tập {exits + enemies}
- Hiển thị:
  - ô đã duyệt (xanh da trời) — rất nhiều ô trong maze liền khối do có nhiều đường xoắn
  - đường đi ngắn nhất (cam)
  - số bước, số ô đã duyệt, thời gian chạy, loại/vị trí mục tiêu đạt được

## Cấu hình (trong `script.js`)

Bạn có thể điều chỉnh độ phức tạp bằng các hằng số ở đầu file:

```javascript
// Kích thước mê cung
const ROWS = 31;
const COLS = 51;
const CELL_SIZE = 18;

// Complexity features - Solid Braided Maze (Liền khối)
const ROOM_COUNT = 0;         // Không dùng rooms
const LOOP_CARVE_RATE = 0.90; // 90% chu trình - hành lang liền khối
const BRAID_RATE = 0.98;      // 98% dead ends kết nối - gần như không có ngõ cụt
const MIN_START_BRANCHES = 4; // 4 lựa chọn từ start
const ENEMY_COUNT = 3;         // Số điểm địch
const ENEMY_MIN_DISTANCE = 8;  // Khoảng cách tối thiểu từ start cho enemy
const EXIT_COUNT = 4;          // Số lối ra
```

### Điều chỉnh độ phức tạp

- **Tăng `LOOP_CARVE_RATE`** (e.g., 0.95) → Mê cung xoắn chặt chẽ hơn, chân chính hơn
- **Tăng `BRAID_RATE`** (e.g., 0.99+) → Loại bỏ gần như 100% dead ends (có thể làm maze khó sinh do quá dày đặc)
- **Giảm `LOOP_CARVE_RATE`** (e.g., 0.75) → Mê cung ít xoắn hơn, nhiều cụt ngõ hơn

### Về Solid Braided Maze

Solid braided maze là mê cung hoàn toàn **liền khối** (connected solid block) mà không có (hoặc rất ít) dead ends:
- ✅ Gần như tất cả hành lang đều kết nối với nhau thành các vòng
- ✅ Hầu như không có lối sáng mù — mỗi di chuyển đều dẫn đến lựa chọn khác
- ✅ Cực kỳ thách thức cho AI pathfinding (BFS phải duyệt qua nhiều đường xoắn tương đương)
- ✅ Mê cung trông như một **khối liên thông** chứ không phải các hành lang tách rời

**So sánh với braided maze thường**: Solid braided maze có loop carving (90%) và braiding rate (98%) cao hơn, tạo ra sự liên kết chặt chẽ hơn.



