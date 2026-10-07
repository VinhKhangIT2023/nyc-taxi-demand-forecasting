# Spark thử nghiệm tháng 01/2024

Môi trường đã được người dùng duyệt: PySpark 3.5.7, Python 3.11, Java 17; local[2], driver heap 2 GiB, container tối đa 2 CPU và 4 GiB RAM (không thêm swap). Đây là xử lý trên một máy, không phải cụm nhiều máy. Python Windows 3.13 và venv Windows không được đưa vào image.

Đã build và chạy thành công ngày 07/10/2026: Python 3.11.17, Java 17.0.20.1, Spark 3.5.7; xử lý 2.964.624 dòng raw và giữ 2.951.871 chuyến. Cả 76.190 nhóm vùng–giờ khớp đối chứng, bảy cờ chất lượng khớp. Thời gian job ghi nhận 22,76 giây (không gồm build image; không phải benchmark tổng quát). Giới hạn cgroup thực tế: memory.max=4294967296, cpu.max=200000 100000. Phép thử Python worker đạt.

## Build và chạy từ thư mục gốc dự án

Docker Desktop phải chạy Linux containers. Cần dữ liệu giai đoạn 2 tháng 01/2024, lookup vùng và các manifest đã nghiệm thu. Không cần kích hoạt venv Windows để chạy Docker.

```text
docker compose -f docker/spark/compose.yaml build
docker compose -f docker/spark/compose.yaml run --rm spark
```

Build lần đầu tải Java/PySpark nên tốn thời gian và dung lượng mạng. `.dockerignore` chỉ cho phép gửi Dockerfile và requirements vào build context, không gửi dataset, môi trường Python hoặc tài liệu riêng. Base image Python khóa digest. Java 17 lấy bản vá tại thời điểm build từ Debian; vì vậy rebuild tương lai không mặc định tạo cùng image byte-for-byte. File metrics sẽ ghi phiên bản Java thực tế và image ID tại lần chạy kiểm thử.

Compose gắn code và `data/` ở chế độ chỉ đọc; chỉ gắn thư mục kết quả riêng `/output` và thư mục metrics ở chế độ ghi. Không publish cổng Spark UI. Job tự kết thúc, `--rm` chỉ xóa container job, không xóa file đầu ra trên máy hoặc container HBase.

## Phép đối soát

Job `src/processing/spark_trial.py`:

1. Kiểm tra checksum raw, lookup và CSV đối chứng từ giai đoạn 2.
2. Thử một tác vụ Python worker để xác nhận Python và JVM phối hợp được.
3. Đọc raw Parquet, kiểm tra timestamp/vùng; áp dụng cùng thứ tự cách ly ngoài tháng, vùng 264/265, thời lượng ≤ 0.
4. Đối chiếu số dòng ở từng bước và cả bảy cờ chất lượng.
5. Nhóm vùng/giờ và full outer join với bảng đối chứng, yêu cầu không có nhóm khác biệt và tổng chuyến khớp.
6. Chỉ khi đạt mới ghi Parquet tổng hợp và báo cáo `complete=true`.

Spark dùng session timezone UTC để bảo toàn nhãn giờ naive trong phép thử. Không coi timestamp nguồn là giờ UTC thực tế, không suy ra offset, không thay chính sách DST. Tháng 01 không có ngày DST; job này chưa kiểm chứng logic DST cho cả năm.

Đầu ra:

- `data/processed/spark_trial_2024-01_v1/hourly_observed/`: Parquet tổng hợp Spark, không cộng thêm vào dataset chính.
- `data/processed/spark_trial_2024-01_v1/audit.json` và `artifacts/metrics/spark_trial_2024-01.json`: số liệu và kết quả đối soát.

Job từ chối chạy khi thư mục output không rỗng để tránh ghi đè kết quả đã nghiệm thu. Nếu cần chạy lại, dùng thư mục output mới bằng cấu hình mount riêng; không xóa dữ liệu cũ theo lệnh tự động. Chưa ghi dữ liệu NYC vào HBase, chưa tạo lại lưới đầy đủ, chưa huấn luyện mô hình. PyArrow Windows 19 không được cài vào Spark: phép thử sử dụng Spark SQL đọc Parquet trực tiếp, không dùng pandas UDF/Arrow bridge.
