# Nhật ký quyết định

## Quyết định 014 — Mô hình và dự phòng giai đoạn 4 (08/10/2026)

Người dùng đã trả lời “Duyệt baseline + Random Forest và chính sách dự phòng”. Triển khai seasonal naive cùng giờ tuần trước và Random Forest trong Spark. So sánh lịch sử 2024 với 2023–2024 trên ba fold cuối 2024 theo temporal_splits.json; khóa lựa chọn trước khi tính sai số 2025.

Đặc trưng chỉ dùng nhãn giờ quá khứ hợp lệ. Thiếu do DST/nguồn không được đổi thành 0: RF dùng baseline khi đầu vào chưa đầy đủ; baseline thiếu dùng trung bình vùng chỉ học trên train của fold, rồi trung bình toàn train nếu cần. Đếm và công bố các lượt dự phòng; đo toàn hệ thống trên cùng mọi nhãn hợp lệ, đồng thời báo riêng phần đủ đặc trưng. Chi tiết, tham số khởi đầu và nghiệm thu ở [MO_HINH.md](MO_HINH.md).

Phát hiện chuẩn bị: image ETL chưa có NumPy, Spark ML yêu cầu thư viện này. Tạo image mở rộng từ image hiện có với numpy 1.26.4 cho Python 3.11, không thay image/bằng chứng giai đoạn 3. Dữ liệu, model và file tạm gắn thư mục D.

Cập nhật nghiệm thu 08/10/2026: 12 lượt validation đã khóa RF 20 cây/depth 12 với lịch sử B (2023–2024). MAE validation 3,508892 so với 3,530719 của RF tốt nhất chỉ dùng 2024, lợi ích lịch sử bổ sung khoảng 0,62%, chưa kiểm định ý nghĩa thống kê. Test 2025 đủ 2.291.256 nhãn: MAE 3,851490 so với baseline 5,320124; không đổi lựa chọn sau khi thấy test. Model lưu/nạp lại và 27 tests/5 nhóm Spark window đạt. Xem [tổng kết giai đoạn 4](tong-ket/TONG_KET_GIAI_DOAN_4.md).

## Quyết định 012 — Thử ghi dữ liệu giờ vào HBase, ngày 07/10/2026

Người dùng trả lời “Duyệt phương án thử 168 giờ”: dùng bảng `transport_demand_hourly_trial_v1`, khóa vùng 3 chữ số + nhãn giờ, families d/q/m, null không thành 0. Mẫu vùng 161 trong 01–07/01/2024 giúp kiểm chứng luồng và ghi lặp trước khi mở rộng. Thiết kế và kết quả tại LICH_SU.md#thiet-ke-hbase-thu. Chưa phê duyệt nạp toàn bộ dataset hoặc dùng bảng thử làm schema ứng dụng cuối cùng.

## Quyết định 011 — Cấu hình Spark thử đã duyệt, ngày 07/10/2026

Người dùng đồng ý PySpark 3.5.7, Python 3.11, Java 17 trong Docker; local[2], driver 2 GiB và container giới hạn 4 GiB. Thử một tháng trước khi mở rộng để đối chiếu quy tắc đã nghiệm thu. Đã chạy tháng 01/2024 thành công, không thay đổi chính sách dữ liệu. Xem LICH_SU.md#giai-doan-3 và docs/VAN_HANH.md. Chưa chốt schema HBase chính thức hoặc quy mô nạp dữ liệu thật trong bước thử này.

## Quyết định 010 — Python Windows có chữ ký, ngày 07/10/2026

Người dùng xác nhận máy cá nhân, Smart App Control On và đồng ý cài Python 3.13 chính thức ngoài dự án để thử trước khi thay venv. Python 3.14 hiện có được giữ; PyArrow 19 hỗ trợ đến 3.13 nên chưa dùng 3.14 cho bộ thư viện hiện tại. Đã kiểm tra checksum/chữ ký bộ cài Python 3.13.16, cài theo tài khoản, không đổi PATH. Venv thử chạy được và đạt 15 kiểm thử; HappyBase đọc danh sách bảng HBase thành công sau khi bổ sung setuptools 80.9.0 (HappyBase 1.2.0 cần pkg_resources). Sau đó tạo lại `.venv` ở đúng đường dẫn, giữ bản cũ trong `.tools/venv311-blocked-backup/`.

