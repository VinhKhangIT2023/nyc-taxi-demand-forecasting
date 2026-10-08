# Tổng kết giai đoạn 2 — Chuẩn bị dữ liệu 2023–2025

Ngày tổng hợp: 07/10/2026. Trạng thái: hoàn thành, nghiệm thu dữ liệu đạt. Đây là giai đoạn triển khai nội bộ, không phải toàn bộ đợt nộp giai đoạn 2 của môn học.

## 1. Mục tiêu và phạm vi

Chuẩn bị Yellow Taxi NYC TLC đủ 36 tháng của 2023–2025 để phân tích và tạo mô hình dự báo lượt đón theo vùng/giờ; lưu quy tắc làm sạch, nguồn và bằng chứng kiểm tra.

## 2. Công việc đã thực hiện

- Tải 36 file tháng, ghi URL, schema, số dòng và checksum; giữ nguyên raw.
- Cách ly lần lượt bản ghi ngoài tháng nguồn, vùng 264/265 và thời lượng không dương. Giữ dữ liệu cách ly cùng lý do.
- Giữ các bất thường khác theo quy tắc đã duyệt, thêm cờ chất lượng; không tự sửa tiền âm, điền hành khách hoặc xóa trùng.
- Chuẩn hóa schema các năm, giữ cột phí mới năm 2025 và biểu diễn null cho năm chưa có.
- Tạo lưới 263 vùng theo giờ; phân biệt 0 với thiếu toàn nguồn và che nhãn cả hai ngày DST mỗi năm.
- Chuẩn bị loader theo manifest và chia tập theo thời gian cho hai thí nghiệm lịch sử A/B; chưa huấn luyện mô hình.

## 3. Kết quả đạt được

| Năm | Dòng raw | Chuyến giữ lại |
|---|---:|---:|
| 2023 | 38.310.226 | 37.909.554 |
| 2024 | 41.169.720 | 41.010.718 |
| 2025 | 48.722.602 | 48.073.756 |
| Tổng | 128.202.548 | 126.994.028 |

Lưới có 6.917.952 dòng vùng–giờ, trong đó 6.880.080 dòng đủ điều kiện làm nhãn trước khi tạo đặc trưng. Cả ba năm đạt kiểm tra nghiệm thu; 15/15 kiểm thử đã đạt tại thời điểm kết thúc xử lý. Số dòng trùng dư giữ lại lần lượt là 2, 4, 1 cho 2023, 2024, 2025.

## 4. Đầu ra và kiểm chứng

| File hoặc thư mục | Vai trò / bằng chứng |
|---|---|
| [DU_LIEU.md](../DU_LIEU.md) | Hướng dẫn chi tiết, số liệu cách ly và cách tái lập |
| [stage2_acceptance.json](../../artifacts/metrics/stage2_acceptance.json) | Kết quả nghiệm thu `complete=true` của cả ba năm |
| [temporal_splits.json](../../configs/temporal_splits.json) | Khoảng train, validation và test |
| `data/processed/yellow_YYYY_v1/trips/` | Partition chuyến theo tháng; lưu cục bộ, không push dữ liệu |
| `data/processed/hourly_grid_v1/YYYY/` | Lưới vùng–giờ và audit |
| [open_dataset.py](../../src/ingestion/open_dataset.py), [load_split.py](../../src/ingestion/load_split.py) | Đọc đúng partition và chọn nhãn theo thời gian |
| [verify_stage2.py](../../src/processing/verify_stage2.py) | Đối soát checksum, bảo toàn dòng, lưới đủ/duy nhất, 0/null/DST và chia tập |

## 5. Quyết định và lý do

Theo [nhật ký quyết định](../QUYET_DINH.md), bảo toàn dữ liệu nguồn, chỉ áp dụng quy tắc đã duyệt. Mask cả ngày DST vì timestamp không có UTC offset để phân biệt giờ lặp. Không xóa trùng tự động vì không có ID chuyến duy nhất. Thí nghiệm A dùng lịch sử 2024, B thêm 2023; cùng validation tháng 10–12/2024, dành 2025 cho đánh giá cuối để tránh chọn mô hình bằng dữ liệu test.

## 6. Vấn đề và giới hạn

Năm 2025 có 545.589 dòng thời lượng không dương được cách ly (543.355 bằng 0, 2.234 âm), tăng mạnh so với hai năm trước; chưa xác định nguyên nhân từ nguồn. Có bảng ảnh hưởng theo vùng/giờ để phục vụ diễn giải. Dữ liệu phản ánh chuyến đã phục vụ sau làm sạch, không đo toàn bộ nhu cầu tiềm ẩn. Làm sạch dùng thời điểm trả nên chưa phải mô phỏng khả năng có dữ liệu theo thời gian thực.

## 7. Bàn giao

Dữ liệu và cấu hình chia tập đã sẵn sàng. Các phần còn lại của dự án gồm tích hợp Spark/HBase, đặc trưng và mô hình, dashboard, báo cáo/slide/demo; chưa coi các phần này là hoàn thành. Không cộng lại tập thử tháng 01/2024 khi đọc dữ liệu cả năm. Hướng mở rộng lịch sử chỉ được kết luận sau thực nghiệm validation.
