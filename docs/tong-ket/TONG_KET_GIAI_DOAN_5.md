# Tổng kết giai đoạn 5 — Dashboard và kiểm chứng dự báo

Ngày hoàn thành: 08/10/2026. Trạng thái: **hoàn thành theo phạm vi demo lịch sử một giờ đã duyệt**. Bằng chứng: [stage5_acceptance.json](../../artifacts/metrics/stage5_acceptance.json).

## 1. Mục tiêu và phạm vi

Tạo Web có dữ liệu thật, phân tích theo thời gian/khu vực, hiển thị dự báo và có số thực tế để kiểm chứng. Giữ dataset Yellow Taxi 2023–2025, model giai đoạn 4 và chính sách dữ liệu đã duyệt. Không huấn luyện lại, không mở rộng 2026/horizon, không giả nguồn trực tiếp.

## 2. Công việc đã thực hiện

- Cài và khóa môi trường Streamlit/Plotly trên Python Windows 3.13; pip check đạt, giữ các thư viện đã khóa của giai đoạn 4.
- Xây 5 trang nền tối: Tổng quan, Bản đồ, Phân tích vùng, Dự báo & kiểm chứng, Dữ liệu & mô hình. Có bộ lọc, CSV, tooltip/zoom biểu đồ, trạng thái đang tải/lỗi và thông tin phiên bản.
- Tạo snapshot phục vụ từ Parquet đã nghiệm thu, kiểm tra checksum. Giữ riêng dự báo và số thực tế; lưu mode historical_replay, model version, origin hour, horizon 1 và thời gian tạo thật.
- Nạp toàn bộ dự báo 2025 và tổng hợp ngày/tháng vào bảng HBase riêng. Không sửa/xóa bảng lịch sử.
- Tải ranh giới chính thức TLC, chuyển CRS sang EPSG:4326, kiểm tra đủ 263 vùng. Dùng bản đồ SVG để ổn định trên màn hình nhỏ.
- Kiểm tra giá trị theo bộ lọc bằng nguồn Parquet độc lập; kiểm tra hai ngày DST, dự phòng và ranh giới năm. Đối chiếu toàn bộ bảng sau ghi và đọc lại toàn bộ sau khi HBase bật lại.
- Thử 5 trang bằng trình duyệt thật, mở nhãn đối chiếu, chọn ngày qua ô ngày/tháng, tải CSV, điều hướng điện thoại, kiểm tra 390px/320px. Kiểm thử lỗi endpoint riêng không dừng HBase thật.

## 3. Kết quả đạt được

| Cấp dữ liệu | Số dòng | Ý nghĩa |
|---|---:|---|
| Chuyến đã làm sạch | 126.994.028 | Chuyến chi tiết còn nguyên trong Parquet |
| Lưới vùng–giờ | 6.917.952 | Dữ liệu lịch sử theo giờ từ giai đoạn 2–3 |
| Dự báo hợp lệ năm 2025 | 2.291.256 | RF và dự phòng; không gồm nhãn DST/thiếu |
| Tổng hợp vùng–ngày | 288.248 | 1.096 ngày × 263 vùng |
| Tổng hợp vùng–tháng | 9.468 | 36 tháng × 263 vùng |
| Tổng bảng tổng hợp phục vụ | 297.716 | Hai loại tổng hợp trên, không phải số chuyến được giữ |

Hai bảng phục vụ đối chiếu từng khóa/ô: **0 sai lệch**, cả lần đầu và lần đọc lại sau khởi động HBase. Tổng số đếm từ 9.468 tổng hợp tháng bằng **126.994.028**. Truy vấn 3.682 tổng hợp ngày qua năm khớp snapshot; 6 trường hợp dự báo/nhãn/metric khớp nguồn. 36 unit tests đạt, 0 lỗi/0 thất bại; pip check không có xung đột. Model giữ nguyên checksum giai đoạn 4.

Ví dụ demo thật: vùng 161, 07/01/2025, 12:00; dự báo 244,67 lượt, baseline 211, thực tế 299, sai số tuyệt đối 54,33 lượt (làm tròn chỉ để hiển thị). Đây là một điểm, không thay thế kết quả toàn test MAE 3,851, RMSE 11,753 và WAPE 18,458%. Các độ đo vùng/ngày được tính lại trên đúng các nhãn hợp lệ; chỉ số toàn test nằm riêng.

Thời gian đo bước phục vụ: Prepare 69,55 giây; nạp forecast 177,67 giây; nạp tổng hợp 8,72 giây; đối chiếu forecast ban đầu 103,23 giây, tổng hợp 6,15 giây. Đây là lần chạy máy hiện tại, không phải SLA hay benchmark đa người dùng. Thời gian trang trong browser report có cả thời gian chờ cố định để chụp/kiểm tra, không dùng làm độ trễ chuẩn.

## 4. Đầu ra và kiểm chứng