Không tắt Smart App Control. Các phiên bản đã thử được lưu trong requirements/requirements-stage3-windows.txt; chưa xác nhận toàn bộ dashboard hoặc Spark chạy trên Python 3.13. Không còn áp dụng yêu cầu xóa project là xóa Python nền cho môi trường Windows mới; người dùng đã đồng ý thay đổi này. Xem CAI_DAT.md mục môi trường hiện hành.

## Quyết định 001 — Phạm vi khảo sát ban đầu

Trạng thái: người dùng đã đồng ý trong cuộc trao đổi ngày 05/10/2026.

- Chọn nguồn Yellow Taxi NYC TLC.
- Bắt đầu với tháng 01/2024 để khảo sát dữ liệu và kiểm tra môi trường.
- Mục tiêu dự kiến: dự báo số chuyến đón khách theo khu vực trong giờ tiếp theo.
- Lý do: đề tài cho phép taxi; nguồn có thời gian đón và mã khu vực; bắt đầu một tháng giúp kiểm tra trước khi mở rộng.
- Giới hạn: số chuyến đã phục vụ là nhu cầu quan sát được, không phải toàn bộ nhu cầu gọi xe; không suy rộng kết quả sang Việt Nam.

Chưa chốt: số tháng dùng cho mô hình, quy tắc làm sạch, môi trường xử lý thực tế, mô hình và tham số. Các lựa chọn trong kế hoạch tổng thể vẫn là đề xuất cho đến khi người dùng duyệt.

## Cách làm việc đã thống nhất

Trước mỗi quyết định về dữ liệu, làm sạch, công nghệ hoặc mô hình: nêu vấn đề, các phương án, lý do đề xuất và chờ người dùng chốt trước khi triển khai. Khảo sát phải giữ nguyên dữ liệu gốc; thống kê vấn đề không đồng nghĩa với quyết định loại bản ghi.

## Quyết định 015 — Dashboard giai đoạn 5 có số thực tế kiểm chứng

Ngày 08/10/2026, người dùng yêu cầu “bám sát yêu cầu của file kế hoạch, dự đoán có số liệu để kiểm chứng là oke” và cho phép triển khai giai đoạn 5. Tham khảo dashboard nền tối đã gửi, giữ nguồn 36 tháng và model giai đoạn 4. Không tải 2026, không sửa mô hình hoặc chính sách dữ liệu.

Streamlit theo kiến trúc kế hoạch; 5 trang Tổng quan, Bản đồ, Phân tích vùng, Dự báo & kiểm chứng, Dữ liệu & mô hình. Dự báo một giờ năm 2025 được tính sẵn từ model đã kiểm tra tải lại, nạp vào bảng HBase riêng; dữ liệu thực tế đọc riêng để đối chiếu. Hiển thị rõ phát lại lịch sử, thời gian snapshot và phương án dự phòng; không giả thời gian thực hoặc accuracy phân lớp.

Chi tiết kỹ thuật phục vụ trong phạm vi được duyệt: bảng forecast khóa vùng/giờ đích/model/horizon, nhóm p/q/m, max_versions=1; bảng tổng hợp ngày/tháng có khóa thời gian/vùng để tránh quét toàn lưới trong mỗi lần lọc. Giữ bảng lịch sử nguyên trạng, bật WAL, đối chiếu đầy đủ sau ghi. Xem [DASHBOARD.md](DASHBOARD.md).

Hai video TikTok không truy cập được, đã báo người dùng. Chưa coi các yêu cầu chưa xem được trong video là đã đáp ứng. Áp dụng và kiểm tra các yêu cầu giao diện đã mô tả trong trao đổi: chữ/đơn vị rõ, loading/error/empty, zero/null, nhãn mô phỏng, phạm vi độ đo và màn hình nhỏ.

## Quyết định 002 — Python riêng trong thư mục dự án

Người dùng đã đồng ý Python 3.11 và yêu cầu có thể xóa cùng dự án. Vì venv cần Python nền, đặt bản CPython độc lập trong `.python/` rồi tạo `.venv/` từ bản đó. Công cụ uv được tải vào `.tools/`, cache chỉ định tại `.uv-cache/`; không đăng ký Python vào Windows registry hoặc thêm executable vào PATH toàn máy.

