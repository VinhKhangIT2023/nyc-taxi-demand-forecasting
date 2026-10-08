> Hoàn thành đầy đủ ngày 08/10/2026: Spark đủ 36 tháng 2023–2025; HBase đủ 6.917.952 dòng, hai lượt nạp và phục hồi được đối chiếu từng ô, 0 sai lệch, 21/21 tests đạt. Xem [tổng kết giai đoạn 3](tong-ket/TONG_KET_GIAI_DOAN_3.md) và [hướng dẫn hiện hành](VAN_HANH.md). Các mốc thử nghiệm bên dưới là lịch sử triển khai.

> Giai đoạn 4 hoàn thành 08/10/2026: 12 lượt validation; Random Forest 20 cây/depth 12 với lịch sử 2023–2024; test 2025 có 2.291.256 nhãn, MAE 3,851 so với baseline 5,320, 27 tests và 5 nhóm Spark window đạt. Xem [tổng kết giai đoạn 4](tong-ket/TONG_KET_GIAI_DOAN_4.md) và [hướng dẫn mô hình](MO_HINH.md).

> Cập nhật giai đoạn 5 hoàn thành 08/10/2026: 5 trang dashboard HBase có số thực tế kiểm chứng; đủ 2.291.256 dự báo và 297.716 tổng hợp, đối chiếu toàn bộ cả sau khi bật lại HBase; 36 tests và kiểm thử Web/mobile đạt. Xem [tổng kết giai đoạn 5](tong-ket/TONG_KET_GIAI_DOAN_5.md), [dashboard](DASHBOARD.md). Chỉ còn giai đoạn 6; không mở rộng 2026/Redis trong lần triển khai này.

# Kế hoạch triển khai đồ án phân tích và dự báo nhu cầu sử dụng xe công cộng

Ngày lập: 05/10/2026. Thành viên: Đào Văn Hiếu và Nguyễn Đặng Vĩnh Khang.

Cập nhật phạm vi dữ liệu 07/10/2026: đã mở rộng và xử lý đủ 2023–2025 theo quyết định sau khảo sát. Các đề xuất sáu tháng dưới đây là kế hoạch ban đầu; phạm vi và cách đọc hiện hành nằm trong [DU_LIEU.md](DU_LIEU.md), quyết định tại [QUYET_DINH.md](QUYET_DINH.md). “Giai đoạn 2” chuẩn bị dữ liệu trong tiến trình làm việc này không có nghĩa đã hoàn thành toàn bộ đợt nộp giai đoạn 2 của môn học.

Kế hoạch hướng đến một sản phẩm chạy được trên máy cá nhân: chọn khu vực, xem lịch sử nhu cầu, xem dự báo giờ tiếp theo và kiểm tra sai số. Spark xử lý dữ liệu chuyến đi; HBase phục vụ lưu trữ và truy vấn kết quả; Streamlit hiển thị dashboard. Phân công dưới đây là đề xuất để hai thành viên thống nhất.

## 1. Yêu cầu thực sự của môn học

### Quy ước tổng kết 6 giai đoạn triển khai

Theo yêu cầu người dùng ngày 07/10/2026, dự án có 6 giai đoạn triển khai. Sau mỗi giai đoạn phải có một file riêng `docs/tong-ket/TONG_KET_GIAI_DOAN_N.md` (N từ 1 đến 6), được cập nhật trước khi thông báo hoàn thành giai đoạn. Đây là mốc triển khai nội bộ, không đồng nhất với các đợt nộp của môn học hoặc lịch 10 tuần bên dưới.

Mỗi bản tổng kết phải ghi: mục tiêu/phạm vi, công việc thực tế đã làm, kết quả và số liệu, file đầu ra kèm bằng chứng kiểm tra, quyết định và lý do, vấn đề/hạn chế còn lại, công việc của giai đoạn sau. Không ghi kế hoạch thành kết quả, không tự gán đóng góp cho thành viên. Nếu có sửa đổi sau nghiệm thu, ghi ngày và nội dung cập nhật.

