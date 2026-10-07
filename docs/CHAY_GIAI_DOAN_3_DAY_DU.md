# Chạy và kiểm tra giai đoạn 3 trên toàn bộ dữ liệu

Phạm vi: 36 tháng 2023–2025, 263 vùng, 6.917.952 dòng vùng–giờ. Thực hiện từ thư mục gốc repo trong PowerShell. Kết quả nghiệm thu hiện hành nằm trong `artifacts/metrics/stage3_full_acceptance.json`; các file `*trial*` và `stage3_acceptance.json` là bằng chứng thử nghiệm trước đó.

## 1. Môi trường

- Docker Desktop Linux containers đang chạy.
- Image `bigdata-spark:3.5.7-py311` đã build theo `docker/spark/Dockerfile`; xem README trong thư mục đó nếu cần dựng lại.
- Windows `.venv` dùng Python 3.13, thư viện trong `requirements-stage3-windows.txt`.
- Có dữ liệu raw đủ 36 tháng, lookup, các manifest và dữ liệu giai đoạn 2 đã nghiệm thu. Dữ liệu không được tải kèm khi clone GitHub.

```powershell
.\.venv\Scripts\python.exe --version
docker compose -p bigdata-hbase -f docker/hbase/compose.yaml up -d
docker compose -p bigdata-hbase -f docker/hbase/compose.yaml ps
```

Chờ `healthy`. HBase ứng dụng: Thrift `127.0.0.1:19090`, giao diện `http://localhost:16011`, bảng `transport_demand_hourly_v1`, volume `bigdata-hbase_hbase_data`. Container `hbase-demo` cũ dùng 9090/16010, không phải nơi chứa bộ dữ liệu đầy đủ của luồng này.

## 2. Spark xử lý đủ 36 tháng

```powershell
docker compose -f docker/spark/compose.full.yaml run --rm spark /workspace/src/processing/spark_full.py
```

Script kiểm tra checksum nguồn, áp dụng quy tắc đã duyệt, chuẩn hóa schema tháng, so sánh các tổng và cờ chất lượng; đối chiếu từng nhóm quan sát được và từng dòng lưới giờ với giai đoạn 2. Tạo lại lưới độc lập bằng Spark, kể cả zero/null/DST. Đầu ra riêng: `data/processed/spark_full_v1/YYYY-MM/`. Chạy lại ghi đè các phân vùng Spark này, không sửa nguồn hay đầu ra giai đoạn 2. Thông tin kết quả và thời gian từng tháng: `artifacts/metrics/spark_full.json`.

Spark chạy local[2], giới hạn 2 CPU/4 GiB; Python/Java của Spark nằm trong Docker. Container chạy xong tự xóa do `--rm`, image và đầu ra trên ổ đĩa vẫn còn. Đây là xử lý trên một máy, chưa phải cụm nhiều máy.

## 3. Nạp và đối chiếu đầy đủ

```powershell
docker compose -f docker/spark/compose.full.yaml run --rm spark /workspace/src/storage/spark_hbase_full.py --pass-number 1
.\.venv\Scripts\python.exe -m src.storage.verify_hbase_full --report artifacts/metrics/hbase_full_verify_pass1.json
docker compose -f docker/spark/compose.full.yaml run --rm spark /workspace/src/storage/spark_hbase_full.py --pass-number 2
.\.venv\Scripts\python.exe -m src.storage.verify_hbase_full --report artifacts/metrics/hbase_full_verify_pass2.json --compare artifacts/metrics/hbase_full_verify_pass1.json
```

Mỗi lượt nạp đủ 36 tháng bằng hai Spark worker, batch 500 thao tác, bật WAL. Khóa `ZZZ#YYYYMMDDHH` xác định duy nhất vùng–giờ, ba nhóm cột `d`, `q`, `m`, giữ một phiên bản. Khi giá trị thiếu, xóa ô đếm cũ nếu có; không ghi 0 thay thế. Nạp lại là upsert cùng khóa. Không có giao dịch nguyên tử cho toàn bộ 6,9 triệu dòng: nếu gián đoạn, chạy lại lượt nạp rồi kiểm tra đầy đủ; báo cáo chỉ có `complete=true` khi hoàn thành.

Script kiểm tra đọc từng dòng/cell HBase và đối chiếu với Parquet giai đoạn 2, kiểm tra thừa/thiếu khóa, tổng số chuyến/cờ theo năm, ba range query và sáu point query. Dấu vân tay nội dung không gồm timestamp nội bộ HBase nên dùng để đối chiếu khi nạp lại. Xử lý theo luồng, không gom cả bảng vào RAM.

## 4. Sao lưu và phục hồi

```powershell
.\scripts\test_hbase_full_recovery.ps1
.\.venv\Scripts\python.exe -m src.storage.verify_stage3_full
```

Script yêu cầu lượt đối chiếu thứ hai thành công, dừng sạch HBase managed rồi sao lưu toàn volume vào `.tools/hbase-backups/stage3-full.tar` và khởi động lại nguồn. Phục hồi vào project/volume mới `bigdata-hbase-full-restore`, cổng 19092/16013, kiểm tra toàn bộ bảng đầy đủ và bảng thử 168 giờ. Không nạp lại dữ liệu để che lỗi phục hồi. Khi kiểm tra đạt, dừng container phục hồi để tiết kiệm RAM; giữ volume và archive.

Script từ chối ghi đè nếu archive/volume phục hồi đã tồn tại. Sau lần nghiệm thu, không cần chạy lại backup mỗi khi mở máy. Muốn thử bản sao lưu mới cần dùng tên archive/project mới và kiểm tra đúng volume nguồn/đích. Backup cùng ổ đĩa dùng để chứng minh phục hồi; muốn bảo vệ khi hỏng ổ cần sao chép archive ra nơi lưu khác.

Lệnh tổng hợp cho lần nghiệm thu đầu, sau khi Spark hoàn thành:

```powershell
.\scripts\run_stage3_full.ps1
.\.venv\Scripts\python.exe -m src.storage.verify_stage3_full
```

## 5. Sử dụng hằng ngày và GitHub

Chỉ bật Docker Desktop và `docker compose -p bigdata-hbase -f docker/hbase/compose.yaml start`. Không nạp lại toàn bộ mỗi lần mở máy. `stop` giữ dữ liệu; không dùng `down -v` khi còn cần volume.

Đưa code, cấu hình Docker, requirements, tài liệu và các JSON metrics nhỏ lên GitHub. `.gitignore` loại dữ liệu lớn, `.venv`, `.tools` (gồm archive), cache và log. Volume Docker nằm ngoài cây repo; không push volume hay image vào Git. Hiếu cần dựng môi trường và chuẩn bị dữ liệu theo hướng dẫn, hoặc nhận archive ngoài Git để phục hồi vào volume riêng.

126.994.028 chuyến chi tiết nằm trong Parquet; HBase chứa toàn bộ lưới theo giờ phục vụ ứng dụng. Mô hình, dashboard và báo cáo Word/PPT cuối kỳ là các giai đoạn tiếp theo.