Bản đã cài: CPython 3.11.17, lấy qua uv 0.12.23 từ Astral python-build-standalone. Các thư mục môi trường được Git bỏ qua. Xóa cả thư mục dự án sẽ xóa các thành phần cục bộ này; chỉ xóa `.venv` thì Python nền trong `.python` vẫn còn. Docker container/volume nằm ngoài dự án, không tự mất khi xóa thư mục dự án.

Phạm vi mở rộng dữ liệu chưa được duyệt. Một tháng phục vụ khảo sát và kiểm tra pipeline, không được coi là đủ để kết luận về tính mùa vụ theo năm.

## Quyết định 003 — Khảo sát bằng PyArrow

Người dùng đã đồng ý cài PyArrow và khảo sát file gốc theo lô. Đã cài PyArrow 19.0.1 trong `.venv`; phiên bản được lưu ở `requirements/requirements-profile.txt`. Chỉ thống kê dữ liệu, không xóa dòng, điền thiếu hoặc sửa giá trị. Phạm vi dataset cuối cùng sẽ được thống nhất sau thử nghiệm.

## Quyết định 004 — Giới hạn thời điểm đón cho tập thử tháng 01/2024

Người dùng đồng ý và yêu cầu tiếp tục sau khi đã giải thích 18 dòng ngoài tháng. Áp dụng khoảng `[2024-01-01, 2024-02-01)` theo thời điểm đón, giữ nguyên timestamp nguồn. Lý do: nhu cầu được định nghĩa theo giờ đón. Không giới hạn thời điểm trả trong cùng tháng.

Đã chạy thử bằng PyArrow: 2.964.606 dòng trong tháng và 18 dòng cách ly có lý do. File raw không thay đổi; SHA256 đã đối chiếu trước/sau. Đây là kết quả trung gian, chưa phải bộ dữ liệu sạch cuối cùng. Quy tắc khác chưa được duyệt. Code dừng nếu gặp timestamp đón null để tránh tự quyết định thêm quy tắc cho dữ liệu mới.

## Quyết định 005 — Đối chiếu danh mục vùng

Người dùng đồng ý tải Taxi Zone Lookup chính thức và đối chiếu trước, chưa loại dòng. Đã tải ngày 05/10/2026 và kiểm tra PULocationID trên tập trong tháng. Kết quả tại `LICH_SU.md#kiem-tra-ma-vung`: 10.360 chuyến mã 264, 1.658 chuyến mã 265; không có mã null hoặc không có trong danh mục. Đề xuất tách hai nhóm này khỏi tập dự báo vùng cụ thể đang chờ người dùng duyệt. Chưa thay đổi dữ liệu.

## Quyết định 006 — Tách riêng mã vùng 264 và 265

Người dùng đã đồng ý tách 12.018 chuyến mã 264/265 khỏi tập ứng viên dự báo vùng cụ thể, vẫn lưu các chuyến đó cho thống kê. Lý do: không xác định được một khu vực cụ thể; không tự suy diễn vùng đón từ vùng trả. Giữ mã 1 Newark Airport.

Đã thực hiện: `data/interim/pickup_zones_2024-01/zone_candidates.parquet` có 2.952.588 dòng; `unspecified_zones.parquet` có 12.018 dòng và lý do riêng theo mã. SHA256 đầu vào trước/sau giống nhau; chưa xử lý tiền âm, thời lượng, số hành khách hoặc quãng đường. Cả 5 kiểm thử hiện tại thành công.

## Quyết định 007 — Hoàn tất tập thử v1 và hướng mở rộng

Ngày 06/10/2026, người dùng duyệt triển khai phương án đã trình bày: cách ly thời lượng không dương; giữ các bất thường khác kèm cờ, không tự sửa giá trị. Đã xuất 2.951.871 dòng thử nghiệm, 717 dòng cách ly và bảng ảnh hưởng theo vùng/giờ. Xem `DU_LIEU_THU_NGHIEM_V1.md`. Trạng thái này thay thế các đề xuất chờ duyệt trước đó.

Đã duyệt hướng 2024–2025, triển khai theo giai đoạn: hoàn thiện tháng 1, phát triển với 2024 và đánh giá tương lai với 2025. Không giới hạn kỹ thuật ở hai năm; thêm năm 2023 hoặc lịch sử dài hơn chỉ khi thử nghiệm validation chứng minh lợi ích và được thống nhất. Hiện chưa tải các tháng/năm bổ sung.

