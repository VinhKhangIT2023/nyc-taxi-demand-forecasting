# HBase tái lập cho giai đoạn 3

Đã kiểm thử ngày 07/10/2026. Dùng cùng HBase 2.1.2/Java 8 như container cũ, khóa image bằng registry digest trong Compose. Đây là môi trường standalone cho học tập, không phải cụm production. [Tài liệu Apache HBase 2.1](https://hbase.apache.org/2.1/book.html) mô tả standalone và giới hạn độ bền khi dùng local filesystem.

## Những cấu hình đã bổ sung

- Named volume `/data` chứa cả `/data/hbase` và `/data/zookeeper`; không để dữ liệu ZooKeeper ở thư mục tạm của container.
- Hostname cố định, file cấu hình và script startup có trong repo; không phụ thuộc container ID cũ.
- Cổng host chỉ bind loopback: `19090` cho Thrift, `16011` cho giao diện. Không tranh cổng 9090/16010 của `hbase-demo`.
- Giới hạn RAM 2 GiB, heap 512 MiB mỗi tiến trình HBase. Script chuyển tín hiệu dừng tới Java để shutdown sạch, timeout 60 giây.
- Healthcheck dùng HBase shell xác nhận active master; phép thử ứng dụng kiểm tra Thrift riêng, không suy ra từ TCP hoặc healthcheck đơn thuần.

## Dựng trên máy Hiếu

1. Clone repo, mở thư mục gốc, khởi động Docker Desktop Linux containers.
2. Chạy:

```text
docker compose -p bigdata-hbase -f docker/hbase/compose.yaml up -d
docker compose -p bigdata-hbase -f docker/hbase/compose.yaml ps
```

Đợi trạng thái healthy. Nếu chưa đạt, xem log:

```text
docker compose -p bigdata-hbase -f docker/hbase/compose.yaml logs --tail 80 hbase
```

Giao diện: http://localhost:16011. Python Windows kết nối `127.0.0.1:19090`. Trong container Spark trên Docker Desktop, dùng `host.docker.internal:19090`. Hiếu không cần tạo container `hbase-demo` thủ công.

3. Cài Python chính thức và venv theo `docs/CAI_DAT.md`, dùng `requirements-stage3-windows.txt`. Chuẩn bị dữ liệu/manifest giai đoạn 2 theo `docs/GIAI_DOAN_2.md` vì raw/Parquet không nằm trên GitHub. Build Spark theo `docker/spark/README.md`.
4. Nạp mẫu 168 giờ đã duyệt và đọc lại:

```text
docker compose -f docker/spark/compose.yaml run --rm -e HBASE_PORT=19090 -e HBASE_TRIAL_METRICS=artifacts/metrics/spark_hbase_managed_trial.json spark /workspace/src/storage/spark_hbase_trial.py
```

```powershell
.\.venv\Scripts\python.exe -m src.storage.inspect_hbase_trial --port 19090 --report artifacts/metrics/hbase_managed_readback.json
.\.venv\Scripts\python.exe -m src.storage.verify_hbase_edges --port 19090
```

Mẫu thật gồm 168 dòng/26.365 chuyến. Phép thử edge tạo bảng giả lập riêng và kiểm tra 0, null, DST, xóa cell cũ và khôi phục giá trị 0. Bảng synthetic không được tính vào số chuyến NYC.

## Kiểm tra sao lưu/khôi phục đã thực hiện

Chạy bằng PowerShell từ thư mục gốc, khi môi trường managed đã có mẫu thử:

```powershell
.\scripts\test_hbase_recovery.ps1
```

Script chỉ xử lý project `bigdata-hbase`, không dừng hay sửa `hbase-demo`. Nó:

1. Lấy fingerprint mọi dòng/cell và cấu hình family của các bảng thử (từ chối bảng khác).
2. Dừng sạch HBase managed, yêu cầu exit code 0, rồi tar toàn volume đã ngừng ghi.
3. Lưu `.tools/hbase-backups/stage3.tar` và checksum; khởi động lại nguồn.
4. Tạo project `bigdata-hbase-restore`, volume mới, kiểm tra trống rồi giải nén archive. Cổng riêng 19091/16012.
5. Đợi healthy, so sánh fingerprint mọi bảng và đọc 168 dòng độc lập với Parquet.
6. Ghi metrics và dừng container restore để tiết kiệm RAM, giữ volume/archive/container làm bằng chứng.

Script từ chối nếu archive hoặc volume restore đã tồn tại. Không xóa bằng chứng để chạy lại; lần thử mới cần tên archive/project riêng được rà soát. Đây là backup offline của môi trường mẫu được tạo mới, không phải backup toàn bộ dữ liệu NYC hay bảng `users` trong container gốc.

Kết quả đã đạt: 168 dòng thật và 2 dòng giả lập được khôi phục sang container/volume khác, nội dung và schema khớp hoàn toàn. Không có thao tác reinsert dữ liệu sau restore. Bằng chứng ở `artifacts/metrics/hbase_recovery.json`, `hbase_before_backup.json`, `hbase_after_restore.json`, `hbase_restored_readback.json`.

## Vận hành và giới hạn

```text
docker compose -p bigdata-hbase -f docker/hbase/compose.yaml stop
docker compose -p bigdata-hbase -f docker/hbase/compose.yaml start
```

Stop/start giữ volume. Không dùng `down -v` nếu còn cần dữ liệu: tùy chọn đó xóa volume. Image không chứa code/dataset cá nhân; Git chỉ lưu cấu hình, code và metrics nhỏ. Archive ở `.tools/` bị Git bỏ qua; giữ thêm bản sao ngoài máy nếu muốn bảo vệ trước mất ổ đĩa.

HBase 2.1.2 là bản cũ, được giữ để tái lập môi trường đã có. Không expose môi trường này ra Internet. Phép thử xác nhận khôi phục sau shutdown sạch, không chứng minh an toàn khi mất điện hoặc khả năng chịu lỗi nhiều máy. Chưa chạy trên phần cứng của Hiếu; hướng dẫn đã được kiểm chứng bằng container và volume mới trên máy hiện tại.
