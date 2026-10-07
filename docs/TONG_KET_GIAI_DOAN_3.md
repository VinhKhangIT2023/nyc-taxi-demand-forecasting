# Tổng kết giai đoạn 3 — Tích hợp và tái lập Spark/HBase

Ngày hoàn thành: 07/10/2026. Trạng thái: **hoàn thành phạm vi hạ tầng local và tích hợp thử đã duyệt**. Nghiệm thu máy đọc được tại [stage3_acceptance.json](../artifacts/metrics/stage3_acceptance.json), `complete=true`.

## 1. Mục tiêu và phạm vi

Có môi trường Spark xử lý dữ liệu thật, Python/Spark ghi và đọc HBase, cấu hình tái lập trong repo và bằng chứng dữ liệu còn sau restart/khôi phục. Phạm vi thử: Spark làm sạch tháng 01/2024; HBase nạp 168 giờ vùng 161, chưa nạp toàn bộ 6,9 triệu dòng vùng–giờ.

## 2. Công việc đã thực hiện

- Kiểm tra container HBase có sẵn, phiên bản, Thrift, bảng và đường dẫn lưu trữ.
- Xử lý vướng mắc Smart App Control bằng Python 3.13.16 chính thức có chữ ký; tạo lại venv sau kiểm thử, giữ chính sách bảo vệ và Python 3.14. Ghi phiên bản thư viện để tái lập.
- Viết phép thử HBase bảng riêng: put/get/scan, ghi lặp và đọc lại sau restart.
- Xây image Spark 3.5.7, Python 3.11.17, Java 17.0.20.1; local[2], driver 2 GiB, container 2 CPU/4 GiB. Tách khỏi môi trường Windows.
- Viết Spark ETL thử từ raw tháng 01/2024, đối soát từng nhóm vùng–giờ và cờ chất lượng với giai đoạn 2.
- Thiết kế codec HBase đã duyệt; ghi mẫu thật qua Spark foreachPartition, đọc lại độc lập từ Windows.
- Bổ sung Compose HBase với named volume, hostname ổn định, dữ liệu ZooKeeper trong /data, healthcheck và dừng sạch.
- Dựng HBase từ cấu hình trên volume mới, lặp lại tích hợp, kiểm tra zero/null/DST thực tế.
- Sao lưu offline volume thử và khôi phục vào container/volume khác; đối soát nội dung và schema mà không nạp lại bằng ứng dụng.

## 3. Kết quả đạt được

| Phép kiểm tra | Kết quả |
|---|---|
| Spark xử lý raw tháng 01/2024 | 2.964.624 dòng raw → 2.951.871 chuyến giữ lại |
| Đối soát tổng hợp | 76.190 nhóm vùng–giờ, 0 khác biệt; 7 cờ chất lượng khớp |
| Python worker trong Spark | Đạt |
| Spark → HBase | 168 giờ vùng 161, tổng 26.365 chuyến |
| Ghi mẫu hai lần | Vẫn 168 dòng; mỗi lượt đọc/scan khớp từng cell |
| Windows đọc lại | Khớp toàn bộ cột Parquet nguồn |
| Edge cases thực tế HBase | 0, 0→null, null→0 và DST đều đạt |
| Backup/restore | Nguồn dừng sạch exit code 0; volume/container mới giữ đúng 168 dòng thật + 2 dòng giả lập |
| Unit suite cuối giai đoạn | 19/19 đạt |

Spark trial mất 22,76 giây cho job trên máy hiện tại, không gồm build image; chưa phải benchmark hoặc kết luận khả năng mở rộng.

## 4. Đầu ra và bằng chứng

