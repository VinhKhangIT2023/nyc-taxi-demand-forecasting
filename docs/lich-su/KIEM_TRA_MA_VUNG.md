> Tài liệu lịch sử: giữ để truy vết quyết định/thử nghiệm; không dùng làm hướng dẫn cài đặt hiện hành. Xem [mục lục](../README.md).

# Kiểm tra mã vùng đón khách tháng 01 năm 2024

Đã đối chiếu toàn bộ 2.964.606 bản ghi sau bước giới hạn thời điểm đón. Bước kiểm tra chỉ đọc dữ liệu. Sau đó, người dùng đã duyệt bước tách mã 264/265; kết quả triển khai ghi ở cuối tài liệu.

Nguồn tham chiếu: Taxi Zone Lookup CSV liên kết từ [NYC TLC](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page), tải ngày 05/10/2026, có 265 mã không trùng. Đây là bản danh mục hiện được cung cấp, chưa xác minh là snapshot lịch sử tháng 01/2024.

| Nhóm | Số chuyến | Ý nghĩa |
|---|---:|---|
| Có tên khu vực cụ thể trong danh mục | 2.952.588 | Có thể xác định vùng theo danh mục; chưa khẳng định chuyến hợp lệ theo mọi tiêu chí |
| Mã 264: Borough Unknown, Zone N/A | 10.360 | Không xác định được khu vực cụ thể |
| Mã 265: Zone Outside of NYC | 1.658 | Nhãn ngoài NYC, không xác định được một vùng cụ thể |
| Mã null | 0 | Không có giá trị thiếu ở PULocationID |
| Mã không nằm trong danh mục | 0 | Tất cả mã đều tra được |

Có 260 mã vùng đón xuất hiện. Hai nhóm 264/265 cộng lại 12.018 chuyến, khoảng 0,4054% của tập trong tháng. Không tự suy ra khu vực từ vùng trả vì vùng trả có thể khác vùng đón.

Mã 1 có tên Newark Airport, Borough EWR, với 295 chuyến. Đây là khu vực có tên cụ thể và không được nhập chung với mã 265. Việc chỉ nghiên cứu các vùng trong NYC hay giữ các vùng có tên trong danh mục là quyết định phạm vi riêng; chưa tự loại mã 1.

## Phương án đã được duyệt

Tách 12.018 chuyến mã 264/265 ra nhóm chưa đủ thông tin vị trí cho bài toán dự báo theo từng vùng; giữ riêng hai lý do và vẫn đưa vào báo cáo tổng số chuyến. Tập ứng viên theo vùng còn 2.952.588 dòng, chưa phải tập sạch cuối cùng.

Lý do: gộp các vị trí không xác định thành một vùng giả sẽ làm sai ý nghĩa nhu cầu theo khu vực; tự điền mã vùng có thể tạo dữ liệu không có căn cứ. Có thể giữ nhóm Unknown trên dashboard để minh bạch chất lượng nguồn, nhưng chưa đưa nhóm đó vào mô hình cho một vùng cụ thể.

Giữ mã 264/265 thành hai nhóm riêng trong phân tích tổng quan, với nhãn rõ không phải khu vực cụ thể. Sau khi người dùng đồng ý, đã tạo đầu ra riêng cho tập ứng viên và các chuyến chưa rõ vùng; không sửa file đầu vào.

## Chạy lại và kiểm chứng

```powershell
.\.venv\Scripts\python.exe src/ingestion/check_pickup_zones.py
```

Code: `src/ingestion/check_pickup_zones.py`. Kết quả máy đọc: `artifacts/metrics/pickup_zones_2024-01.json`, gồm tần suất và tên vùng của từng mã đã xuất hiện, SHA256 hai đầu vào và hạn chế diễn giải.

Đã đối chiếu tổng các nhóm với số dòng Parquet và SHA256 trước/sau để xác nhận đầu vào không đổi. Cả 4 kiểm thử hiện tại thành công, gồm phân biệt mã không tồn tại với mã có trong bảng nhưng không rõ vị trí. Chỉ kiểm tra PULocationID; chưa kiểm tra DOLocationID hoặc các vấn đề tiền cước/thời lượng.

## Kết quả tách đã thực hiện

| File trong data/interim/pickup_zones_2024-01 | Số dòng | Nội dung |
|---|---:|---|
| zone_candidates.parquet | 2.952.588 | Tập ứng viên theo vùng; giữ nguyên 19 cột |
| unspecified_zones.parquet | 12.018 | Toàn bộ giá trị gốc và cột quarantine_reason |
| audit.json | — | Quy tắc, số dòng, phiên bản thư viện, SHA256 đầu vào/đầu ra |

Hai lý do cách ly là `unknown_pickup_zone_264` (10.360 dòng) và `outside_nyc_unspecified_265` (1.658 dòng). Mã 1 Newark Airport được giữ. Tập ứng viên chưa phải dữ liệu sạch cuối cùng.

Đối soát từ đầu: **2.964.624 = 18 ngoài tháng + 12.018 chưa rõ vùng + 2.952.588 ứng viên**. Cả ba nhóm đều được lưu, không xóa dữ liệu raw.

Chạy từ thư mục gốc:

```powershell
.\.venv\Scripts\python.exe -m src.processing.split_pickup_zones
```

Lệnh từ chối ghi đè thư mục đầu ra đã tồn tại. Muốn chạy lại, thêm `--output-dir data/interim/pickup_zones_2024-01_rerun`. Chương trình dừng trước khi tạo đầu ra nếu gặp mã null hoặc mã ngoài danh mục vì chưa có quy tắc được duyệt cho các trường hợp đó.

Sau khi bổ sung bước tách, cả 5 kiểm thử thành công. Kiểm thử mới xác nhận giữ nguyên các giá trị null/âm ở trường khác, giữ mã 1, tách đúng 264/265 và không ghi đè kết quả có sẵn. SHA256 đầu vào/lookup không đổi.
