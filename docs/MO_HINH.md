# Giai đoạn 4 — Đặc trưng, huấn luyện và đánh giá dự báo

Ngày chuẩn bị và hoàn thành: 08/10/2026. Trạng thái: **đã nghiệm thu giai đoạn 4**, sau phê duyệt phương án ở quyết định 014. Xem [tổng kết giai đoạn 4](tong-ket/TONG_KET_GIAI_DOAN_4.md) và [bằng chứng](../artifacts/metrics/stage4_acceptance.json). Các bước dưới đây là phương án đã triển khai và hướng dẫn tái lập.

## 1. Bài toán và phạm vi đã thống nhất

Dự báo số chuyến đón taxi ghi nhận của từng vùng trong **một giờ tiếp theo**, sau khi giờ hiện tại kết thúc. Phạm vi 263 vùng, dữ liệu 2023–2025. Dùng lưới giờ đã nghiệm thu, không xử lý lại 128 triệu chuyến cho mỗi lần train. Nguồn đầu vào theo giờ chỉ gồm các đường dẫn trong manifest; không đọc đệ quy cả data/processed.

Giữ chính sách DST/thiếu nguồn đã duyệt: nhãn bị che không được điền 0 hoặc forward-fill. Đây là thử nghiệm dự báo một bước trên dữ liệu lịch sử đã làm sạch; nguồn TLC công bố trễ nên chưa chứng minh triển khai thời gian thực.

## 2. Phương án đã duyệt và lý do

| Lựa chọn | Phương án đề xuất | Lý do |
|---|---|---|
| Mốc so sánh | Seasonal naive: số chuyến cùng vùng, cùng giờ tuần trước | Đơn giản, phản ánh mùa vụ theo tuần, có thể giải thích và tái lập |
| Mô hình chính | Một Random Forest dùng chung các vùng trong Spark ML | Có sẵn trong image Spark, học quan hệ phi tuyến; không phải cài thêm thư viện ML trên Windows |
| Đặc trưng | Với giờ đích h: y(h−1), y(h−2), y(h−24), y(h−168), trung bình [h−24,h), [h−168,h), giờ/thứ của h và mã vùng phân loại | Tất cả thông tin đều nằm trước giờ đích, trừ lịch tương lai đã biết |
| Thiếu đặc trưng | Không train RF trên dòng thiếu; khi dự báo dùng baseline nếu RF không đủ đầu vào. Baseline thiếu y(h−168) thì dùng trung bình vùng từ train của fold | Tránh coi thiếu là 0; vẫn đánh giá hệ thống trên toàn bộ nhãn hợp lệ, công bố tỷ lệ dự phòng |
| Độ đo chọn phương án | MAE chung trên toàn bộ validation là chính; RMSE, WAPE và MAE trung bình theo vùng là bổ sung | MAE có đơn vị chuyến/giờ; WAPE không chia cho từng nhãn 0. Báo cáo theo vùng để thấy ảnh hưởng vùng đông khách |
| Giới hạn thử nghiệm | RF seed 42, 20 cây; thử maxDepth 8 và 12, minInstancesPerNode 20; đo pilot trước | Giới hạn số lượt train để phù hợp máy cá nhân; tham số cụ thể là điểm xuất phát, chưa phải kết quả tối ưu |

Mã vùng phải được mã hóa phân loại và encoder chỉ fit trên train. Với 263 vùng và bucket dự phòng, cấu hình cây cần maxBins tối thiểu 264; pilot sẽ kiểm tra metadata thực tế trước khi train lớn. Không dùng mã vùng như thang đo liên tục.

Các cửa sổ phải đủ số giờ hợp lệ mới có giá trị; `avg` bỏ qua null một cách mặc định chưa đáp ứng chính sách. Dùng lưới đầy đủ, sắp theo giờ trong từng vùng; kiểm tra khóa trùng/khoảng cách giờ trước khi dùng lag. Nhãn hoặc cờ chất lượng của giờ đích không được làm đặc trưng.

Nếu dòng thiếu trung bình vùng từ train, dùng trung bình toàn train và đánh dấu rõ. Dự báo được chặn dưới tại 0 thống nhất; giữ số thực khi đánh giá, chỉ làm tròn để hiển thị.