| Thành phần | Đường dẫn |
|---|---|
| Docker Spark và cách chạy | [docker/spark/README.md](../docker/spark/README.md) |
| Docker HBase và hướng dẫn cho Hiếu | [docker/hbase/README.md](../docker/hbase/README.md) |
| Thiết kế row key/cột đã duyệt | [THIET_KE_HBASE_THU.md](THIET_KE_HBASE_THU.md) |
| Job Spark ETL | [spark_trial.py](../src/processing/spark_trial.py) |
| Job Spark → HBase | [spark_hbase_trial.py](../src/storage/spark_hbase_trial.py) |
| Script backup/restore có kiểm tra | [test_hbase_recovery.ps1](../scripts/test_hbase_recovery.ps1) |
| Nghiệm thu tổng hợp và checksum bằng chứng | [stage3_acceptance.json](../artifacts/metrics/stage3_acceptance.json) |
| Bằng chứng khôi phục | [hbase_recovery.json](../artifacts/metrics/hbase_recovery.json) |
| Hướng dẫn môi trường Windows | [CAI_DAT.md](CAI_DAT.md) |

Archive `.tools/hbase-backups/stage3.tar` và Parquet giữ trên máy, không push GitHub. Image/volume nằm trong Docker; Git lưu cấu hình, code, tests, tài liệu và metrics nhỏ.

## 5. Quyết định và lý do

Giữ HBase 2.1.2 để tương thích môi trường đã có, cố định image digest; không đổi phiên bản trong lúc xác minh phục hồi. Spark chạy theo job để không giữ tài nguyên khi không cần. Cấu hình HBase mới dùng cổng riêng để giữ nguyên container cũ. Named volume chứa cả HBase và ZooKeeper để không phụ thuộc filesystem tạm của container. Mẫu nhỏ có thể đối chiếu toàn bộ trước khi mở rộng. Chi tiết phê duyệt Python, Spark và mẫu 168 giờ ở [QUYET_DINH.md](QUYET_DINH.md).

## 6. Vấn đề đã xử lý và giới hạn

- Python standalone bị Smart App Control chặn: thay bằng bản chính thức có chữ ký theo phê duyệt, không tắt bảo vệ.
- HappyBase 1.2.0 cần pkg_resources: khóa setuptools 80.9.0; còn cảnh báo deprecated, không có lỗi trong phép thử.
- Healthcheck ban đầu tìm chuỗi không khớp chế độ status simple: đã sửa sang status, container managed đạt healthy.
- HBase standalone local filesystem/Java 8 là môi trường học tập cũ, không dùng làm hệ production hoặc expose Internet. Không chứng minh crash consistency khi mất điện, chống mất máy hay cụm phân tán.
- Tái lập và restore đã chạy trên container/volume mới ở máy hiện tại; chưa xác minh trên phần cứng của Hiếu.
- Không backup bảng users của container cũ; archive phục hồi chỉ chứa môi trường thử riêng. Dataset giai đoạn 2 nằm ở Parquet, không nằm trong bản backup HBase này.
- Chưa xử lý đủ 36 tháng bằng Spark, chưa nạp toàn bộ dataset vào HBase, chưa huấn luyện hoặc làm dashboard. Những việc đó không thuộc phép thử hạ tầng đã duyệt.

## 7. Trạng thái vận hành và bàn giao

| Instance | Trạng thái lúc nghiệm thu | Cổng Thrift / UI |
|---|---|---|
| hbase-demo cũ | Giữ nguyên, đang chạy | 9090 / 16010 |
| bigdata-hbase-hbase-1 | Đang chạy, healthy; môi trường tái lập cho bước sau | 19090 / 16011 |
| bigdata-hbase-restore-hbase-1 | Đã dừng sau kiểm chứng để tiết kiệm RAM; giữ volume | 19091 / 16012 khi bật |
| Spark job | Hoàn thành; container tạm đã xóa, image và output còn | Không publish UI |

Đọc dữ liệu thật từ môi trường tái lập:

```powershell
.\.venv\Scripts\python.exe -m src.storage.inspect_hbase_trial --port 19090 --report artifacts/metrics/hbase_managed_readback.json
```

Bước tiếp theo: chốt đặc trưng, baseline và quy trình huấn luyện/đánh giá trên cấu hình chia tập đã chuẩn bị. Phải quyết định riêng phạm vi nạp HBase chính thức và tránh dùng holdout 2025 để chọn mô hình. Báo cáo Word, slide và demo cuối kỳ vẫn cần hoàn thiện ở các giai đoạn sau.
