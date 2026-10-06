# Dữ liệu Yellow Taxi năm 2023

## Phạm vi và nguồn

Người dùng duyệt bổ sung đủ năm 2023 để chuẩn bị so sánh việc học thêm lịch sử với phương án chỉ học từ 2024. Đã tải 12 file Yellow Taxi từ các liên kết thực tế trên [trang TLC](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page). Manifest tải lưu URL, thời điểm kiểm tra, checksum, dung lượng, số dòng và schema ở `artifacts/metrics/download_manifest_2023.json`.

File nguồn có tổng cộng 38.310.226 dòng, 635.743.618 byte. Bản tải được nhận diện bằng SHA256; không tuyên bố đã đối chiếu với checksum do TLC phát hành. Dữ liệu nguồn giữ tại `data/raw/` và không push lên GitHub.

## Kết quả đã hoàn thành

| Nhóm | Số dòng |
|---|---:|
| Raw đủ 12 tháng | 38.310.226 |
| Ngoài tháng theo thời điểm đón | 730 |
| Vùng đón 264/265 | 387.192 |
| Thời lượng không dương | 12.750 |
| Dữ liệu chính sau xử lý | **37.909.554** |

Đối soát: 730 + 387.192 + 12.750 + 37.909.554 = 38.310.226. Mỗi tháng có audit riêng và tổng hợp ở `artifacts/metrics/processed_2023.json`. Manifest năm ghi complete=true. 12 file đầu ra dùng chung schema đã sẵn sàng đọc.

Bảng tổng hợp có 869.552 nhóm vùng × giờ quan sát; tổng số chuyến khớp dữ liệu chính. Có 261 mã vùng có chuyến trong năm. Ghép với tập tháng 01/2024 v1 hiện có được **40.861.425 dòng**; loader đã được chạy thử thành công.

Kiểm tra thời gian ghi nhận 8.759 nhãn giờ địa phương trong năm; không có nhãn 12/03/2023 lúc 02:00. Khoảng đó liên quan chuyển giờ mùa hè, không tự điền thành một giờ có 0 chuyến. Tại lần lùi đồng hồ tháng 11, timestamp thiếu offset không phân biệt được hai lần xuất hiện cùng giờ. Bảng hiện dùng nhãn giờ địa phương, chưa được quảng bá là chuỗi UTC liên tục sẵn sàng huấn luyện.