## 3. So sánh lịch sử và khóa test

Cấu hình đã có: [temporal_splits.json](../configs/temporal_splits.json).

- A: bắt đầu 01/01/2024; B: bắt đầu 01/01/2023.
- Ba fold: train trước tháng 10, 11, 12/2024; validation tương ứng một tháng. Phương án A không được dùng 2023 làm ngữ cảnh đặc trưng ở đầu train.
- Mỗi fold fit lại encoder, mô hình và các trung bình dự phòng trên train của chính fold đó. Ngữ cảnh quá khứ được nối qua ranh giới tháng/năm; không reset lag đầu validation/test.
- Các phương án phải dự báo trên cùng tập khóa vùng–giờ validation. Báo cáo sai số RF trên phần đủ đặc trưng và sai số toàn hệ thống có dự phòng riêng; không so các độ đo tính trên tập dòng khác nhau.
- Chọn độ dài lịch sử và tham số bằng MAE gộp theo số dòng của ba fold; hòa thì ưu tiên cấu hình đơn giản, lịch sử ngắn hơn. Ghi cấu hình đã khóa và checksum trước khi tính sai số 2025.
- Train lại phương án thắng với dữ liệu trước 01/01/2025; đánh giá toàn năm 2025 một lần ở bước nghiệm thu. Không sửa mô hình theo kết quả test. Được dùng các giờ test đã kết thúc làm đầu vào dự báo giờ tiếp theo theo giả định một bước.
- Nếu RF không cải thiện baseline trên validation, giữ baseline làm phương án phục vụ, báo cáo RF và nguyên nhân trung thực. Không cần ép kết quả “mô hình phức tạp thắng”.

## 4. Các bước thực hiện và đầu ra

| Bước | Công việc | Đầu ra và điều kiện đi tiếp |
|---|---|---|
| 4.0 Chuẩn bị | Kiểm tra Python/image Spark, manifest/checksum/schema lưới; thử Spark ML và lưu/đọc model trên dữ liệu tổng hợp nhỏ | Preflight đạt; phê duyệt phương án được ghi trong QUYET_DINH.md |
| 4.1 Đặc trưng | Viết Spark window, tách nhãn khỏi đầu vào; kiểm thử chuỗi biết trước, DST, ranh giới năm và thay dữ liệu tương lai | Parquet đặc trưng trên D, manifest/schema/số dòng đủ và thiếu; kiểm thử chống nhìn tương lai đạt |
| 4.2 Baseline và pilot | Chạy baseline đầy đủ validation; thử RF nhỏ để đo RAM/thời gian và save/load; pilot giữ 2025 ngoài đánh giá | Metrics baseline, thời gian pilot; báo người dùng nếu RAM/thời gian buộc đổi cấu hình |
| 4.3 Validation | Hai độ dài lịch sử × hai cấu hình RF × ba fold, tổng tối đa 12 lượt fit; chạy tuần tự, tái dùng feature cache | Bảng metrics, coverage/dự phòng, tham số và thời gian; cấu hình thắng đã khóa |
| 4.4 Train cuối và test | Fit phương án khóa, predict 2025, tính sai số theo vùng/giờ/tháng, phân tích giờ cao điểm và vùng ít chuyến | Model/version, manifest đầu vào, bảng lỗi, predictions, biểu đồ dùng được cho báo cáo |
| 4.5 Kiểm tra và tài liệu | Thử save/load dự đoán trùng khớp; lệnh tái lập, nghiệm thu và tổng kết | stage4_acceptance.json và tong-ket/TONG_KET_GIAI_DOAN_4.md chỉ ghi hoàn thành khi mọi bước đạt |

Không ấn định thời gian train khi chưa đo pilot. Sau pilot sẽ báo thời gian một lượt và ước lượng toàn bộ. Người dùng chỉ cần Docker Desktop hoạt động; Spark chạy theo job rồi kết thúc. Huấn luyện đọc Parquet, có thể để HBase dừng để giảm RAM; giai đoạn 5 kết nối dự báo với HBase/dashboard. Bảng dự báo HBase sẽ được thiết kế và chốt khi tích hợp phục vụ, không tự đổi bảng lịch sử ở giai đoạn này.