Hiện có [tổng kết giai đoạn 1](tong-ket/TONG_KET_GIAI_DOAN_1.md), [giai đoạn 2](tong-ket/TONG_KET_GIAI_DOAN_2.md), [giai đoạn 3](tong-ket/TONG_KET_GIAI_DOAN_3.md), [giai đoạn 4](tong-ket/TONG_KET_GIAI_DOAN_4.md) và [giai đoạn 5](tong-ket/TONG_KET_GIAI_DOAN_5.md). Giai đoạn 6 chưa hoàn thành; tạo bản tổng kết khi có kết quả thực tế. Dùng [mẫu tổng kết](tong-ket/MAU_TONG_KET_GIAI_DOAN.md) để giữ cấu trúc nhất quán. Các file Markdown này được đưa lên GitHub và làm tư liệu cho báo cáo Word cuối kỳ.

Nguồn đối chiếu: file `Ke hoach Do an mon hoc Nhap mon Big data_SV.docx`, mục II, III và IV; ảnh danh sách đăng ký ghi đề tài 10 và Apache HBase.

| Yêu cầu trong tài liệu | Việc nhóm cần làm | Bằng chứng nộp hoặc demo |
|---|---|---|
| Nêu bài toán, đầu vào, đầu ra và giá trị | Định nghĩa nhu cầu theo khu vực và giờ; xác định ai dùng | Chương giới thiệu và trang dashboard |
| Có công nghệ Big Data/lưu trữ, xử lý phân tán | Sử dụng Spark và HBase thực sự | Mã ETL, schema, dữ liệu trong HBase, log chạy |
| Thu thập, mô tả bộ dữ liệu | Ghi nguồn, ngày tải, phạm vi, số dòng, dung lượng và schema | Danh mục dữ liệu và bảng thống kê |
| Làm sạch, xử lý thiếu, trùng, ngoại lệ | Xây quy tắc có thống kê trước/sau | Báo cáo chất lượng dữ liệu |
| Thiết kế kiến trúc và luồng xử lý | Vẽ luồng và giải thích lựa chọn | Sơ đồ, cấu hình, hướng dẫn chạy |
| Chọn mô hình và cài đặt thực nghiệm | Baseline theo mùa và ít nhất một mô hình hồi quy | Code huấn luyện, tham số, model artifact |
| Đánh giá và giải thích | MAE, RMSE; phân tích theo khu vực và giờ | Bảng so sánh, biểu đồ sai số, hạn chế |
| Trực quan hóa/sản phẩm minh họa | Dashboard lịch sử và dự báo | Demo có dữ liệu thật |
| Hoàn thiện hồ sơ | Source, liên kết dữ liệu, Word, PPT, hướng dẫn, đóng góp | Bộ nộp Classroom |

**Có, phải viết báo cáo Word.** Tài liệu đồng thời yêu cầu PPT và demo, và ghi rõ nộp Source Code, file Word, file PPT trên Classroom.

Rubric 10 điểm: tính ứng dụng 1; lưu trữ/xử lý/phân tích 2; mô hình/công nghệ 2,5; trực quan hóa/ứng dụng 2,5; báo cáo 1; phối hợp nhóm 1. Vì vậy cần hoàn thiện cả chuỗi xử lý, dashboard và hồ sơ, không chỉ một notebook mô hình.

Hai điểm phải xác nhận với giảng viên khi chốt phạm vi:

- Lịch giai đoạn 1 không thống nhất: đoạn đầu mục IV ghi tuần 5–6, bảng ghi tuần 6–7. Chuẩn bị sẵn giai đoạn 1 ở tuần 5; hạn chính thức theo giảng viên. Giai đoạn 2 dự kiến tuần 9; tuần 10 thuyết trình. Chưa có ngày cụ thể nên không tự suy ra ngày nộp.
- Dòng đề tài 10 gợi ý HDFS và Spark; ảnh đăng ký ghi HBase. Yêu cầu chung chỉ đòi ít nhất một công nghệ phù hợp. Kế hoạch dùng Spark + HBase, HDFS bổ sung nếu giảng viên yêu cầu đúng kiến trúc gợi ý. Không coi HBase và HDFS là cùng một thành phần.