Đối chiếu quy tắc giờ mùa hè của [NIST](https://www.nist.gov/pml/time-and-frequency-division/popular-links/daylight-saving-time-dst): đây là khoảng nhảy đồng hồ từ 02:00 lên 03:00 vào Chủ nhật thứ hai tháng 3. Timestamp wall-clock cũng có thể làm thời lượng chuyến qua lần lùi đồng hồ bị nhập nhằng; nhóm cách ly thời lượng không dương không đồng nghĩa mọi chuyến đó đều không tồn tại.

Kiểm tra trùng hoàn tất cả 12 tháng trên toàn bộ 19 cột nguồn: **2 nhóm giống hệt, mỗi nhóm 2 dòng**, tương ứng 2 bản sao dư, đều thuộc ngày 13/11/2023. Chưa xóa vì không có định danh chuyến duy nhất; ghi đầy đủ giá trị để truy vết ở `artifacts/metrics/duplicate_audit_2023.json`. Nếu thử bỏ một bản sao mỗi nhóm, tác động tối đa là giảm 2 chuyến trên toàn năm; hiện giữ nhất quán chính sách không tự deduplicate. Các tháng khác không có bản sao dư giống toàn bộ cột.

Không phát hiện NaN hoặc vô cực trong các cột số trên tập đầu ra (null được thống kê riêng, không coi là NaN). Các cờ chất lượng và null vẫn được bảo toàn. Đã chạy 11 kiểm thử thành công; kiểm tra tổng số chuyến theo giờ khớp số dòng, checksum đầu vào và schema chung. Kết quả kiểm tra độ phủ tại `artifacts/metrics/coverage_2023.json`.

## Quy tắc xử lý

Áp dụng cùng chính sách v1 đã duyệt cho tháng 01/2024, theo thứ tự:

1. Tách theo thời điểm đón thuộc tháng của file nguồn. Giữ các dòng ngoài tháng để xem lại, không tự sửa ngày hoặc chuyển sang tháng khác.
2. Tách PULocationID 264/265. Mã 1 Newark Airport vẫn được giữ.
3. Tách thời lượng không dương, giữ lý do âm hoặc bằng 0.
4. Giữ các vấn đề khác, thêm cờ chất lượng. Không biến tiền âm thành dương, không điền số hành khách, không tự đặt ngưỡng quãng đường tối đa.
5. Chuẩn hóa schema đầu ra để đọc nhiều tháng cùng nhau.

Nếu timestamp cần thiết bị thiếu hoặc mã vùng không tồn tại trong lookup, pipeline dừng thay vì tự thêm quy tắc. Quarantine của từng bước được giữ riêng; đây là các nhóm tuần tự không chồng lấp.

## Schema dùng chung

Tháng 01/2023 dùng `airport_fee`, các tháng sau dùng `Airport_fee`. Đầu ra thống nhất `Airport_fee`. Các mã ID được nâng lên int64; passenger_count và RatecodeID dùng float64 để giữ cả kiểu double của nguồn tháng 1 và giá trị thiếu; string nâng thành large_string. Không làm tròn, không điền null. Phép cast ở chế độ safe để từ chối giá trị không thể biểu diễn chính xác. Timestamp giữ đơn vị microsecond như nguồn.

Schema cuối có 19 cột nguồn, duration_minutes và 7 cờ chất lượng. Raw và bản đầu ra trước chuẩn hóa được giữ để truy vết.

## Cách dùng

Sau khi `dataset_manifest.json` ghi `complete: true`, thư mục chỉ chứa các file chuyến đã chuẩn hóa là:

`data/processed/yellow_2023_v1/trips/part-2023-01.parquet` đến `part-2023-12.parquet`.

Không đọc đệ quy toàn bộ `data/processed/` hoặc `data/interim/`: sẽ trộn bản lặp giữa các bước và file cách ly. Chỉ chọn `part-*.parquet` trong thư mục `trips` hoặc dùng loader có sẵn.

```powershell
.\.venv\Scripts\python.exe -m src.ingestion.load_clean_trips --year 2023
.\.venv\Scripts\python.exe -m src.ingestion.load_clean_trips --year 2023 --include-january-2024
```

Trong Python, xử lý từng lô để không nạp toàn bộ năm vào RAM:

```python
from src.ingestion.load_clean_trips import iter_clean_batches

for table in iter_clean_batches(2023, include_january_2024=True):
    # table là pyarrow.Table, schema đã thống nhất
    pass
```

`hourly_observed.csv` ở thư mục năm là số chuyến theo vùng × giờ có quan sát. Không có suy diễn rằng giờ vắng bản ghi chắc chắn bằng 0. Mô hình cần bước dựng lưới thời gian và đặc trưng riêng.

## Chạy lại và phục hồi

```powershell
.\.venv\Scripts\python.exe -m src.ingestion.download_year --year 2023
.\.venv\Scripts\python.exe -m src.processing.process_year --year 2023
.\.venv\Scripts\python.exe -m src.ingestion.audit_year_duplicates --year 2023
```

Lệnh xử lý chỉ dùng lại bước đã có audit và checksum khớp; nếu file thay đổi hoặc bước dở dang, dừng để kiểm tra. Kiểm tra trùng chạy theo tháng và có thể dùng nhiều RAM hơn pipeline theo lô. Các dòng có cùng giá trị không tự động bị xóa vì nguồn không có khóa chuyến duy nhất. Kết quả kiểm tra trùng được báo riêng.

## Giới hạn cần nhớ

- Danh mục vùng là bản TLC cung cấp khi tải, chưa xác nhận là snapshot lịch sử năm 2023.
- Dòng ngoài tháng nguồn được giữ trong quarantine; chưa tự phân bổ lại qua các file giáp tháng. Điều này có thể bỏ sót một số lượt đón trong tập chính và phải báo trong nghiên cứu.
- Timestamp nguồn không có offset. Giờ lặp khi đổi giờ mùa hè có thể bị gộp trong bảng wall-clock; không tự khôi phục UTC khi không có đủ thông tin. Cần chính sách DST trước mô hình chuỗi giờ liên tục.
- Lọc theo thời điểm trả là làm sạch hồi cứu, không phải mô phỏng hệ thống thời gian thực đã nhận đủ dữ liệu ngay khi giờ đón kết thúc.
- Dữ liệu phục vụ phân tích lượt đón đã ghi nhận, không đo được nhu cầu chưa phục vụ.
- Hiện chỉ có 2023 và tháng 01/2024. Chưa có đủ 2024 để chạy phép so sánh đã bàn; 2025 vẫn dành cho đánh giá tương lai. Chưa huấn luyện hoặc khẳng định mô hình tốt hơn.
