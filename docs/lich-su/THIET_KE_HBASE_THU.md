> Tài liệu lịch sử: giữ để truy vết quyết định/thử nghiệm; không dùng làm hướng dẫn cài đặt hiện hành. Xem [mục lục](../README.md).

# Thiết kế thử Spark → HBase

Trạng thái: người dùng đã duyệt phương án thử 168 giờ; phép thử tích hợp đã đạt ngày 07/10/2026. Đây chưa phải nghiệm thu toàn bộ giai đoạn 3 hoặc nạp đầy đủ dữ liệu.

## Phạm vi thử

- Bảng riêng `transport_demand_hourly_trial_v1` (thuộc namespace default, tiền tố transport chỉ là tên bảng).
- Đầu vào: lưới đã nghiệm thu `data/processed/hourly_grid_v1/2024/zone_hours.parquet`.
- Vùng 161, từ 01/01/2024 00:00 đến trước 08/01/2024 00:00: 168 dòng, đã kiểm tra bằng loader.
- Spark đọc Parquet, lọc mẫu, ghi theo partition qua HappyBase. Không collect dữ liệu toàn năm vào driver. Chỉ mẫu 168 dòng dùng để đối chiếu đầy đủ sau ghi.
- Chưa phải schema chính thức của dashboard, không ghi vào bảng `users` hoặc bảng smoke trước đó.

## Khóa dòng

UTF-8/ASCII `ZZZ#YYYYMMDDHH`, ví dụ `161#2024010100`. Mã vùng đệm đủ 3 chữ số giúp thứ tự từ điển ổn định. Khoảng truy vấn đầu bao gồm, cuối không bao gồm: `[161#2024010100, 161#2024010800)`.

Giờ vẫn là nhãn địa phương New York của dataset, không chuyển thành UTC. Ngày DST đã được mask ở giai đoạn 2; schema phải giữ các cờ này. Cấu trúc vùng-trước phù hợp truy vấn lịch sử một vùng; chưa tối ưu cho truy vấn tất cả vùng cùng một giờ hoặc cụm có nhiều region.

## Cột và encoding đề xuất

| Cột HBase | Nguồn / ý nghĩa |
|---|---|
| `d:recorded_trip_count` | Số chuyến được giữ; thiếu toàn nguồn thì không có cell |
| `d:target_trip_count` | Nhãn dự báo; thiếu hoặc ngày DST thì không có cell |
| `q:source_hour_missing` | Cờ thiếu toàn nguồn |
| `q:dst_day` | Cờ cả ngày DST |
| `q:zero_recorded` | Có nguồn nhưng không có chuyến được giữ ở vùng này |
| `q:model_eligible` | Đủ điều kiện làm nhãn |
| `m:dataset_version` | `hourly_grid_v1` |
| `m:timezone` | `America/New_York` (wall-clock labels) |

Số nguyên lưu dưới dạng chuỗi thập phân UTF-8, boolean là `1`/`0`. Ba column family d/q/m có max_versions=1 trong bảng thử. Không lưu chuỗi `None`, không thay null bằng 0. Nếu một cell chuyển từ có giá trị sang null khi ghi lại, phải xóa cell cũ trong cùng mutation của dòng; nếu không sẽ còn giá trị lỗi thời.

## Kiểm chứng dự kiến

1. Unit test codec: khóa, số 0, null, DST và mutation ghi lại; mẫu tháng 1 tự nó không chứng minh xử lý null/DST đúng.
2. Thử kết nối từ container tới HBase qua endpoint phù hợp Docker Desktop.
3. Chỉ sau khi được duyệt mới tạo bảng thử, xác minh schema nếu bảng đã tồn tại.
4. Ghi 168 dòng, đọc lại từng khóa/cell và scan đúng khoảng; so với nguồn.
5. Ghi lại cùng dữ liệu, kiểm tra vẫn 168 dòng với cùng giá trị.
6. Lưu checksum đầu vào, cấu hình, số dòng và kết quả đối soát. Dừng nếu có khác biệt.

Việc nạp toàn bộ 6,9 triệu dòng vùng–giờ, schema chính thức, điều chỉnh dung lượng hoặc đổi phiên bản HBase là quyết định riêng sau kết quả thử.

## Kết quả đã kiểm chứng

- Spark 3.5.7 local[2] đọc lưới Parquet, lọc đúng 168 giờ rồi ghi từ hai partition qua `host.docker.internal:9090` vào bảng thử đã duyệt.
- Ghi hai lượt; mỗi lượt point get 168 khóa và scan 168 dòng đều khớp từng cell, không có khóa ngoài mẫu. Bảng vẫn có đúng 168 dòng.
- Python Windows đọc qua `127.0.0.1:9090`, giải mã độc lập và đối chiếu tất cả cột với PyArrow: 0 sai khác, 26.365 chuyến.
- 19/19 unit tests đạt, gồm 4 kiểm thử codec cho zero/null/DST và dữ liệu không nhất quán. Mẫu tháng 1 không có DST: đây là kiểm chứng codec, chưa phải nghiệm thu ghi null/DST thực tế trên HBase.
- Bằng chứng: `artifacts/metrics/spark_hbase_trial.json`, `artifacts/metrics/hbase_windows_readback.json`. Bảng users và bảng synthetic smoke được giữ nguyên.

## Lệnh sử dụng từ thư mục gốc

HBase phải chạy và expose Thrift 9090. Trên Docker Desktop, container Spark dùng `host.docker.internal` để kết nối cổng host; `localhost` bên trong container không phải máy Windows.

Chỉ đọc và kiểm tra kết quả hiện tại trên Windows:

```powershell
.\.venv\Scripts\python.exe -m src.storage.inspect_hbase_trial
```

Chạy lại thử tích hợp (ghi lại đúng phạm vi bảng thử, không nạp năm đầy đủ):

```text
docker compose -f docker/spark/compose.yaml run --rm spark /workspace/src/storage/spark_hbase_trial.py
```

Lệnh nạp từ chối schema bảng khác hoặc khóa/metadata ngoài phạm vi thử. Lần chạy lại cập nhật file metrics của phép thử hiện tại. Cấu hình cổng hiện có phục vụ máy cá nhân; bản HBase tái lập trên máy khác cần được kiểm tra riêng trước khi tuyên bố hoàn thành giai đoạn.