## 2. Phạm vi sản phẩm nên chốt

Tên triển khai đề xuất: **Phân tích và dự báo nhu cầu taxi theo khu vực tại New York bằng Apache Spark và Apache HBase**. Giữ tên đề tài đăng ký trên bìa và dùng tên này làm phạm vi thực nghiệm.

- Đối tượng: người theo dõi và lập kế hoạch bố trí xe.
- Đơn vị dữ liệu đầu ra: một khu vực × một giờ.
- Biến cần dự báo: số chuyến đón khách trong giờ tiếp theo.
- Thời điểm dự báo: khi giờ hiện tại đã kết thúc, có đầy đủ số đếm đến giờ đó.
- Phạm vi đã triển khai: Yellow Taxi NYC TLC đủ 36 tháng 2023–2025. Mẫu tháng 01/2024 là bước khảo sát lịch sử, không còn là giới hạn dataset.
- Demo là dự báo trên dữ liệu lịch sử được phát lại theo thời gian. Giao diện phải ghi ngày dữ liệu, mốc dự báo và phân biệt lịch sử với tương lai mô phỏng.
- Số chuyến đã phục vụ là đại diện cho nhu cầu quan sát được; không đo được khách không gọi được xe, nhu cầu tiềm ẩn hoặc nhu cầu của toàn bộ giao thông công cộng.

Đề tài trong Word cho phép taxi, xe buýt hoặc xe đạp công cộng. Taxi là đề xuất để sớm có dữ liệu thực nghiệm; nếu lớp yêu cầu riêng xe buýt Việt Nam phải thay nguồn sau khi khảo sát khả năng tiếp cận dữ liệu lượt khách.

Chức năng tối thiểu:

1. Lọc khoảng thời gian và khu vực; hiển thị tổng chuyến, xu hướng theo ngày/giờ và khu vực đông khách.
2. Heatmap giờ × thứ; bảng xếp hạng khu vực. Bản đồ vùng thêm sau khi có dữ liệu hình học hợp lệ.
3. Chọn một mốc lịch sử và khu vực, xem dự báo giờ tiếp theo cùng mô hình được dùng.
4. So sánh giá trị thực với dự báo và hiển thị MAE/RMSE trên tập test.
5. Hiển thị nguồn, khoảng ngày dữ liệu, thời điểm xử lý, phiên bản mô hình và trạng thái HBase.

Chưa ưu tiên đăng nhập, mobile, API thời gian thực, Kafka, Kubernetes, LSTM hoặc tối ưu điều phối xe. Những phần này chỉ mở rộng sau khi sản phẩm cốt lõi và báo cáo hoàn thành.

## 3. Dữ liệu cần tìm và kiểm tra

Nguồn chính: [NYC TLC Trip Record Data](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page). Tải các file Yellow Taxi theo tháng dạng Parquet và Taxi Zone Lookup Table; lấy thêm dữ liệu ranh giới khu vực nếu làm bản đồ. Đọc [từ điển Yellow Taxi](https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_yellow.pdf) trước khi viết quy tắc làm sạch.

Các trường chính cần khảo sát: `tpep_pickup_datetime`, `tpep_dropoff_datetime`, `PULocationID`, `DOLocationID`, `trip_distance`, `passenger_count`. Nhãn đếm chuyến dùng thời điểm đón và khu vực đón; các trường khác phục vụ kiểm tra chất lượng, không mặc định là đầu vào dự báo.

Checklist khảo sát:

- Ghi URL từng file, ngày tải, tên file, SHA256, dung lượng, số dòng và kiểu dữ liệu.
- Kiểm tra schema các tháng; chỉ chọn và ép kiểu các cột cần dùng trước khi hợp nhất.
- Thống kê timestamp thiếu/sai, bản ghi nằm ngoài tháng, mã vùng không có trong danh mục và dữ liệu trùng.
- Không dùng `passenger_count` để đếm chuyến. Không loại chuyến hợp lệ chỉ vì số hành khách bị thiếu.
- Phát hiện trùng nhưng không tự động xóa mọi bản ghi có cùng giờ/vùng: nhiều chuyến hợp lệ có thể trùng các thuộc tính đó. Ghi rõ quy tắc nếu loại bản ghi trùng toàn bộ cột.
- Với các khoảng nguồn dữ liệu đầy đủ, tạo lưới khu vực × giờ và điền 0 cho giờ không có chuyến. Khoảng thiếu file hoặc lỗi thu thập phải đánh dấu thiếu, không biến thành 0.
- Ghi nhận cách xử lý giờ địa phương `America/New_York` và DST. Timestamp nguồn thiếu offset có thể gây nhập nhằng; chọn chính sách rõ ràng và nêu giới hạn, kiểm tra các ngày chuyển giờ.
- Dùng tập vùng hợp lệ cố định từ dữ liệu tham chiếu, hoặc chọn vùng theo tập train; không chọn top vùng dựa trên cả test.

Dung lượng và số dòng chỉ được ghi vào báo cáo sau khi đo thực tế. Không nhân bản file để tuyên bố có thêm dữ liệu thật. Nếu tạo tải tổng hợp để benchmark phải tách riêng và ghi rõ.

