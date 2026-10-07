# Thiết kế Docker cần triển khai

Cập nhật 07/10/2026: HBase 2.1.2 trong container hiện có đã vượt qua phép thử Python ghi/get/scan 3 dòng giả lập, ghi lặp không tăng số dòng và đọc lại đúng sau restart cùng container/volume. Bằng chứng tại `artifacts/metrics/hbase_smoke.json` và `hbase_restart.json`; hướng dẫn tại `docs/GIAI_DOAN_3.md`. Các mục chưa xác nhận dưới đây ghi lại trạng thái khảo sát ban đầu; việc tái tạo container/khôi phục volume và lưu ZooKeeper vẫn chưa nghiệm thu.

Container `hbase-demo` cũ được giữ nguyên. Đã có Compose/Dockerfile riêng cho Spark, xem [hướng dẫn Spark](spark/README.md). Đã hoàn thiện [Compose HBase tái lập](hbase/README.md) với cổng 19090/16011, volume chứa cả HBase/ZooKeeper; phép thử khôi phục sang container và volume khác đạt. Đây là trạng thái cuối giai đoạn 3, thay thế các ghi chú khảo sát chưa hoàn thành bên dưới.

## Cấu hình đã xác nhận từ kết quả người dùng

- Image được cấu hình: `dajobe/hbase` (chưa xác định phiên bản HBase và image digest).
- Cổng `9090/tcp` và `16010/tcp` ánh xạ ra cùng cổng host trên mọi địa chỉ IPv4/IPv6.
- Volume Docker loại `volume`, quyền đọc/ghi, gắn vào `/data`.
- Tên volume hiện tại: `ee5e68e6753f94290d0d414792142c6143f8d48825b4bb9da538a179641a7189`.
- Chưa xác nhận dịch vụ healthy, Thrift phục vụ được client hoặc thư mục lưu trữ HBase/ZooKeeper nằm trong volume. Ánh xạ cổng không chứng minh dịch vụ đang lắng nghe.

## Kiểm tra tiếp trong PowerShell của người dùng

```powershell
docker inspect hbase-demo --format '{{.State.Status}}'
docker logs --tail 80 hbase-demo
Test-NetConnection localhost -Port 9090
```

Nếu trạng thái là `exited`, chạy `docker start hbase-demo`, đợi khởi động rồi kiểm tra lại. Thử mở `http://localhost:16010` để xem UI nếu dịch vụ sẵn sàng. TCP thành công mới chỉ chứng minh kết nối cổng; sau đó cần thử client HappyBase đọc danh sách bảng và thử put/get ở bảng thử riêng.

Trước khi chuyển sang Compose: xác định phiên bản HBase, image digest, đường dẫn `hbase.rootdir` và thư mục ZooKeeper; xác nhận các đường dẫn dữ liệu bền vững nằm trong `/data`. Giữ nguyên container/volume hiện tại đến khi có phương án tái lập và sao lưu được kiểm tra. Khi thêm container Spark phải cấu hình cùng Docker network và alias phù hợp; tên `hbase` trong kế hoạch chưa tự tồn tại cho container hiện có.

Các bước nghiệm thu:

1. Chọn bản phát hành HBase và JDK tương thích theo tài liệu Apache; cố định bản sau thử nghiệm.
2. Khởi động HBase standalone với dữ liệu lưu ở volume, gateway Thrift 1 và healthcheck thực sự kiểm tra dịch vụ.
3. Tạo bảng thử, put/get/scan từ client Python và kiểm tra restart không mất dữ liệu.
4. Container Spark dùng Python 3.11, JDK 17, PySpark 3.5.7; đọc Parquet mẫu và groupBy.
5. Thử ghi một batch kết quả từ Spark qua HBase; dùng hostname service trong network Docker.
6. Chỉ publish cổng cần cho máy cá nhân qua 127.0.0.1; ghi CPU/RAM/image và đường dẫn mount vào hướng dẫn.

Không cần thêm Kafka/Kubernetes vào cấu hình tối thiểu. Nếu GV yêu cầu HDFS, thiết kế và kiểm thử HDFS/HBase tương thích trước khi khóa môi trường.