## 5. File dự kiến và tài nguyên

```text
configs/stage4_model.json                 # Cấu hình sau khi duyệt
src/models/                              # Preflight, features, baseline, train/evaluate, predict, verify
tests/test_model_features.py              # Nhìn tương lai, thiếu dữ liệu, ranh giới thời gian
tests/test_model_evaluation.py            # Tập so sánh và độ đo
docker/spark/compose.models.yaml          # Dùng image hiện có; output bind mount sang D
scripts/run_stage4.ps1                    # Chạy từng bước, dừng khi lỗi
data/processed/model_features_v1/         # Không push GitHub
data/processed/model_predictions_v1/      # Không push GitHub
artifacts/models/                         # Model và encoder, không push
artifacts/metrics/stage4_*.json            # Kết quả nhỏ, đẩy GitHub
reports/figures/                          # Biểu đồ chọn lọc
docs/MO_HINH.md                           # Hướng dẫn hiện hành này
docs/tong-ket/TONG_KET_GIAI_DOAN_4.md      # Tạo khi có kết quả thực tế
```

Tạo image bigdata-spark-ml:3.5.7-py311-np1264 mở rộng image bigdata-spark:3.5.7-py311 bằng NumPy 1.26.4, phụ thuộc bắt buộc cho Spark ML. Giữ Spark local[2], container 4 GiB/driver 2 GiB. Windows dùng venv hiện có để điều phối và kiểm tra Arrow. Không cần SQL, GPU, tải lại dataset hoặc thêm Kafka/HDFS để triển khai bước này. Dung lượng feature/cache/model sẽ đo trong pilot; xuất file qua bind mount trên D, tránh ghi dữ liệu lớn vào writable layer Docker trên C.

## 6. Nghiệm thu

### Lệnh chạy hiện hành

Từ PowerShell ở thư mục gốc, Docker Desktop đang bật. Môi trường Windows dùng requirements-stage4-windows-lock.txt sau khi cài thành công; phần NumPy/Matplotlib Windows phục vụ biểu đồ, không huấn luyện Spark.

**Máy mới clone Git, đã hoàn thành lại giai đoạn 2–3 và chưa có feature/model/dự báo cục bộ:** các metrics stage4 đi kèm repo là bằng chứng lịch sử, không phải cache cho máy mới. Chuyển chúng vào archive cục bộ trước khi chạy các bước dưới. Folder archive giữ nguyên bằng chứng, không xóa dữ liệu nguồn:

```powershell
New-Item -ItemType Directory -Force -Path .tools/stage4-evidence-original
Get-ChildItem -LiteralPath artifacts/metrics -File -Filter 'stage4_*' |
    Move-Item -Destination .tools/stage4-evidence-original
```

Trên máy đã có đầy đủ kết quả giai đoạn 4, dùng bước Verify để kiểm tra lại. Nếu chỉ có một phần output hoặc muốn đổi code/config, kiểm tra manifest và giữ bản cũ trước khi tạo một lượt thử mới; các lệnh train cố ý từ chối ghi đè kết quả khác context. Không dùng metrics đã commit làm bằng chứng rằng máy mới vừa huấn luyện thành công.

```powershell
.\.venv\Scripts\python.exe -m pip install --no-cache-dir -r requirements-stage4-windows-lock.txt
.\scripts\run_stage4.ps1 -Step Prepare
.\scripts\run_stage4.ps1 -Step Pilot
.\scripts\run_stage4.ps1 -Step Validation
# Validation chạy đủ các fold rồi khóa lựa chọn; sau đó mới dùng test:
.\scripts\run_stage4.ps1 -Step Final
.\scripts\run_stage4.ps1 -Step Verify
$env:MPLCONFIGDIR = "$PWD\.tools\stage4-tmp\matplotlib"
.\.venv\Scripts\python.exe -m src.models.report
```

Trên máy mới phải build image Spark giai đoạn 3 trước; Dockerfile.models dùng image đó làm nền. Máy hiện tại đã có image và dữ liệu, không cần tải lại. Script dừng khi lỗi, không ghi đè model hoặc dataset đã tồn tại. Job train hoàn tất được bỏ qua khi checksum context giống hệt; file chạy dở phải được kiểm tra và lưu lại bằng tên khác trước khi thử lại. Bước Prepare không tự dựng lại feature khi đã có manifest hoàn tất; nghiệm thu kiểm tra checksum toàn bộ file feature. Không sửa code/config giữa các lượt validation, vì lựa chọn sẽ từ chối kết quả khác context.