Nếu nguồn chính không phù hợp, khảo sát [Citi Bike System Data](https://citibikenyc.com/system-data) như phương án xe đạp công cộng trước khi đổi. Không cần thu thập tất cả các loại phương tiện. Không dùng dữ liệu lịch chạy xe đơn thuần làm nhãn lượt khách.

## 4. Kiến trúc và vai trò công nghệ

```text
NYC TLC Parquet + danh mục khu vực
                 |
                 v
         data/raw (giữ bản gốc)
                 |
                 v
 Spark: đọc -> kiểm tra -> làm sạch -> tổng hợp khu vực/giờ
                 |
                 v
 Parquet sạch + báo cáo chất lượng + đặc trưng quá khứ
                 |
          +------+-----------------+
          |                        |
          v                        v
   Lịch sử theo giờ       Baseline + Spark ML hồi quy
          |                        |
          |              Đánh giá + dự báo + lưu model
          |                        |
          +------------+-----------+
                       v
             HBase qua Thrift gateway
                       |
                       v
          Streamlit đọc lịch sử/dự báo từ HBase
```

Spark chịu trách nhiệm ETL và mô hình. HBase là nơi lưu bảng phục vụ truy vấn theo vùng/thời gian; không phải thư viện học máy. Parquet là định dạng file; HDFS là hệ lưu trữ phân tán nếu được bổ sung. Docker đóng gói môi trường, không tự biến một máy thành cụm phân tán nhiều máy.

Phương án nhẹ ban đầu: Spark local trong container, HBase standalone trong container và dữ liệu gắn volume. [Tài liệu HBase](https://hbase.apache.org/docs/getting-started/) mô tả standalone gộp các daemon trong một JVM và lưu trên filesystem cục bộ. Báo cáo phải ghi đúng chế độ đã chạy; không tuyên bố đã kiểm chứng khả năng chịu lỗi của một cụm phân tán.

Nếu cần HDFS: thêm NameNode/DataNode, chuyển raw/processed vào HDFS và cấu hình `hbase.rootdir` phù hợp; kiểm tra ma trận phiên bản HBase–Hadoop–JDK. Thực hiện ở tuần 3–4, trước khi khóa môi trường, tránh thêm hạ tầng sát ngày nộp.

Thiết kế HBase đề xuất:

| Bảng | Row key | Column family và dữ liệu | Truy vấn chính |
|---|---|---|---|
| `transport:demand_hourly` | `zone_id_padded#hour_key` | `d:trips`, `q:valid`, `m:run_id` | Lịch sử một vùng trong khoảng giờ |
| `transport:forecast_hourly` | `zone_id_padded#target_hour#model_version#origin_hour` | `p:value`, `m:horizon`, `m:run_id` | Dự báo của một vùng tại một thời điểm |
| `transport:zone_summary` | `period_key#zone_id_padded` | `d:trips`, `d:rank` | Top vùng theo ngày/tháng |

`hour_key` phải có dạng cố định, sắp xếp thời gian đúng và chính sách múi giờ thống nhất. Cố định độ dài mã vùng để scan ổn định. Chỉ số dạng số cần quy ước encoding đọc/ghi đồng nhất. Lưu mô hình ở `artifacts/models`, không nhét toàn bộ model vào HBase.

Viết batch có kích thước giới hạn, row key xác định để chạy lại không nhân đôi kết quả. Với Spark, ghi theo partition và mở kết nối trong worker; không `collect()` toàn bộ dữ liệu thô về driver. Dashboard dùng scan có giới hạn và bảng tổng hợp, không full scan toàn bộ lịch sử mỗi lần chọn bộ lọc.

Cầu nối đề xuất là HappyBase qua Thrift 1; cần kiểm tra transport/protocol khớp gateway và thử put/get/scan ngay tuần 2. [Tài liệu HappyBase](https://happybase.readthedocs.io/en/latest/api.html) mô tả transport và protocol. Nếu thử nghiệm không tương thích phiên bản đã chọn, sửa cầu nối trước khi viết ETL đầy đủ.

## 5. Mô hình và đánh giá đúng bài toán dự báo

Baseline bắt buộc để có mốc so sánh: lấy số chuyến của cùng khu vực, cùng giờ, cùng thứ tuần trước. Với trường hợp thiếu lịch sử, dùng giá trị trung bình từ tập train và ghi số lần phải dùng fallback.

Mô hình đầu tiên: `RandomForestRegressor` trong Spark ML; mở rộng `GBTRegressor` nếu còn thời gian. Không cần thử quá nhiều mô hình.

Định nghĩa đặc trưng tại thời điểm kết thúc giờ t để dự báo y(t+1):

- Số chuyến y(t), y(t−1), y(t−23), y(t−167).
- Trung bình các giờ đã quan sát trong 24 giờ và 7 ngày gần nhất.
- Giờ/thứ của t+1, cuối tuần, mã khu vực được mã hóa như biến phân loại.
- Tùy chọn lịch ngày lễ đã biết trước. Thời tiết chỉ thêm khi có nguồn và phân biệt dự báo thời tiết với thời tiết thực quan sát sau thời điểm dự báo.

Không dùng giá tiền, số chuyến hoặc dữ liệu kết thúc của giờ tương lai để tạo đặc trưng. Viết kiểm tra bằng chuỗi nhỏ biết trước để xác nhận cửa sổ không nhìn tương lai.

Chia dữ liệu đề xuất khi đã đủ 6 tháng: tháng 1–4 train, tháng 5 validation, tháng 6 test. Cắt theo timestamp thực tế, không theo tên file đơn thuần. Chọn tham số trên validation; chỉ đánh giá test sau khi chốt mô hình. Các bước học encoder, điền thiếu hoặc chọn vùng phải fit trên train.

Trong đánh giá một bước theo thời gian, được dùng giá trị thật của các giờ test đã kết thúc để dự báo giờ kế tiếp, đúng giả định vận hành. Không được dùng giá trị thật tương lai để vẽ một lượt dự báo 24 giờ. Dự báo 24 giờ là tính năng mở rộng riêng, cần mô hình nhiều horizon hoặc đệ quy được đánh giá riêng.

Đo MAE và RMSE trên cùng các điểm hợp lệ cho baseline và mô hình. Có thể bổ sung WAPE khi tổng số chuyến thực > 0. Tránh dùng MAPE làm độ đo chính vì nhiều vùng/giờ có nhãn 0. Nếu chặn dự báo âm về 0 thì áp dụng thống nhất khi đánh giá và phục vụ.

Báo cáo thêm sai số theo giờ cao điểm, từng vùng và vùng ít chuyến. Ghi seed, tham số, khoảng dữ liệu, thời gian train, phần cứng và mã phiên bản. Mục tiêu là cải thiện baseline; nếu không cải thiện vẫn báo cáo trung thực, phân tích nguyên nhân và có thể chọn baseline làm mô hình phục vụ.

## 6. Kế hoạch 10 tuần với đầu ra kiểm tra được

Tuần dưới đây là tuần môn học; điều chỉnh theo lịch thực tế của lớp. Đưa khảo sát dữ liệu lên sớm vì mô hình phụ thuộc dữ liệu.

| Tuần | Công việc | Hiếu phụ trách chính | Khang phụ trách chính | Điều kiện hoàn thành |
|---|---|---|---|---|
| 1 | Chốt bài toán, dữ liệu, repo và lịch | Khảo sát HBase/Docker | Khảo sát TLC, viết phạm vi | Có đề cương, kế hoạch, repo và phân công |
| 2 | Thử môi trường và 1 tháng dữ liệu | HBase put/get/scan, volume | Đọc Parquet, thống kê schema | Hai máy theo hướng dẫn chạy được thử nghiệm nhỏ |
| 3 | ETL và bảng theo giờ | Spark ETL, schema HBase | EDA, quy tắc dữ liệu, baseline | Có dữ liệu sạch, thống kê loại/giữ và baseline |
| 4 | Luồng từ dữ liệu đến màn hình | Ghi HBase, đọc theo khoảng | Dashboard lịch sử, đặc trưng | Chọn vùng và xem dữ liệu thật từ HBase |
| 5 | Bản giai đoạn 1 | Đo ETL, lưu cấu hình | Hồi quy đầu tiên, metrics | Có demo, báo cáo tiến độ, bảng baseline/mô hình |
| 6 | Nộp theo lịch GV, sửa phản hồi | Mở rộng đủ dữ liệu, tối ưu batch | Validation, kiểm tra leakage | Ghi phản hồi và hoàn thành sửa ưu tiên |
| 7 | Hoàn thiện dự báo | Tự động chuỗi job, chạy lại an toàn | Trang dự báo và sai số | Luồng train/predict/store/view hoàn chỉnh |
| 8 | Khóa tính năng, đánh giá cuối | Kiểm thử clone trên máy khác | Test cuối, biểu đồ, bản nháp Word | Máy Hiếu hoặc Khang tái lập kết quả được |
| 9 | Nộp giai đoạn 2 | Đóng gói code, hướng dẫn, kiểm tra dữ liệu | Hoàn thiện Word, PPT, demo dự phòng | Đủ bộ hồ sơ nộp Classroom |
| 10 | Thuyết trình và phản biện | Kiến trúc, HBase, pipeline | Dữ liệu, mô hình, dashboard | Hai người đều chạy và giải thích toàn hệ thống |

Mỗi tuần họp ngắn 2 lần: đầu tuần chốt việc, cuối tuần chạy demo và cập nhật nhật ký. Người còn lại review PR, không chỉ review phần mình phụ trách. Mỗi thành viên viết phần báo cáo liên quan ngay khi hoàn thành thực nghiệm.

Nếu đã gần hạn: ưu tiên một nguồn dữ liệu, một horizon, baseline + một mô hình, dashboard hai trang, HBase có dữ liệu thật và hồ sơ đầy đủ. Giảm phạm vi bản đồ và tuning trước khi giảm phần đánh giá hoặc báo cáo.

## 7. Viết báo cáo, slide và chuẩn bị demo

Giữ cấu trúc quy định trong file môn học:

1. Trang bìa: môn, tên đăng ký, phạm vi thực nghiệm, giảng viên, nhóm, MSSV.
2. Lịch làm việc nhóm hằng tuần.
3. Công việc và đóng góp từng thành viên, dẫn chứng task/commit/PR.
4. Mục lục.
5. Giới thiệu: bối cảnh, mục tiêu, phạm vi, đầu vào/đầu ra.
6. Cơ sở lý thuyết: Big Data, Spark, HBase, row key, hồi quy, baseline, độ đo.
7. Xây dựng ứng dụng và trực quan hóa: nguồn và chất lượng dữ liệu, kiến trúc, môi trường, schema, ETL, mô hình, thực nghiệm, đánh giá, dashboard.
8. Kết luận và định hướng phát triển: kết quả đạt, giới hạn, việc có thể mở rộng.
9. Tài liệu tham khảo: nguồn dữ liệu, tài liệu công nghệ, thuật toán; có URL và ngày truy cập.
10. Phụ lục: cách chạy, tham số, bảng kết quả bổ sung nếu cần.

Gợi ý nhóm tự đặt: khoảng 20–30 trang nội dung và 10–15 slide, không phải định mức giảng viên đã yêu cầu. Điều chỉnh theo mẫu và thời lượng GV giao. Không điền kết quả hoặc số liệu giả vào báo cáo.

Kịch bản demo gợi ý 5–7 phút, điều chỉnh theo thời lượng được giao: nêu bài toán → chỉ dữ liệu và log xử lý → chứng minh bảng HBase có dữ liệu → xem lịch sử vùng → dự báo một giờ → so sánh baseline → nêu hạn chế. Chuẩn bị ảnh/video dự phòng, nhưng demo thật là chính.

## 8. Tiêu chí nghiệm thu cuối cùng

- [ ] Có nguồn dữ liệu hợp lệ, thông tin tải lại và quy mô thực tế.
- [ ] Một chuỗi lệnh tái lập ETL, train, evaluate, publish kết quả.
- [ ] Chạy lại cùng đầu vào không làm nhân đôi số đếm hoặc bản ghi kết quả.
- [ ] Kiểm tra dữ liệu thiếu/0, timestamp, mã vùng và đặc trưng tránh leakage.
- [ ] HBase lưu lịch sử/dự báo; dashboard thực sự đọc qua lớp storage.
- [ ] Restart container vẫn còn dữ liệu đã lưu trong volume.
- [ ] Baseline và mô hình được đánh giá trên cùng tập test theo thời gian.
- [ ] Có log số dòng, thời gian ETL/train, phiên bản và tham số.
- [ ] Dashboard rõ đơn vị, ngày dữ liệu, mô hình, lỗi kết nối và trạng thái thiếu dữ liệu.
- [ ] Hiếu và Khang đều clone repo và làm theo README để chạy được.
- [ ] Đủ Source Code, Word, PPT, hướng dẫn, liên kết dữ liệu và nhật ký nhóm.

## 9. Những chủ đề cần tìm hiểu theo thứ tự

1. Git branch/PR và Python venv; Parquet và schema của TLC.
2. Spark DataFrame: đọc Parquet, ép kiểu, groupBy theo giờ, window/lag, partition.
3. HBase: table, column family, row key, scan, batch put, ZooKeeper, Thrift.
4. Dự báo chuỗi thời gian: seasonal baseline, cắt train/test theo thời gian, leakage.
5. Spark ML Pipeline: mã hóa vùng, Random Forest, GBT, đánh giá hồi quy.
6. Streamlit và Plotly: bộ lọc, biểu đồ, cache có hạn, truy vấn HBase.
7. Docker Compose: network, volume, healthcheck, log và khóa phiên bản.

Các nguồn kỹ thuật đã đối chiếu ngày 05/10/2026: [Spark 3.5.7](https://spark.apache.org/docs/3.5.7/), [HBase](https://hbase.apache.org/docs/getting-started/), [HappyBase](https://happybase.readthedocs.io/en/latest/api.html), [VSCode Python](https://code.visualstudio.com/docs/python/environments), [Docker Windows](https://docs.docker.com/desktop/setup/install/windows-install/). Kiến trúc và phân công là đề xuất của kế hoạch, không phải yêu cầu nguyên văn của các nguồn này.
