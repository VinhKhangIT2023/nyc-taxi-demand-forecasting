# Chuẩn bị dữ liệu giai đoạn 2

## Phạm vi

Chuẩn bị đủ Yellow Taxi 2023, 2024 và 2025. So sánh hai cách chọn lịch sử: A dùng 2024, B dùng 2023 cộng 2024. Năm 2025 là holdout tương lai. Kiểm tra schema/chất lượng holdout được phép; chưa dùng sai số mô hình trên holdout để lựa chọn phương án.

**Đã hoàn thành và nghiệm thu ngày 07/10/2026.** Cả ba năm đạt kiểm tra toàn bộ dữ liệu, kết quả `complete=true` tại `artifacts/metrics/stage2_acceptance.json`; 15/15 kiểm thử đạt. Đã thử đọc chung 36 partition bằng loader, nhận đúng 126.994.028 dòng và cột phí mới null ở các năm cũ. Không xem một thư mục có file là bằng chứng pipeline đã chạy thành công: các manifest phải có complete=true.

## Chính sách đã duyệt

- Giữ nguyên raw, checksum và các file cách ly.
- Cách ly timestamp ngoài tháng nguồn, vùng đón 264/265, thời lượng không dương; ghi lý do và bảo toàn tổng số dòng.
- Giữ các vấn đề khác kèm cờ chất lượng theo v1. Không tự biến tiền âm thành dương, không tự điền số hành khách.
- Các ngày đổi giờ mùa hè: giữ chuyến và số đếm mô tả, nhưng mọi nhãn của cả ngày đều không dùng cho học/đánh giá. Không tự suy ra UTC offset từ timestamp nguồn.
- Giờ có ít nhất một bản ghi raw trong tháng nguồn: vùng không có bản ghi được giữ có số đếm 0. Đây là 0 lượt đón ghi nhận sau chính sách làm sạch, không phải khẳng định không có nhu cầu thực tế.
- Giờ không có bản ghi trên toàn nguồn: số đếm để null. Có dữ liệu toàn nguồn không chứng minh tất cả nhà cung cấp báo cáo đầy đủ.
- Audit các thuộc tính nguồn cho thấy số dòng trùng dư lần lượt là 2 (2023), 4 (2024), 1 (2025). Giữ và báo cáo theo chính sách không tự suy ra cùng chuyến khi thiếu định danh; không tự xóa trùng. Không phát hiện NaN/Infinity không-null trong các cột số thực của tập giữ lại.

## Đầu ra sử dụng

1. `data/processed/yellow_YYYY_v1/trips/part-YYYY-MM.parquet`: chuyến đã xử lý, mỗi file một tháng.
2. `data/processed/hourly_grid_v1/YYYY/zone_hours.parquet`: lưới 263 vùng từ lookup × tất cả nhãn giờ địa phương của năm.
3. `configs/temporal_splits.json`: cấu hình train, validation và test dùng chung cho hai thí nghiệm.
4. `artifacts/metrics/`: manifest tải, đối soát xử lý, kiểm tra trùng, độ phủ và nghiệm thu.

Không đọc đệ quy toàn bộ `data/processed`: có đầu ra trung gian, quarantine và bản chuẩn hóa của cùng dữ liệu. Loader chỉ đọc danh sách partition được manifest chỉ định. File v1 tháng 01/2024 cũ vẫn được giữ nhưng không cộng thêm vào dataset năm 2024.

```powershell
.\.venv\Scripts\python.exe -m src.ingestion.open_dataset --kind hourly --years 2023 2024
.\.venv\Scripts\python.exe -m src.ingestion.open_dataset --kind trips --years 2023 2024
```

Trong Python, đọc các nhãn train của thí nghiệm B mà không nạp cả tập vào RAM:

```python
from src.ingestion.load_split import label_scanner

scanner = label_scanner('B_add_2023', role='train', fold=0)
for batch in scanner.to_batches():
    pass
```

## Hợp đồng dữ liệu theo giờ

| Cột | Ý nghĩa |
|---|---|
| PULocationID | Vùng thuộc danh mục cố định; không chọn top vùng bằng dữ liệu tương lai |
| pickup_hour | Nhãn giờ địa phương, không phải UTC |
| recorded_trip_count | Số chuyến đã giữ theo giờ; null khi cả nguồn không có bản ghi |
| target_trip_count | Nhãn dự báo; null khi thiếu nguồn hoặc thuộc ngày đổi giờ |
| q_source_hour_missing | Cả nguồn không có bản ghi trong giờ |
| q_dst_day | Thuộc một trong hai ngày chuyển giờ của năm |
| q_zero_recorded | Có nguồn trong giờ, nhưng vùng này không có chuyến được giữ |
| model_eligible | Đủ điều kiện làm nhãn theo chính sách hiện tại |

Không forward-fill các nhãn bị mask. Lúc tạo lag/rolling, chỉ dùng giờ trước target; feature phụ thuộc nhãn null phải để thiếu hoặc loại điểm dự báo tương ứng. Lưới đã sẵn sàng cho bước tạo đặc trưng nhưng chưa có lag, rolling hoặc mô hình huấn luyện.

## Chia tập theo thời gian

Ba fold validation lần lượt là tháng 10, 11 và 12/2024. Mỗi fold chỉ huấn luyện bằng thời gian trước tháng validation. A bắt đầu từ 01/01/2024, B bắt đầu từ 01/01/2023, hai phương án dùng cùng khoảng validation. Sau khi chốt mô hình bằng các fold này, fit lại đến trước 01/01/2025 và đánh giá holdout 2025.

