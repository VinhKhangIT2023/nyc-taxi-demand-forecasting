# Docker cho dự án

- [HBase](hbase/README.md): dịch vụ lưu trữ chính, Thrift 19090/UI 16011, dữ liệu ở named volume.
- [Spark](spark/README.md): image Python 3.11/Java 17/Spark 3.5.7, chạy job theo nhu cầu.
- [Hướng dẫn đầy đủ](../docs/VAN_HANH.md): chuẩn bị, nạp, kiểm tra, backup/restore và dung lượng.

Container `hbase-demo` là môi trường cũ, không phải nơi lưu bảng đầy đủ của pipeline hiện hành. Compose thử tháng 01/2024 và script thử 168 giờ được giữ để tái lập các bằng chứng cũ. Dùng `docker/spark/compose.full.yaml` cho luồng đầy đủ.