| Đầu ra | Vai trò | Bằng chứng |
|---|---|---|
| [src/dashboard](../../src/dashboard/) | Giao diện, truy vấn giới hạn, chuẩn bị snapshot, đối chiếu/nghiệm thu | 36 tests; kiểm thử trình duyệt |
| [run_stage5.ps1](../../scripts/run_stage5.ps1) | Prepare/Geometry/Load/Verify/App | Đã chạy với môi trường thật |
| [stage5_dashboard.json](../../configs/stage5_dashboard.json) và [.streamlit](../../.streamlit/) | Bảng, model, giới hạn, theme/localhost | Cấu hình được ghi checksum |
| [requirements/requirements-stage5-windows-lock.txt](../../requirements/requirements-stage5-windows-lock.txt) | Tái lập môi trường | pip check đạt |
| data/processed/dashboard_v1 | Snapshot dự báo/tổng hợp, không push | stage5_prepared.json |
| data/reference/taxi_zones.geojson | Bản đồ 263 vùng, không push | stage5_geometry.json |
| [stage5_storage.json](../../artifacts/metrics/stage5_storage.json) | Toàn bộ lần nạp và đối chiếu | 2.291.256 + 297.716 dòng, 0 sai lệch |
| [stage5_storage_recheck.json](../../artifacts/metrics/stage5_storage_recheck.json) | Kiểm tra chỉ đọc sau khi HBase bật lại | Toàn bộ khóa/ô khớp |
| [stage5_queries.json](../../artifacts/metrics/stage5_queries.json) | Số thực tế, metric và tổng hợp | 6 cases + ngày/tháng đạt |
| [stage5_browser.json](../../artifacts/metrics/stage5_browser.json) | Luồng UI thật | 5 trang, DST/dự phòng/CSV/mobile đạt, không page error |
| [stage5_error_state.json](../../artifacts/metrics/stage5_error_state.json) | HBase không kết nối | Lỗi rõ, không dữ liệu giả/exception UI |
| [DASHBOARD.md](../DASHBOARD.md) | Chạy lại, kịch bản demo và giới hạn | Hướng dẫn cho máy hiện có/máy clone |

## 5. Quyết định và lý do

Theo [quyết định 015](../QUYET_DINH.md#quyết-định-015--dashboard-giai-đoạn-5-có-số-thực-tế-kiểm-chứng), người dùng duyệt Web bám kế hoạch và có số thực tế kiểm chứng. Phục vụ dự báo tính sẵn vì model đã nghiệm thu/tải lại, tránh mở Spark cho mỗi lần chọn giờ. HBase lưu kết quả đã tính và số thực tế ở bảng riêng; không đưa nhãn vào payload dự báo.

Tổng hợp nhỏ và cache 300 giây tránh quét toàn bộ lưới theo giờ. Chưa thêm Redis: chạy một tiến trình demo, đã có cache; chỉ cân nhắc cache dùng chung khi cần nhiều tiến trình/người dùng và đo thấy nút thắt. Redis không cải thiện độ chính xác dự báo.

## 6. Vấn đề và giới hạn

- Streamlit 1.49.1 xung đột packaging 26.3; chuyển sang 1.65.0 sau khi kiểm tra metadata, giữ nguyên lock giai đoạn 4. Bản đồ WebGL có Map error khi đổi kích thước; đổi sang SVG, kiểm tra đủ polygon và không còn lỗi trình duyệt.
- Một lượt test đầu gặp quyền thư mục Temp của sandbox; chuyển Temp kiểm thử vào .tools trên D, bộ test đạt. Lỗi selector checkbox/date trong tự động hóa được sửa để thao tác label và ô spinbutton hiển thị thật, không dùng input native ẩn.
- HBase có lúc dừng trong phiên làm việc; đã bật lại volume hiện có và đọc đối chiếu toàn bộ hai bảng phục vụ. Không nhận là đã benchmark chịu lỗi cụm phân tán.
- Demo lịch sử, dự báo một giờ; chưa trực tiếp, chưa 2026, chưa dự báo nhiều bước/khoảng tin cậy/điều phối số xe. Không train lại hoặc sửa model theo kết quả test.
- Hai video TikTok không truy cập được: đã báo người dùng, không tuyên bố đạt các lỗi cụ thể chưa xem. Đã kiểm tra các yêu cầu UI rõ ràng được mô tả trong trao đổi.
- Dữ liệu/model/volume không nằm trong Git; máy clone phải làm các giai đoạn chuẩn bị theo hướng dẫn. Nếu nguồn mới cần phiên bản và nghiệm thu mới, không ghi đè bằng chứng cũ.

## 7. Công việc của giai đoạn 6

Ứng dụng chạy tại http://127.0.0.1:8501. HBase volume giữ lịch sử, dự báo, tổng hợp. Code, config, lock, metrics và hướng dẫn có thể đưa lên Git; không tự commit/push.

Giai đoạn 6 còn: viết báo cáo Word cuối kỳ theo yêu cầu môn học, PPT, sơ đồ kiến trúc, ảnh/chứng cứ demo, đối chiếu rubric, thông tin đóng góp được xác nhận, hướng dẫn và kiểm tra bộ nộp trên máy khác. Không coi Word giải thích đã tạo rồi xóa ở cuộc trao đổi trước là báo cáo cuối kỳ đã nộp. Chỉ bổ sung tính năng lớn nếu được chốt riêng.

## Lịch sử cập nhật

- 08/10/2026: nghiệm thu giai đoạn 5 sau đối chiếu lại HBase và kiểm thử Web.
- 08/10/2026: bổ sung Light/Dark native qua menu ⋮, cấu hình cả hai nền và màu biểu đồ nhất quán; sidebar bổ sung phạm vi dữ liệu, chỉ số kiểm chứng và hướng dẫn nhanh. Kiểm tra bổ sung ghi trong mục `appearance` của `stage5_browser.json`; dữ liệu và mô hình giữ nguyên.
- 09/10/2026: gom lock/danh sách thư viện Windows vào `requirements/`, giữ điểm cài đặt `requirements.txt`, bỏ hai danh sách bổ sung stage 4/5 trùng chức năng với lock. Cập nhật đường dẫn trong tài liệu và công cụ kiểm chứng; nội dung lock, phiên bản, dữ liệu và model giữ nguyên.
