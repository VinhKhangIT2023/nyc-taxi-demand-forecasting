# Tổng kết giai đoạn 3 — Spark và HBase trên toàn bộ 2023–2025

Hoàn thành 08/10/2026. Trạng thái: **đã nghiệm thu đầy đủ giai đoạn 3**. Bằng chứng: [stage3_full_acceptance.json](../../artifacts/metrics/stage3_full_acceptance.json), `complete=true`, 21/21 tests đạt. Mốc thử tháng 01/2024 và 168 giờ trước đây đã được mở rộng theo yêu cầu người dùng. Không dùng kết quả thử làm kết luận cho toàn bộ dữ liệu.

## 1. Mục tiêu và phạm vi

Spark xử lý đủ 36 tháng Yellow Taxi 2023–2025, đối chiếu với giai đoạn 2; HBase lưu toàn bộ 263 vùng theo giờ. Xác minh dữ liệu sau hai lượt nạp và sau phục hồi vào container/volume mới. Chi tiết chuyến đi được giữ trong Parquet; HBase phục vụ truy vấn số đếm và chất lượng theo giờ.

## 2. Công việc đã triển khai

- Python Windows 3.13.16 chính thức, venv và thư viện khóa phiên bản; giữ Smart App Control.
- Spark 3.5.7/Python 3.11.17/Java 17 trong Docker, local[2], 2 CPU/4 GiB, driver 2 GiB.
- Spark đọc từng tháng, kiểm tra checksum, áp dụng quy tắc lọc, chuẩn hóa schema 28 cột, kiểm tra 7 cờ chất lượng và tổng hợp theo giờ.
- Tạo lại lưới giờ bằng Spark và so từng dòng với giai đoạn 2. Giữ số đếm mô tả ngày DST, che nhãn huấn luyện; phân biệt zero/null.
- HBase 2.1.2 trong Compose với named volume, ZooKeeper lưu cùng volume, healthcheck và dừng sạch.
- Bảng chính `transport_demand_hourly_v1`: khóa `ZZZ#YYYYMMDDHH`, ba nhóm cột d/q/m, một phiên bản; batch 500 thao tác, bật WAL, hai Spark worker.
- Đối chiếu HBase theo luồng với nguồn Parquet độc lập; phát hiện mọi dòng/ô sai hoặc thừa/thiếu. Kiểm tra cả range query qua ranh giới năm, ngày DST và point query.
- Có script nạp hai lần, sao lưu offline, phục hồi volume mới và nghiệm thu tự động. Chỉ báo đạt khi các bằng chứng thực tế đều thành công.

## 3. Kết quả đã xác nhận

| Hạng mục | Kết quả |
|---|---|
| Spark 36 tháng | 128.202.548 dòng raw → 126.994.028 chuyến giữ lại |
| Lưới giờ | 6.917.952 dòng; 0 sai khác với giai đoạn 2 |
| Thời gian Spark ETL | 555,70 giây, khoảng 9 phút 16 giây |
| HBase nạp lần 1 | 6.917.952 dòng, 347,79 giây |
| Đọc kiểm tra lần 1 | Đủ 6.917.952 dòng, 0 sai lệch, 310,31 giây |
| Nạp/đọc kiểm tra lần 2 | 6.917.952 dòng, 0 sai lệch; nạp 341,98 giây, đọc 352,32 giây; fingerprint giống lượt 1 |
| Phục hồi bản sao lưu đầy đủ | Đủ 6.917.952 dòng, 0 sai lệch, fingerprint giống hai lượt nạp; đọc đối chiếu 326,17 giây |
| Đối chiếu sau khởi động lại | Đủ 6.917.952 dòng, 0 sai lệch, 279,56 giây |
| Kiểm tra sau khi người dùng bật lại Docker | Spark chạy được; 24 point query và 3 range query khớp |
| Unit tests cuối giai đoạn | 21/21 đạt |

| Năm | Dòng vùng–giờ | Tổng chuyến ghi nhận | Tổng nhãn đủ điều kiện |
|---|---:|---:|---:|
| 2023 | 2.303.880 | 37.909.554 | 37.709.280 |
| 2024 | 2.310.192 | 41.010.718 | 40.785.663 |
| 2025 | 2.303.880 | 48.073.756 | 47.809.126 |

Số nhãn thấp hơn tổng chuyến vì che ngày DST theo quyết định đã duyệt, không phải mất dữ liệu khi nạp. Mỗi năm có 263 dòng thiếu nguồn tại giờ chuyển sang giờ mùa hè; toàn bộ hai ngày DST có 12.624 dòng không dùng làm nhãn. Toàn bộ ba năm có 6.880.080 dòng đủ điều kiện làm nhãn.

## 4. Đầu ra và bằng chứng

