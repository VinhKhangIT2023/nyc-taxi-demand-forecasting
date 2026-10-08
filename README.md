# NYC Taxi Demand — Spark & HBase

Phân tích và chuẩn bị dữ liệu dự báo số lượt đón taxi theo khu vực và giờ tại New York. Dự án dùng NYC TLC Yellow Taxi 2023–2025, Apache Spark để xử lý và Apache HBase để lưu kết quả theo giờ. Số chuyến đã phục vụ là đại diện cho nhu cầu quan sát được, không phải toàn bộ nhu cầu giao thông công cộng.

## Trạng thái

- Hoàn thành giai đoạn 1–5: môi trường, dữ liệu, Spark/HBase, mô hình và dashboard.
- Đã xử lý 36 tháng: 128.202.548 dòng nguồn, giữ 126.994.028 chuyến; lưới 263 vùng có 6.917.952 dòng vùng–giờ.
- Hai lượt nạp HBase và phục hồi từ archive được đối chiếu đầy đủ, không sai lệch. Bộ kiểm thử tại lần nghiệm thu: 21/21 đạt.
- Đã so sánh 12 lượt validation và khóa Random Forest dùng lịch sử 2023–2024. Test 2025 đủ 2.291.256 nhãn: MAE 3,851 so với baseline 5,320 (giảm 27,61%); 27 unit tests và 5 nhóm kiểm tra cửa sổ Spark đạt.
- Dashboard có 5 trang, đọc dữ liệu thật từ HBase; đủ 2.291.256 dự báo 2025 và 297.716 tổng hợp ngày/tháng được đối chiếu đầy đủ. 36 unit tests và kiểm thử Web/DST/dự phòng/CSV/mobile đạt. Báo cáo Word/PPT cuối kỳ còn ở giai đoạn 6.

Các con số trên là kết quả của snapshot đã nghiệm thu, không phải kết quả tự có sau khi clone repo. Xem [tổng kết từng giai đoạn](docs/tong-ket/) và [bằng chứng nghiệm thu](artifacts/metrics/stage3_full_acceptance.json).

## Bắt đầu trên máy mới

Môi trường đã kiểm thử: Windows, PowerShell, Git, VSCode, Python 3.13.16 chính thức và Docker Desktop chạy Linux containers. Spark dùng Python 3.11/Java 17 trong Docker; không cần cài Spark hoặc Java trực tiếp vào Windows.

```powershell
git clone <URL_REPOSITORY> nyc-taxi-demand
cd nyc-taxi-demand
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
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

## Chạy dashboard

Trên máy đã có dữ liệu/model giai đoạn 1–4, lần đầu chuẩn bị bảng phục vụ:

```powershell
.\scripts\run_stage5.ps1 -Step Prepare
.\scripts\run_stage5.ps1 -Step Geometry
.\scripts\run_stage5.ps1 -Step Load
.\scripts\run_stage5.ps1 -Step App
```

Mở [localhost:8501](http://127.0.0.1:8501). Máy đã nghiệm thu giai đoạn 5 chỉ cần bật HBase và chạy bước App. Xem [hướng dẫn dashboard](docs/DASHBOARD.md) và [tổng kết giai đoạn 5](docs/tong-ket/TONG_KET_GIAI_DOAN_5.md). Web phát lại dự báo một giờ năm 2025, có số thực tế để đối chiếu; không tự train hoặc giả nguồn trực tiếp. Dữ liệu nguồn có 128,20 triệu chuyến, dữ liệu sạch giữ 126,99 triệu chuyến; bảng phục vụ nhỏ là dữ liệu tổng hợp, không phải cắt còn 297 nghìn chuyến.

## Dữ liệu và cách tiếp tục phát triển

Chuyến chi tiết nằm trong Parquet; HBase chứa số đếm theo vùng–giờ, nhãn và cờ chất lượng. Phân biệt số 0 với thiếu dữ liệu; che nhãn hai ngày DST mỗi năm. Không đọc đệ quy toàn bộ `data/processed`, vì có bản trung gian và tập thử. Dùng loader `src.ingestion.open_dataset` hoặc `src.ingestion.load_split` theo [hợp đồng dữ liệu](docs/DU_LIEU.md).

Giai đoạn 4 đã nghiệm thu theo [hướng dẫn mô hình](docs/MO_HINH.md) và [tổng kết](docs/tong-ket/TONG_KET_GIAI_DOAN_4.md): so sánh lịch sử 2024 với 2023–2024 trên cùng validation cuối 2024, giữ 2025 làm holdout. Model và dự báo lưu trên D, bị Git bỏ qua; Spark chạy theo scripts/run_stage4.ps1. Giai đoạn 5 đã tích hợp dự báo vào HBase/dashboard. Các quyết định về mô hình và đánh giá ghi trong [nhật ký quyết định](docs/QUYET_DINH.md). Sau mỗi giai đoạn có một bản tổng kết theo [mẫu](docs/tong-ket/MAU_TONG_KET_GIAI_DOAN.md).

## Cấu trúc repo

```text
configs/          Cấu hình chia tập theo thời gian
src/              ingestion, processing, storage, models, dashboard
tests/            Kiểm thử dữ liệu, mã hóa HBase, độ đo và lựa chọn mô hình
scripts/          Các bước nghiệm thu và backup/restore
docker/           Dockerfile, Compose và cấu hình dịch vụ
data/             Raw, reference, intermediate, processed (không đưa dữ liệu lên Git)
artifacts/metrics/ Manifest và bằng chứng kiểm tra nhỏ, được theo dõi bằng Git
artifacts/models/ Mô hình và encoder đã sinh ra (không push)
docs/             Hướng dẫn hiện hành và kế hoạch
  tong-ket/       Một file tổng kết cho mỗi giai đoạn
  LICH_SU.md     Lịch sử khảo sát/thử nghiệm đã gộp, không dùng để cài đặt
reports/          Biểu đồ đánh giá; báo cáo/slide cuối kỳ chưa hoàn thành
notebooks/        Dành cho khảo sát khi cần
```

[Danh mục tài liệu](docs/README.md) giúp chọn đúng hướng dẫn. `.gitkeep` chỉ giữ những thư mục chưa có file được Git theo dõi. `requirements.txt` dùng lock dashboard giai đoạn 5 đã kiểm thử; các lock giai đoạn 3–4 giữ để tái lập lịch sử. Spark dùng `requirements-spark.txt`.

## Lưu trữ và đóng dịch vụ

`docker compose -p bigdata-hbase -f docker/hbase/compose.yaml stop` giữ volume. Không dùng `down -v` khi còn cần dữ liệu. Docker có thể lưu đĩa ảo trên C dù repo nằm ở D; xem [ghi chú dung lượng](docs/VAN_HANH.md#dung-lượng-và-dọn-dẹp).

Chỉ push code, cấu hình, requirements, tài liệu và metrics nhỏ. `.gitignore` đã loại dữ liệu lớn, `.venv`, `.tools`, cache, log và file Word yêu cầu môn học. Không gửi nguyên venv sang máy khác; tạo lại từ requirements.
