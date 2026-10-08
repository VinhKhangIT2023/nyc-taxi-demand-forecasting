# Spark

Image `bigdata-spark:3.5.7-py311` dùng Spark 3.5.7, Python 3.11.17 và Java 17. Base image khóa digest; gói Java được cài từ Debian tại thời điểm build nên rebuild không nhất thiết giống từng byte với image cũ.

Spark chạy `local[2]`, driver 2 GiB, container tối đa 2 CPU/4 GiB. Đây là xử lý một máy. Không cần Java/Spark trong venv Windows.

Từ thư mục gốc repo:

```powershell
# Build image; chỉ cần lần đầu hoặc khi thay dependencies/Dockerfile.
docker compose -f docker/spark/compose.yaml build
# Luồng đầy đủ, cần dữ liệu giai đoạn 2:
docker compose -f docker/spark/compose.full.yaml run --rm spark /workspace/src/processing/spark_full.py
# Kiểm tra chỉ đọc khi HBase đã có dữ liệu:
docker compose -f docker/spark/compose.full.yaml run --rm spark /workspace/src/storage/check_stage3_services.py
```

`compose.full.yaml` gắn nguồn ở chế độ chỉ đọc, ghi kết quả vào `data/processed/spark_full_v1` và metrics. HBase được truy cập qua `host.docker.internal:19090`. Container Spark tự xóa sau job; image và đầu ra còn trên máy.

`.dockerignore` loại dataset, venv và tài liệu khỏi build context. Không cần giữ một container Spark chạy thường trực. Luồng nạp HBase và nghiệm thu xem [vận hành](../../docs/VAN_HANH.md).

`compose.yaml` còn giữ lệnh mặc định thử tháng 01/2024 để tái lập bằng chứng ban đầu; dùng `compose.full.yaml` cho toàn bộ 36 tháng. Các script thử vẫn được giữ vì có kiểm thử và module dùng chung phụ thuộc vào chúng.
