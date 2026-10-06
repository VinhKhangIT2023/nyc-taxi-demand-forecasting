# Khảo sát dữ liệu Yellow Taxi tháng 01 năm 2024

## Kết quả thực tế

Đã đọc toàn bộ **2.964.624 dòng, 19 cột**, 3 row group; file gốc 49.961.641 byte. SHA256 trước/sau giống nhau. Môi trường: Python 3.11.17, PyArrow 19.0.1. Đọc theo lô 32.768 dòng, không lấy mẫu để suy ra các số liệu dưới đây.

| Quan sát | Số dòng / giá trị | Diễn giải |
|---|---:|---|
| Thiếu thời điểm đón hoặc trả | 0 ở mỗi cột | Không cần điền thiếu timestamp trong file này |
| Thiếu mã vùng đón hoặc trả | 0 ở mỗi cột | Không đồng nghĩa mọi mã vùng đều hợp lệ |
| Thiếu passenger_count | 140.162 (khoảng 4,73%) | Cần phân biệt đếm chuyến với đếm hành khách |
| Thiếu RatecodeID, store_and_fwd_flag, congestion_surcharge, Airport_fee | Mỗi cột 140.162 | Chưa kiểm tra chúng có thiếu trên cùng các dòng không |
| Thời điểm đón ngoài tháng 01/2024 | 18 | 15 trước tháng, 3 từ 01/02 trở đi |
| Trả khách trước lúc đón | 56 | Cần kiểm tra mẫu trước khi quyết định xử lý |
| Trả khách đúng lúc đón | 814 | Không tự động kết luận chuyến không tồn tại |
| Quãng đường bằng 0 | 60.371 | Cần xem cùng thời gian và các trường khác |
| Số hành khách bằng 0 | 31.465 | Là số 0 được ghi nhận, khác với null |
| Tổng tiền âm | 35.504 | Chưa xác định nguyên nhân; không sửa thành trị tuyệt đối |
| Trùng toàn bộ giá trị 19 cột | 0 bản sao dư | Không loại trừ việc cùng chuyến bị ghi khác giá trị |
| Quãng đường lớn nhất | 312.722,3 mile | Bất thường cần khảo sát; chưa đặt ngưỡng loại |

Thời điểm đón trải từ `2002-12-31 22:59:39` đến `2024-02-01 00:01:15`. Đây là timestamp thực sự có trong file mang tên 01/2024, không phải bằng chứng nguồn có dữ liệu lịch sử đầy đủ từ năm 2002. Có 2.964.606 bản ghi có thời điểm đón trong tháng 01/2024; cả 31 ngày đều có bản ghi, nhưng điều đó chưa chứng minh độ đầy đủ từng khu vực/giờ.

Đã kiểm thử chương trình bằng dữ liệu nhỏ biết trước, gồm bản trùng nằm ở hai lô khác nhau, timestamp null, trả trước đón và mốc cuối tháng loại trừ. Kiểm tra dependency bằng `pip check` thành công.

## Quy tắc đầu tiên đã được duyệt và chạy

Đề xuất đầu tiên: khi xây tập nhu cầu tháng 01/2024, chỉ lấy thời điểm đón trong `[2024-01-01, 2024-02-01)`, chuyển 18 dòng ngoài khoảng sang dữ liệu cách ly có lý do, không xóa file gốc. Không ràng buộc thời điểm trả phải nằm trong tháng: chuyến đón cuối tháng có thể trả đầu tháng sau.

Lý do: đơn vị nhu cầu được định nghĩa theo thời điểm đón; trộn timestamp ngoài tháng sẽ làm sai phạm vi đang thử nghiệm. Đây chưa phải quy tắc tự động cho nhiều tháng; khi mở rộng cần kiểm tra bản ghi giáp tháng giữa các file để tránh bỏ sót hoặc đếm hai lần.

Đã được người dùng duyệt và thực hiện bằng `src/processing/split_pickup_month.py`. Kết quả tại `data/interim/pickup_month_2024-01/`:

- `in_month.parquet`: 2.964.606 dòng, giữ nguyên 19 cột và các giá trị.
- `outside_month.parquet`: 18 dòng, thêm cột `quarantine_reason` để giải thích vì sao cách ly.
- `audit.json`: số dòng, khoảng thời gian, phiên bản PyArrow và SHA256 đầu vào/đầu ra.

