# NYC Taxi Demand — Spark & HBase

Phân tích và chuẩn bị dữ liệu dự báo số lượt đón taxi theo khu vực và giờ tại New York. Dự án dùng NYC TLC Yellow Taxi 2023–2025, Apache Spark để xử lý và Apache HBase để lưu kết quả theo giờ. Số chuyến đã phục vụ là đại diện cho nhu cầu quan sát được, không phải toàn bộ nhu cầu giao thông công cộng.

## Trạng thái

- Hoàn thành giai đoạn 1–3: môi trường, dữ liệu và tích hợp Spark/HBase.
- Đã xử lý 36 tháng: 128.202.548 dòng nguồn, giữ 126.994.028 chuyến; lưới 263 vùng có 6.917.952 dòng vùng–giờ.
- Hai lượt nạp HBase và phục hồi từ archive được đối chiếu đầy đủ, không sai lệch. Bộ kiểm thử tại lần nghiệm thu: 21/21 đạt.
- Chưa triển khai mô hình dự báo, dashboard và báo cáo Word/PPT cuối kỳ. Đây chưa phải ứng dụng hoàn chỉnh để người dùng cuối sử dụng.

Các con số trên là kết quả của snapshot đã nghiệm thu, không phải kết quả tự có sau khi clone repo. Xem [tổng kết từng giai đoạn](docs/tong-ket/) và [bằng chứng nghiệm thu](artifacts/metrics/stage3_full_acceptance.json).

## Bắt đầu trên máy mới

Môi trường đã kiểm thử: Windows, PowerShell, Git, VSCode, Python 3.13.16 chính thức và Docker Desktop chạy Linux containers. Spark dùng Python 3.11/Java 17 trong Docker; không cần cài Spark hoặc Java trực tiếp vào Windows.

```powershell
git clone <URL_REPOSITORY> nyc-taxi-demand
cd nyc-taxi-demand
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-stage3-windows.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Thay `<URL_REPOSITORY>` bằng URL của repo. Trong VSCode, chọn **Python: Select Interpreter → .venv/Scripts/python.exe**. Có thể kích hoạt bằng `.\.venv\Scripts\Activate.ps1`; các lệnh ở đây gọi Python trực tiếp nên không phụ thuộc việc kích hoạt terminal. Xem [cài đặt](docs/CAI_DAT.md).

Repo không chứa dataset, venv, Docker volume hoặc archive sao lưu. Có hai tình huống:

1. **Máy mới chưa có dữ liệu:** làm theo [chuẩn bị dữ liệu](docs/DU_LIEU.md), tải đủ ba năm và Taxi Zone Lookup, chạy làm sạch rồi nghiệm thu giai đoạn 2. Tiếp tục [vận hành Spark/HBase](docs/VAN_HANH.md) để build image, xử lý 36 tháng và nạp bảng. Dự trù dung lượng cho cả dữ liệu trên ổ làm việc và đĩa ảo Docker; các phép thử phục hồi tạo thêm một bản sao lớn.
2. **Máy đã có dữ liệu và volume:** bật Docker Desktop rồi dùng các lệnh sau; không tải hoặc nạp lại mỗi lần mở máy.

```powershell
docker compose -p bigdata-hbase -f docker/hbase/compose.yaml up -d
docker compose -p bigdata-hbase -f docker/hbase/compose.yaml ps
# Chờ HBase healthy rồi chạy kiểm tra chỉ đọc:
docker compose -f docker/spark/compose.full.yaml run --rm spark /workspace/src/storage/check_stage3_services.py
```

HBase: Thrift `localhost:19090`, giao diện [localhost:16011](http://localhost:16011), bảng `transport_demand_hourly_v1`. Spark chạy theo job và tự kết thúc; việc không có container Spark thường trực là bình thường. `up -d` trên máy mới chỉ tạo dịch vụ trống, không tự nạp dữ liệu.

## Dữ liệu và cách tiếp tục phát triển

Chuyến chi tiết nằm trong Parquet; HBase chứa số đếm theo vùng–giờ, nhãn và cờ chất lượng. Phân biệt số 0 với thiếu dữ liệu; che nhãn hai ngày DST mỗi năm. Không đọc đệ quy toàn bộ `data/processed`, vì có bản trung gian và tập thử. Dùng loader `src.ingestion.open_dataset` hoặc `src.ingestion.load_split` theo [hợp đồng dữ liệu](docs/DU_LIEU.md).

Giai đoạn tiếp theo là tạo đặc trưng và huấn luyện: so sánh lịch sử 2024 với 2023–2024 trên cùng validation cuối 2024, giữ 2025 làm holdout. Các quyết định về mô hình và đánh giá cần ghi vào [nhật ký quyết định](docs/QUYET_DINH.md). Sau mỗi giai đoạn tạo một bản tổng kết theo [mẫu](docs/tong-ket/MAU_TONG_KET_GIAI_DOAN.md).

## Cấu trúc repo

```text
configs/          Cấu hình chia tập theo thời gian
src/              ingestion, processing, storage; models/dashboard chưa triển khai
tests/            Kiểm thử quy tắc dữ liệu và mã hóa HBase
scripts/          Các bước nghiệm thu và backup/restore
docker/           Dockerfile, Compose và cấu hình dịch vụ
data/             Raw, reference, intermediate, processed (không đưa dữ liệu lên Git)
artifacts/metrics/ Manifest và bằng chứng kiểm tra nhỏ, được theo dõi bằng Git
artifacts/models/ Mô hình sinh ra (chưa triển khai, không push)
docs/             Hướng dẫn hiện hành và kế hoạch
  tong-ket/       Một file tổng kết cho mỗi giai đoạn
  lich-su/        Khảo sát/thử nghiệm cũ, không dùng để cài đặt hiện hành
reports/          Hình, báo cáo và slide cuối kỳ (chưa hoàn thành)
notebooks/        Dành cho khảo sát khi cần
```

[Danh mục tài liệu](docs/README.md) giúp chọn đúng hướng dẫn. `.gitkeep` chỉ giữ những thư mục chưa có file được Git theo dõi. Các thư viện ứng dụng dự kiến trong `requirements.txt` chưa phải môi trường dashboard đã nghiệm thu; môi trường hiện dùng `requirements-stage3-windows.txt`, Spark dùng `requirements-spark.txt`.

## Lưu trữ và đóng dịch vụ

`docker compose -p bigdata-hbase -f docker/hbase/compose.yaml stop` giữ volume. Không dùng `down -v` khi còn cần dữ liệu. Docker có thể lưu đĩa ảo trên C dù repo nằm ở D; xem [ghi chú dung lượng](docs/VAN_HANH.md#dung-lượng-và-dọn-dẹp).

Chỉ push code, cấu hình, requirements, tài liệu và metrics nhỏ. `.gitignore` đã loại dữ liệu lớn, `.venv`, `.tools`, cache, log và file Word yêu cầu môn học. Không gửi nguyên venv sang máy khác; tạo lại từ requirements.
