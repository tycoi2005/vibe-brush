# Brief nhờ Artist Review quy trình vẽ AI (Open Brush)

## 1) Mục tiêu
Mục tiêu của hệ thống là biến mô tả ngôn ngữ tự nhiên thành một tác phẩm 3D trong Open Brush, theo quy trình nhiều bước để giữ bố cục rõ ràng và giảm lỗi vẽ lan man.

## 2) Quy trình vẽ hiện tại (4 stage)
1. Stage 1 - Ý tưởng (Ideas)
   - Tạo concept brief bằng chữ: tầm nhìn tổng thể, bố cục, màu, brush, độ sâu không gian.
   - Chưa vẽ, chỉ định hướng sáng tác.
2. Stage 2 - Dựng khối thô (Sketch)
   - Dùng primitive/wireframe để chốt form lớn và tỷ lệ trong không gian 3D.
   - Màu trung tính, ít chi tiết, có new_sketch để làm nền sạch.
3. Stage 3 - Hoàn thiện tổng thể (Overall)
   - Vẽ đầy đủ các mảng chính bằng palette chính thức, phân lớp foreground/midground/background.
   - Nếu dùng SVG thì phải tạo cảm giác 3D (nhiều lát Z + nối trục).
4. Stage 4 - Chi tiết và polish (Details)
   - Chỉ thêm hiệu ứng và vi chi tiết: glow, texture, hạt, haze.
   - Không xóa canvas, không vẽ lại khối chính.

## 3) Logic nghệ thuật đằng sau pipeline
- Đi từ lớn đến nhỏ: ý tưởng -> khối -> tổng thể -> chi tiết.
- Ưu tiên đọc hình ở xa trước: silhouette, trọng tâm, phân tầng chiều sâu.
- Chi tiết chỉ thêm khi cấu trúc đã ổn để tránh rối hình.
- Giảm rủi ro lệch phong cách bằng cách cố định concept + palette ngay từ Stage 1.

## 4) Những điểm cần artist góp ý
1. Bố cục: điểm nhìn có rõ trọng tâm chưa? Có bị rối ở các lớp Z không?
2. Khối và tỷ lệ: Stage 2 đã đủ chắc để đỡ Stage 3 chưa?
3. Nhịp chi tiết: Stage 4 có quá tay hoặc thiếu điểm nhấn không?
4. Màu và ánh sáng: palette có nhất quán mood không? Rim light/fog có hỗ trợ chiều sâu thật sự không?
5. Brush language: chọn brush cho từng chất liệu (lông, đá, sương, ánh sáng) đã hợp lý chưa?
6. Tính mạch lạc: từ concept đến tranh cuối có giữ đúng tinh thần ban đầu không?

## 5) Form feedback ngắn (đề xuất)
- Tổng thể tác phẩm (1-10):
- Điểm mạnh nhất:
- 2 điểm cần sửa gấp:
- Ưu tiên sửa theo thứ tự (1 -> 3):
- Gợi ý kỹ thuật cụ thể (brush/màu/layer/độ sâu):

## 6) Kỳ vọng sau review
Sau khi nhận góp ý, team sẽ cập nhật theo thứ tự ưu tiên:
1. Quy tắc bố cục và staging.
2. Quy tắc màu - ánh sáng.
3. Quy tắc detail pass để tránh over-render.
