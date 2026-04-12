# TTNT - AI Maze Solver Mini Project

Ứng dụng web nhỏ mô phỏng đồ án trí tuệ nhân tạo:
- Tạo mê cung ngẫu nhiên
- Có nhiều lối ra với độ dài đường đi khác nhau
- AI tìm đường ngắn nhất đến lối ra (BFS hoặc A*)
- Hiển thị animation quá trình duyệt và đường đi kết quả

## Chạy dự án

Đây là dự án thuần HTML/CSS/JS, không cần cài package.

1. Mở file `index.html` trong thư mục dự án bằng trình duyệt
2. Bấm **Tạo mê cung** để tạo mê cung mới
3. Chọn thuật toán (**BFS** hoặc **A***)
4. Bấm **Giải mê cung** để AI tìm đường ngắn nhất

## Tính năng

- Sinh mê cung bằng DFS backtracking
- Tạo nhiều lối ra ở biên mê cung
- Cố gắng đảm bảo các lối ra có khoảng cách khác nhau từ điểm bắt đầu
- Hiển thị:
  - ô đã duyệt
  - đường đi ngắn nhất
  - số bước, số ô đã duyệt, thời gian chạy, lối ra được chọn