- `artifacts/metrics/spark_full.json`: thống kê, checksum nguồn và thời gian từng tháng.
- `data/processed/spark_full_v1/YYYY-MM/`: lưới tháng tạo bằng Spark, không push GitHub.
- `artifacts/metrics/hbase_full_load_pass1.json`, `hbase_full_load_pass2.json`: kết quả hai lượt nạp.
- `artifacts/metrics/hbase_full_verify_pass1.json`, `hbase_full_verify_pass2.json`: đối chiếu toàn bộ, tổng theo năm, fingerprint nội dung.
- `artifacts/metrics/hbase_full_after_restore.json`, `hbase_full_recovery.json`: bằng chứng phục hồi.
- `artifacts/metrics/stage3_full_acceptance.json`: nghiệm thu đầy đủ, chỉ thành công nếu `complete=true`.
- `artifacts/metrics/stage3_resources_*.jsonl`: ảnh chụp mức tài nguyên tại thời điểm đo, không phải đo peak hay benchmark.
- [Hướng dẫn chạy toàn bộ](../VAN_HANH.md), [nhật ký triển khai](../LICH_SU.md#giai-doan-3), [quyết định phạm vi](../QUYET_DINH.md).

Archive đầy đủ: 17.174.343.680 byte (17,17 GB), SHA256 `1CFF1D90784634C780D0C1B505D9F90DA2DEB79342986F300BFB628B779C70F7`. Chu trình backup/restore và kiểm tra mất 1.346,65 giây. Nguồn dừng sạch exit code 0; đích là container và volume khác. Bảng thử 168 giờ cũng khớp sau phục hồi. Fingerprint nội dung bảng chính của cả ba lần đọc: `e7a9cdeb6332fd07c6458f42661ade814f792fcf5bb9997c540842fc2373615d`.

Các metrics thử trước đó được giữ làm lịch sử. Archive `.tools/hbase-backups/stage3-full.tar`, dữ liệu Parquet, venv và log bị Git bỏ qua. Repo lưu code, cấu hình, tests, docs và metrics nhỏ. Docker volume/image không nằm trong repo.

## 5. Quyết định và lý do

Giữ chính sách dữ liệu đã được người dùng duyệt. Xử lý từng tháng giúp kiểm soát bộ nhớ và khác biệt schema; chưa cần cụm nhiều máy cho thực nghiệm này. Dùng khóa cố định để nạp lặp không sinh thêm dòng; ô thiếu được xóa thay vì ghi 0. Giữ dữ liệu chi tiết trong Parquet để phân tích/huấn luyện, đưa toàn bộ kết quả vùng–giờ vào HBase cho truy vấn ứng dụng.

Bản sao lưu dùng volume đã dừng sạch và được kiểm tra trên volume mới. Phép thử restart hoặc kiểm tra vài dòng không thay thế được việc đối chiếu toàn bộ bản phục hồi.

## 6. Hạn chế và vấn đề

- Phát sinh ở bước bàn giao: log ghi khoảng dừng 50.314 ms, các phiên ZooKeeper hết hạn và HMaster abort; Docker báo OOMKilled=false. Chưa xác định được nguyên nhân khoảng dừng là GC hay lịch chạy/suspend của máy/VM. Đã khởi động lại HBase managed, trở lại healthy; đối chiếu lại đủ 6.917.952 dòng đạt 0 sai lệch trong 279,56 giây, cùng fingerprint trước đó. Người dùng sau đó báo đã tắt máy/Docker rồi bật lại: đã bật lại HBase và chạy Spark kiểm tra 24 point query cùng 3 range query ở cả ba năm, đều khớp. Bằng chứng: `hbase_runtime_incident.json` và `hbase_full_post_restart.json`. Không đổi heap, timeout hoặc chính sách dữ liệu để che lỗi.

- HBase standalone/local filesystem, Java 8 và image HBase cũ phù hợp môi trường học tập hiện tại; chưa chứng minh khả năng chịu lỗi nhiều máy hoặc phục hồi khi mất điện đột ngột.
- Nạp bảng lớn không có giao dịch nguyên tử cho toàn bộ tập; khi gián đoạn phải nạp lại và đối chiếu trước khi sử dụng.
- Backup nằm trên cùng máy; chưa có bản lưu ngoài máy. Bản HBase không thay thế backup Parquet hoặc bảng `users` của container cũ.
- HappyBase có cảnh báo `pkg_resources` deprecated; setuptools đã khóa 80.9.0 và các phép kiểm tra hiện hành vẫn chạy được.
- Đã tái lập môi trường bằng container/volume mới trên máy hiện tại; chưa kiểm thử trên máy của Hiếu.
- Chưa huấn luyện mô hình, làm dashboard hoặc hoàn tất Word/PPT cuối kỳ.

## 7. Bàn giao và giai đoạn tiếp theo

HBase ứng dụng: `bigdata-hbase-hbase-1`, Thrift 19090/UI 16011. Container `hbase-demo` cũ ở 9090/16010 giữ nguyên. Container phục hồi đầy đủ dùng 19092/16013 và đã dừng sau kiểm tra để tiết kiệm RAM. Khi mở máy chỉ cần bật HBase managed, không phải chạy lại ETL/nạp dữ liệu.

Giai đoạn 4: đặc trưng theo thời gian, baseline và huấn luyện/đánh giá. So sánh lịch sử 2024 với 2023–2024 bằng validation cuối 2024; giữ 2025 làm holdout, không dùng để chọn mô hình. Tiếp tục thống nhất với người dùng các quyết định mô hình trước khi triển khai.

## Cập nhật sau nghiệm thu — dọn dẹp 08/10/2026

Theo yêu cầu dọn repo và dung lượng, đã kiểm tra archive đầy đủ còn nguyên rồi xóa container/volume phục hồi thử (17,17 GB). Các mô tả giữ volume phục hồi ở trên là trạng thái tại thời điểm nghiệm thu; hiện chỉ giữ archive trên D và các metrics kiểm chứng. HBase chính không bị xóa. Xem [vận hành và dung lượng](../VAN_HANH.md#dung-lượng-và-dọn-dẹp) và cleanup_2026-10-08.json.