Đây là đầu ra trung gian chưa xử lý các vấn đề chất lượng khác. Có 3 kiểm thử thành công, bao gồm ranh giới tháng, giữ chuyến đón cuối tháng/trả tháng sau, giữ giá trị thiếu/âm và phát hiện trùng giữa lô trong bước khảo sát. File gốc không thay đổi.

Chạy từ thư mục gốc bằng `.\.venv\Scripts\python.exe src/processing/split_pickup_month.py`. Chương trình từ chối ghi đè thư mục đầu ra đã tồn tại; muốn chạy thử lại dùng `--output-dir data/interim/pickup_month_2024-01_rerun`. Không tự xóa đầu ra cũ.

Chưa quyết định loại các dòng thiếu passenger_count, tiền âm, quãng đường 0 hoặc thời lượng bất thường. Bước khảo sát tiếp theo đề xuất đối chiếu danh mục vùng và xem các nhóm bất thường trước khi chốt thêm quy tắc.

## Cách chạy lại

Từ thư mục gốc, sử dụng Python của dự án:

```powershell
.\.venv\Scripts\python.exe -m pip install --no-cache-dir -r requirements-profile.txt
.\.venv\Scripts\python.exe src/ingestion/profile_yellow.py
```

Kết quả chi tiết lưu tại `artifacts/metrics/profile_2024-01.json`. Chương trình chỉ đọc dữ liệu gốc, kiểm tra SHA256 trước/sau và không tạo dữ liệu sạch. Bản ghi trùng được so sánh trên toàn bộ cột, kể cả giữa các lô; cơ sở dữ liệu SQLite tạm trên đĩa được đóng và xóa sau khi chạy xong. Cần ổ đĩa trống cho dữ liệu tạm lớn hơn file Parquet nén.

## Ý nghĩa các cột

| Cột | Ý nghĩa và vai trò trong bài toán |
|---|---|
| VendorID | Mã đơn vị cung cấp bản ghi; phục vụ khảo sát nguồn |
| tpep_pickup_datetime | Thời điểm bắt đầu tính cước; dùng đại diện thời điểm đón |
| tpep_dropoff_datetime | Thời điểm kết thúc tính cước; kiểm tra thứ tự thời gian |
| passenger_count | Số hành khách; không phải số chuyến |
| trip_distance | Quãng đường do đồng hồ ghi nhận, đơn vị mile |
| RatecodeID | Mã biểu giá cuối chuyến |
| store_and_fwd_flag | Cờ lưu trên xe rồi mới truyền khi kết nối lại |
| PULocationID | Mã vùng đón; biến chính để tổng hợp nhu cầu |
| DOLocationID | Mã vùng trả; chưa dùng để định nghĩa nhu cầu đón |
| payment_type | Mã loại thanh toán |
| fare_amount | Tiền cước theo thời gian và quãng đường |
| extra | Các khoản phụ thu khác |
| mta_tax | Thuế MTA |
| tip_amount | Tiền tip ghi nhận; không bao gồm tip tiền mặt |
| tolls_amount | Phí cầu đường |
| improvement_surcharge | Phụ thu cải thiện dịch vụ |
| total_amount | Tổng tiền ghi nhận; không bao gồm tip tiền mặt |
| congestion_surcharge | Phụ thu ùn tắc |
| Airport_fee | Phụ thu đón tại sân bay |

Nguồn giải nghĩa: [TLC Yellow Taxi Data Dictionary](https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_yellow.pdf), bản đang công bố ngày 18/03/2025. Bảng trên mô tả 19 cột thực sự có trong file 01/2024; không thêm cột phí mới chỉ có từ năm 2025. Mã hạng mục cụ thể cần kiểm tra theo năm trước khi diễn giải.

## Cách đọc kết quả

- `nulls` là giá trị thiếu thật; số 0 không tự động được xem là thiếu.
- Khoảng khảo sát theo thời điểm đón: từ 01/01/2024, gồm đầu mốc, đến 01/02/2024, không gồm cuối mốc. Chưa chuyển múi giờ.
- `full_row_duplicate_excess` đếm số bản sao dư sau bản đầu tiên của các hàng giống nhau toàn bộ giá trị; không chứng minh chắc chắn đó là cùng chuyến thực tế.
- Các cờ bất thường có thể chồng lấp; không cộng chúng thành tổng số dòng cần xóa.
- Mã vùng mới chỉ được thống kê, chưa đối chiếu danh mục vùng chính thức.
- Chưa quyết định ngưỡng ngoại lệ, điền thiếu hoặc loại bản ghi. Mọi quy tắc cần người dùng duyệt trước khi triển khai.
