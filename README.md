> Cập nhật 07/10/2026: giai đoạn 3 đang triển khai toàn bộ 2023–2025 theo yêu cầu đã duyệt. Kết quả thử nghiệm bên dưới chưa phải nghiệm thu toàn bộ. Chỉ chốt khi Spark đủ 36 tháng, HBase đủ 6.917.952 dòng, nạp lại và phục hồi được đối chiếu đầy đủ.

# Phân tích và dự báo nhu cầu sử dụng xe công cộng

Đồ án Nhập môn Big Data của Đào Văn Hiếu và Nguyễn Đặng Vĩnh Khang. Công nghệ được ghi trong danh sách đăng ký: Apache HBase.

**Trạng thái dữ liệu:** đã tải và xử lý đủ 36 tháng Yellow Taxi 2023–2025, giữ **126.994.028 chuyến** theo quy tắc v1. Có lưới 263 vùng theo giờ, phân biệt số 0 và thiếu dữ liệu, đồng thời che nhãn ngày đổi giờ mùa hè. Xem [giai đoạn 2 và kết quả nghiệm thu](docs/GIAI_DOAN_2.md). Chưa triển khai pipeline Spark, mô hình, dashboard hoặc Docker Compose.

**Phạm vi thực nghiệm:** so sánh lịch sử 2024 với 2023–2024 trên cùng validation cuối 2024; giữ 2025 cho đánh giá cuối. Dùng loader `src.ingestion.open_dataset` để không đọc trùng tập thử tháng 01/2024 hoặc các bản trung gian. Các tài liệu tập thử và năm 2023 ghi lại các mốc cũ.

Phạm vi đề xuất: dự báo số chuyến taxi đón khách theo khu vực trong giờ tiếp theo, sử dụng dữ liệu NYC TLC. Đây là lựa chọn triển khai của nhóm cần chốt với giảng viên, không phải bộ dữ liệu đã được giảng viên chỉ định.

## Bắt đầu

**Giai đoạn 3 đã hoàn thành phạm vi hạ tầng và tích hợp thử:** Spark đối soát 76.190 nhóm vùng–giờ không sai khác; Spark → HBase đạt trên 168 giờ/26.365 chuyến, ghi lặp không nhân đôi; HBase tái lập và backup/restore sang container/volume mới đạt. Có 19 kiểm thử thành công. Xem [tổng kết giai đoạn 3](docs/TONG_KET_GIAI_DOAN_3.md), [hướng dẫn Spark](docker/spark/README.md) và [hướng dẫn HBase](docker/hbase/README.md). Chưa nạp HBase đầy đủ hoặc huấn luyện mô hình.

**Môi trường Windows hiện hành:** Python 3.13.16 chính thức, venv tại `.venv`, thư viện xử lý dữ liệu/HBase tại `requirements-stage3-windows.txt`. Đã kiểm tra 15 tests và đối soát lại dataset. Xem đầu [CAI_DAT.md](docs/CAI_DAT.md); các ghi chép Python 3.11 là lịch sử hoặc kế hoạch riêng cho Spark trong Docker.

**Tổng kết tiến độ:** mỗi giai đoạn trong kế hoạch 6 giai đoạn có file `docs/TONG_KET_GIAI_DOAN_N.md`. Đã có [giai đoạn 1](docs/TONG_KET_GIAI_DOAN_1.md), [giai đoạn 2](docs/TONG_KET_GIAI_DOAN_2.md) và [giai đoạn 3](docs/TONG_KET_GIAI_DOAN_3.md), ghi công việc, kết quả, bằng chứng kiểm tra và vấn đề còn lại.

1. Đọc [kế hoạch chi tiết](docs/KE_HOACH.md), có phân công, mốc tuần, yêu cầu báo cáo và tiêu chí hoàn thành.
2. Làm theo [hướng dẫn môi trường và GitHub](docs/CAI_DAT.md).
3. Ghi nguồn dữ liệu vào [danh mục dữ liệu](data/README.md).
4. Cập nhật [nhật ký nhóm](docs/NHAT_KY_NHOM.md) hằng tuần.
5. Xem [khảo sát dữ liệu](docs/KHAO_SAT_DU_LIEU.md) và [nhật ký quyết định](docs/QUYET_DINH.md) trước khi triển khai làm sạch.

## Cấu trúc hiện tại

```text
DoAn_BigData/
├── README.md
├── .gitignore
├── .gitattributes
├── .env.example
├── .vscode/                  # Interpreter và extension đề xuất
├── requirements.txt         # Thư viện ứng dụng; chưa phải lock đã kiểm thử
├── requirements-spark.txt   # Thư viện cho container Spark
├── configs/                 # Tham số dữ liệu, mô hình, đường dẫn
├── data/
│   ├── README.md
│   ├── raw/                 # File tải gốc, không push
│   ├── interim/             # Kết quả trung gian, không push
│   ├── processed/           # Dữ liệu sạch và bảng theo giờ, không push
│   └── reference/           # Danh mục khu vực và dữ liệu bản đồ
├── docker/
│   ├── README.md            # Thiết kế các service cần xây dựng
│   ├── hbase/
│   └── spark/
├── src/
│   ├── ingestion/           # Tải và kiểm tra nguồn
│   ├── processing/          # Spark ETL và đặc trưng
│   ├── storage/             # Schema và đọc ghi HBase
│   ├── models/              # Baseline, train, evaluate, predict
│   └── dashboard/           # Streamlit
├── notebooks/               # Khảo sát; logic dùng lại chuyển vào src
├── scripts/                 # Các lệnh vận hành sẽ bổ sung khi triển khai
├── tests/                   # Kiểm tra dữ liệu, đặc trưng, tích hợp
├── artifacts/
│   ├── models/              # Mô hình sinh ra, không push
│   └── metrics/             # CSV/JSON đánh giá để đưa vào báo cáo
├── reports/
│   ├── figures/
│   ├── report/              # Báo cáo Word cuối kỳ
│   └── slides/              # Slide thuyết trình
└── docs/                    # Kế hoạch, hướng dẫn, nhật ký
```

Các thư mục chưa triển khai có `.gitkeep` để Git theo dõi. File Word yêu cầu môn học ở gốc được giữ nguyên. `.venv/` sẽ được tạo riêng trên mỗi máy và bị Git bỏ qua.

