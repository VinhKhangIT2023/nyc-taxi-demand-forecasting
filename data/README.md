# Danh mục dữ liệu

Nguồn đã được người dùng chốt: [NYC TLC](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page), Yellow Taxi. Phạm vi hiện tại là đủ 36 tháng của **2023–2025**; tháng 01/2024 là bước khảo sát ban đầu.

Cập nhật 07/10/2026: đã xử lý 2023 (37.909.554 chuyến), 2024 (41.010.718), 2025 (48.073.756). Danh mục URL, checksum, dung lượng và số dòng từng file nằm trong `artifacts/metrics/download_manifest_YYYY.json`. Đọc hướng dẫn hiện hành tại `docs/DU_LIEU.md`; nghiệm thu tại `artifacts/metrics/stage2_acceptance.json`. Không gộp thêm tập thử tháng 01/2024 vào dữ liệu cả năm.

`raw/` giữ file gốc; `interim/` chứa kết quả trung gian; `processed/` chứa dữ liệu đã xử lý; `reference/` chứa danh mục vùng và dữ liệu hình học. Các file dữ liệu trong các thư mục này không được Git theo dõi.

Lưu manifest khi tải:

| File | URL nguồn | Ngày tải | SHA256 | Dung lượng | Số dòng | Khoảng thời gian | Ghi chú quyền sử dụng |
|---|---|---|---|---|---|---|---|
| yellow_tripdata_2024-01.parquet | https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet | 05/10/2026 | c4d59da7bbc8abaeeeb1727947ee93d9891a71acb42854bd80db1571b2030510 | 49.961.641 byte | 2.964.624 | Pickup thực tế từ 31/12/2002 đến 01/02/2024; 18 dòng ngoài tháng 01/2024 | Xem điều khoản NYC TLC trước khi phân phối lại |

Đã tải file vào `raw/` và tính SHA256 để nhận diện bản tải; chưa đối chiếu checksum do nhà cung cấp công bố. Bảng trên ghi mốc khảo sát ban đầu; manifest từng năm là danh mục đầy đủ. Dữ liệu gốc được giữ nguyên, dữ liệu đã xử lý nằm riêng trong `processed/`.

Ghi cách tái tải, schema và các thay đổi so với bản gốc. Xem điều khoản của bên cung cấp trước khi phân phối lại dữ liệu. Giữ danh sách file chính xác để người khác tái lập được thực nghiệm.

## Danh mục vùng đã tải

- File: `reference/taxi_zone_lookup.csv`.
- URL: https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv
- Ngày tải: 05/10/2026; 265 dòng dữ liệu, 4 cột, LocationID không trùng.
- SHA256: `1a99e105092230f8620f301edcca7f80d3080642ff404d28ed957d3fa222c8ed`.
- Đây là snapshot danh mục hiện được TLC cung cấp, chưa xác minh phiên bản lịch sử tháng 01/2024. Kết quả đối chiếu tại `docs/lich-su/KIEM_TRA_MA_VUNG.md`.