Mọi chuẩn hóa có học tham số, chọn đặc trưng hoặc tuning phải fit trên train. Không đưa cờ chất lượng của chính giờ cần dự báo vào feature. Các quy tắc làm sạch hồi cứu sử dụng thời điểm trả; mô phỏng thời gian thực cần quy định độ trễ dữ liệu riêng.

## Schema các năm

Tên airport_fee được chuẩn hóa thành Airport_fee. Mã ID nâng lên int64, string lên large_string; cột passenger_count/RatecodeID đọc chung ở float64 để bảo toàn nguồn tháng 01/2023. Phép cast safe từ chối mất giá trị. Cột cbd_congestion_fee mới của năm 2025 được giữ; file năm cũ không có cột này được biểu diễn null, không điền phí 0. Loader chuẩn hóa 2023 theo schema mở rộng khi đọc mà không sửa file cũ.

## Ranh giới hoàn thành

Giai đoạn 2 cung cấp dữ liệu và hợp đồng chia tập có thể tái lập. Spark, HBase, đặc trưng học máy, huấn luyện và dashboard thuộc các giai đoạn tiếp theo. Không gọi dữ liệu là chính xác tuyệt đối hoặc tuyên bố mô hình đã tốt hơn khi chưa có thực nghiệm.

## Kết quả dữ liệu ngày 07/10/2026

| Năm | Dòng raw | Ngoài tháng nguồn | Vùng không xác định | Thời lượng ≤ 0 | Chuyến giữ lại |
|---|---:|---:|---:|---:|---:|
| 2023 | 38.310.226 | 730 | 387.192 | 12.750 | 37.909.554 |
| 2024 | 41.169.720 | 420 | 146.199 | 12.383 | 41.010.718 |
| 2025 | 48.722.602 | 214 | 103.043 | 545.589 | 48.073.756 |
| Tổng | 128.202.548 | 1.364 | 636.434 | 570.722 | 126.994.028 |

Các nhóm cách ly ở bảng này được tính theo thứ tự xử lý, không chồng lặp. Nhãn mô hình còn loại các ngày DST; vì vậy số chuyến giữ lại không đồng nghĩa tất cả chuyến đều tham gia nhãn huấn luyện.

Lưới có 6.917.952 dòng vùng–giờ, trong đó 6.880.080 dòng đủ điều kiện làm nhãn trước khi tạo lag/rolling. Năm nhuận 2024 có đủ ngày 29/02. Mỗi năm có một giờ thiếu toàn nguồn: 12/03/2023 02:00, 10/03/2024 02:00, 09/03/2025 02:00; tất cả thuộc ngày DST đã mask.

**Vấn đề cần đưa vào báo cáo:** năm 2025 có 543.355 bản ghi thời lượng bằng 0 và 2.234 bản ghi âm trong nhóm đã qua kiểm tra tháng/vùng (tổng 545.589, khoảng 1,12% raw). Con số này cao hơn các năm trước; chưa xác định nguyên nhân từ nguồn. Không tự sửa timestamp hoặc khẳng định đây là chuyến giả. Các dòng được cách ly theo chính sách đã duyệt, còn ảnh hưởng theo vùng/giờ được lưu trong `yellow_2025_v1/YYYY-MM/duration_sensitivity.csv`. Khi diễn giải biến động giữa các năm phải nêu ảnh hưởng của chất lượng nguồn và quy tắc loại dòng.

## Tái lập và kiểm tra

Trên máy mới, tải danh mục vùng trước khi chạy pipeline (nếu file chưa có):

```powershell
New-Item -ItemType Directory -Force data/reference | Out-Null
Invoke-WebRequest -Uri 'https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv' -OutFile data/reference/taxi_zone_lookup.csv
Get-FileHash data/reference/taxi_zone_lookup.csv -Algorithm SHA256
```

Checksum snapshot đã nghiệm thu: `1a99e105092230f8620f301edcca7f80d3080642ff404d28ed957d3fa222c8ed`. Nếu nguồn đã thay đổi, kiểm tra phiên bản và ảnh hưởng trước khi thay manifest hoặc ép kết quả kiểm thử thành công.

Chạy từ thư mục gốc bằng Python trong venv, cài thư viện tại `requirements-profile.txt`. Trên máy chưa có đầu ra, thực hiện lần lượt cho từng năm 2023, 2024, 2025:

```powershell
.\.venv\Scripts\python.exe -m src.ingestion.download_year --year 2023
.\.venv\Scripts\python.exe -m src.processing.process_year --year 2023
.\.venv\Scripts\python.exe -m src.ingestion.audit_year_duplicates --year 2023
.\.venv\Scripts\python.exe -m src.processing.build_hourly_grid --year 2023
```

Thay tham số năm cho hai năm còn lại. Cần có `data/reference/taxi_zone_lookup.csv` đúng checksum; URL nằm trong `data/README.md`. Bước tạo lưới từ chối thư mục đầu ra đã tồn tại để tránh ghi đè. Với dữ liệu đã tạo, chạy nghiệm thu thay vì tạo lại:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m src.processing.verify_stage2
```

Kiểm tra nghiệm thu đối chiếu checksum, bảo toàn dòng, tính duy nhất/đủ lưới vùng–giờ, mask DST, số 0/null, số chuyến tổng hợp, audit trùng và số nhãn các tập. Không huấn luyện hoặc đánh giá mô hình trên holdout trong bước này.