## Quyết định 008 — Bổ sung toàn bộ năm 2023

Người dùng yêu cầu thêm năm 2023 ngay để chuẩn bị kịch bản so sánh đã bàn và xử lý dữ liệu để sử dụng. Đã tải đủ 12 tháng từ TLC, áp dụng cùng quy tắc v1 và chuẩn hóa schema không làm mất giá trị. Kết quả giữ 37.909.554 dòng; dữ liệu raw và mọi nhóm cách ly được giữ lại. Xem `LICH_SU.md#du-lieu-2023`.

Đây là phê duyệt mở rộng dữ liệu, chưa phải bằng chứng rằng thêm lịch sử cải thiện mô hình. Tập so sánh vẫn cần phần 2024 đầy đủ; 2025 dành cho kiểm tra cuối. Chưa tải thêm các tháng 2024/2025 trong lần bổ sung 2023 này.

## Quyết định 009 — Hoàn thiện dữ liệu giai đoạn 2

Cập nhật 07/10/2026: theo yêu cầu hoàn thành giai đoạn 2, đã tải và xử lý đủ 2024–2025 cùng 2023. Các trạng thái chưa tải ở mục trước là lịch sử. Giữ nguyên chính sách v1, không tự loại trùng hoặc sửa tiền âm. Chuẩn hóa thêm cột cbd_congestion_fee xuất hiện năm 2025; các năm không có trường này nhận null khi đọc chung.

Người dùng đã trả lời “Đồng ý chính sách bảo thủ này”: giữ chuyến trên hai ngày đổi giờ mỗi năm cho mô tả, che toàn bộ nhãn hai ngày đó khi học/đánh giá; nếu cả nguồn không có bản ghi trong giờ thì để thiếu, chỉ điền 0 cho vùng không có chuyến được giữ khi nguồn có bản ghi trong giờ. Lý do: timestamp không có UTC offset nên không thể khôi phục chính xác giờ lặp.

Cấu hình thực nghiệm lưu tại configs/temporal_splits.json: A bắt đầu 2024, B bắt đầu 2023; cùng ba fold validation tháng 10–12/2024 và holdout 2025. Đây là cấu hình để triển khai kịch bản so sánh, chưa phải kết luận mở rộng lịch sử giúp dự báo tốt hơn. Hướng dẫn hiện hành: DU_LIEU.md.

## Quyết định 013 — Giai đoạn 3 trên toàn bộ dữ liệu (07/10/2026)

Người dùng yêu cầu “hoàn thành toàn bộ giai đoạn 3 theo mục tiêu”, sau khi thống nhất Spark xử lý đủ 36 tháng 2023–2025 và HBase lưu đủ lưới 6.917.952 vùng–giờ. Các kiểm thử tháng 01/2024 và 168 giờ trước đây là tiền đề, chưa đáp ứng nghiệm thu đầy đủ.

Giữ quy tắc làm sạch/DST/zero/null đã duyệt. Spark đọc từng tháng để tránh xung đột schema và giới hạn RAM, chuẩn hóa kiểu dữ liệu, đối chiếu cờ chất lượng, tổng hợp và tạo lại lưới giờ. Giữ 126.994.028 chuyến chi tiết trong Parquet; bảng HBase ứng dụng `transport_demand_hourly_v1` lưu kết quả vùng–giờ phục vụ truy vấn, dùng cùng khóa `ZZZ#YYYYMMDDHH`, nhóm cột d/q/m và max_versions=1 như mẫu đã duyệt. Không đưa chuyến chi tiết vào HBase vì truy vấn ứng dụng cần số đếm theo giờ, không cần tra cứu từng cuốc xe.

Nghiệm thu gồm hai lượt nạp đầy đủ, đọc đối chiếu từng ô sau mỗi lượt, kiểm tra range/point query qua ranh giới năm và ngày DST; sau đó dừng sạch, sao lưu volume và phục hồi vào volume mới để đối chiếu lại toàn bộ. Không coi phép thử restart là thay thế cho backup/restore. Các nguồn và đầu ra giai đoạn 2 được giữ nguyên.