### Kết quả chuẩn bị đã đo

- Preflight: đủ 6.917.952 dòng nguồn, checksum và schema ba năm khớp; bằng chứng giai đoạn 3 còn nguyên.
- Image ETL thiếu NumPy cho ML, đã build image ML riêng và pip check đạt. Smoke tổng hợp 24 dòng, save/reload dự báo giống nhau.
- Năm nhóm kiểm tra Spark window đạt: lag/mean qua năm, thay tương lai, masking/cửa sổ đầy đủ/tách vùng, thiếu giờ/đầu chuỗi, zero hợp lệ.
- Tạo feature đầy đủ: 63,56 giây, 55.464.532 byte Parquet trên D. Ảnh chụp RAM lúc tạo: 1,839 GiB/4 GiB; không phải số peak.
- Pilot: 151.488 dòng train đủ feature, 44.184 nhãn đánh giá; 12,15 giây fit, 42,06 giây cả job, save/reload 100 mẫu giống nhau. Chưa dùng số này làm kết quả đánh giá chính thức.
- 24 unit tests đạt sau khi cài thư viện biểu đồ. File tạm của kiểm thử đặt trên D do quyền ghi sandbox trên C bị chặn.

Nghiệm thu cuối: 27 unit tests; model nạp lại được đối chiếu toàn bộ 2.291.256 dự báo năm 2025 (gồm dự phòng), 0 sai lệch trong 32,47 giây. Model cuối khoảng 5,97 MB; dự báo Parquet khoảng 21,74 MB. Xem số liệu validation/test và các giới hạn trong tổng kết giai đoạn 4.

Lỗi thử ban đầu TIMESTAMP_NTZ được sửa bằng phép cast timestamp trên trục UTC trung tính; không gán offset NYC cho nguồn. File module tên select.py đã được đổi thành choose_model.py để tránh che thư viện chuẩn Python. Một bản metric lỗi feature được giữ để truy vết; kết quả thành công ở stage4_features.json.

- Feature test chứng minh sửa dữ liệu tại/sau h không đổi đầu vào của h; giữ DST/null và lịch sử từng vùng.
- Không trùng khóa; các phương án cùng số dòng/khóa đánh giá, coverage và dự phòng có thống kê.
- Ba fold đầy đủ cho hai lịch sử; encoder/fallback chỉ học từ train. Test 2025 không tham gia lựa chọn.
- Model và baseline có MAE/RMSE/WAPE; WAPE null khi tổng nhãn bằng 0, không tạo số sai.
- Model nạp lại dự báo giống model trước lưu trên mẫu kiểm tra; lưu seed, phiên bản, checksum nguồn, tham số, thời gian và tài nguyên.
- Có predictions để giai đoạn 5 dùng, giới hạn lịch sử phát lại được mô tả rõ.
- File tổng kết riêng ghi kết quả thật và hạn chế. Giai đoạn 4 hoàn thành khi các bằng chứng đạt; báo cáo Word/PPT hoàn chỉnh ở giai đoạn 6.

## Tài liệu kỹ thuật

Đối chiếu 08/10/2026: [Forecasting: Principles and Practice — time series cross-validation](https://otexts.com/fpp3/tscv.html) giải thích chỉ dùng quan sát trước mốc dự báo; [Spark 3.5.7 RandomForestRegressor](https://archive.apache.org/dist/spark/docs/3.5.7/api/python/reference/api/pyspark.ml.regression.RandomForestRegressor.html) mô tả tham số và hỗ trợ đặc trưng phân loại; [phụ thuộc PySpark](https://spark.apache.org/docs/3.5.7/api/python/getting_started/install.html) ghi NumPy là bắt buộc cho ML DataFrame API. Số cây/độ sâu, chính sách dự phòng và tiêu chí chọn ở trên là lựa chọn riêng cho dự án, không phải yêu cầu bắt buộc của các nguồn.
