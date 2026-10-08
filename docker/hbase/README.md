# HBase

Cấu hình hiện hành: `compose.yaml`, `hbase-site.xml`, `start.sh`.

- HBase 2.1.2, Java 8; image cố định bằng digest trong Compose.
- Project `bigdata-hbase`, volume `bigdata-hbase_hbase_data` chứa HBase và ZooKeeper.
- Thrift `127.0.0.1:19090`, UI `http://localhost:16011`.
- Bảng chính `transport_demand_hourly_v1`, khóa `ZZZ#YYYYMMDDHH`, nhóm cột d/q/m, một phiên bản.
- Giới hạn container 2 GiB, heap Java 512 MiB cho mỗi tiến trình master/thrift. Healthcheck dùng HBase shell.

Chạy từ thư mục gốc repo:

```powershell
docker compose -p bigdata-hbase -f docker/hbase/compose.yaml up -d
docker compose -p bigdata-hbase -f docker/hbase/compose.yaml ps
docker compose -p bigdata-hbase -f docker/hbase/compose.yaml stop
```

`stop` giữ dữ liệu. Không dùng `down -v` khi còn cần volume. Trên máy mới, dịch vụ ban đầu trống: [hướng dẫn vận hành](../../docs/VAN_HANH.md) mô tả nạp, kiểm tra và backup/restore.

Container `hbase-demo` ở cổng 9090/16010 là môi trường cũ, không phải dịch vụ chính của pipeline đầy đủ. Bản phục hồi thử đã được dọn sau nghiệm thu để tiết kiệm dung lượng; archive và bằng chứng vẫn giữ. Xem [tổng kết giai đoạn 3](../../docs/tong-ket/TONG_KET_GIAI_DOAN_3.md).

Đây là HBase standalone dùng filesystem cục bộ cho đồ án, không phải cụm production hoặc bảo đảm chịu lỗi nhiều máy. Khi máy/VM dừng lâu và phiên ZooKeeper hết hạn, khởi động lại rồi kiểm tra đọc dữ liệu; không xóa volume để sửa lỗi kết nối.
