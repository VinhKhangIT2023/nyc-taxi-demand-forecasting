# Giai đoạn 5 — Dashboard và kiểm chứng dự báo

## Phạm vi

Ứng dụng Streamlit đọc dữ liệu thật từ HBase; Spark đã xử lý 36 tháng 2023–2025 và tạo model/dự báo ở giai đoạn 4. Giữ nguyên model, cách chia tập, quy tắc làm sạch, zero/null và DST đã duyệt. Không bổ sung 2026, không train lại hoặc mở rộng horizon trong giai đoạn này.

Demo phát lại lịch sử, dự báo một giờ trên năm 2025. Dự báo đã tính sẵn bằng model `stage4_final`, được kiểm tra tải lại trên toàn tập ở giai đoạn 4 và chuyển vào HBase để phục vụ. Chọn giờ trên Web không chạy lại Spark hay fit model. Lịch sử đầu vào chỉ có trước giờ đích; nhãn thực tế được đọc riêng để đối chiếu. Metadata lưu thời gian tạo thật năm 2026 và `historical_replay`; không giả định dự báo đã phát hành năm 2025 hoặc dữ liệu cập nhật trực tiếp.

## Cài đặt và chạy

Từ thư mục gốc project trong PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-stage5-windows.txt
docker compose -p bigdata-hbase -f docker/hbase/compose.yaml up -d
docker compose -p bigdata-hbase -f docker/hbase/compose.yaml ps
# Lần đầu trên máy đã hoàn thành giai đoạn 1–4:
.\scripts\run_stage5.ps1 -Step Prepare
.\scripts\run_stage5.ps1 -Step Geometry
.\scripts\run_stage5.ps1 -Step Load
# Mỗi lần mở lại, chỉ cần HBase và App:
.\scripts\run_stage5.ps1 -Step App
```

Mở http://127.0.0.1:8501. Ctrl+C ở terminal dừng Web; không xóa dữ liệu. Docker Desktop cần hoạt động và HBase phải healthy. Không cần container Spark thường trực. Script App giữ terminal chạy; có thể mở terminal khác. Venv hiện tại Python 3.13; không cần bật Activate để chạy các lệnh gọi trực tiếp này.

Máy clone mới cần tái lập dữ liệu, HBase và model giai đoạn 1–4 trước. Repo chỉ chứa code, cấu hình, bằng chứng nhỏ và tài liệu; dataset, snapshot dashboard, ranh giới bản đồ, model và venv bị Git bỏ qua. Các bước Prepare/Geometry đã hoàn thành với cùng checksum thì bỏ qua; Load đã nghiệm thu thì không nạp lại. Muốn kiểm tra chỉ đọc: `run_stage5.ps1 -Step Verify`. Nếu input thay đổi, công cụ dừng để giữ bằng chứng cũ; phải tạo phiên bản mới sau khi chốt phạm vi.

Streamlit 1.65.0 được chọn sau khi kiểm tra metadata chính thức, vì 1.49.1 yêu cầu packaging <26 và không tương thích với lock giai đoạn 4 (packaging 26.3). Không đổi thư viện đã khóa của giai đoạn 4 để ép tương thích. `requirements-stage5-windows-lock.txt` lưu môi trường cài thành công; kiểm tra bằng `python -m pip check`.

## Các trang và kịch bản demo

1. **Tổng quan:** chọn tối đa 31 ngày; tổng lượt đón, trung bình ngày, top 10 vùng và xu hướng ngày. Biểu đồ tháng bao phủ cả 36 tháng. Các tổng gồm chuyến trên ngày DST để phân tích.
2. **Bản đồ:** chọn ngày và giờ; màu theo số đếm thật, hover xem tên vùng. Ranh giới chính thức TLC, chuyển từ CRS trong shapefile sang EPSG:4326; giữ cả Newark Airport. Không bịa hình vùng hoặc dùng vị trí tâm thay ranh giới.
3. **Phân tích vùng:** chọn vùng/khoảng ngày; so sánh thêm một vùng; lịch sử giờ, heatmap thứ × giờ. Ô thiếu/không có quan sát để trống. Heatmap là trung bình trên khoảng chọn, không phải dự báo.
4. **Dự báo & kiểm chứng:** chọn vùng/giờ đích trong 2025; dự báo, baseline, phương án RF hoặc dự phòng, lịch sử trước giờ đích. Mở số thực tế để xem sai số tuyệt đối. Tab đánh giá tính MAE/RMSE/WAPE đúng vùng/ngày đang chọn; tách khỏi chỉ số toàn test. Sổ dự báo có CSV. Ngày DST không có dự báo/nhãn được nghiệm thu: màn hình giải thích và giữ số đếm mô tả.
5. **Dữ liệu & mô hình:** nguồn, phạm vi, cách xử lý, train/validation/test, thuật ngữ, giới hạn, phiên bản và thời gian snapshot.

Kịch bản: vùng 161, 07/01/2025, 12:00; xem lịch sử trước mốc, dự báo rồi bật số thực tế. Đổi sang 09/03/2025 để thấy chính sách DST; ngày 10/03/2025 có dự phòng do cửa sổ quá khứ đi qua DST. Thử khoảng 32 ngày để thấy giới hạn truy vấn. Chuyển sang một vùng ít chuyến để hiểu MAE và WAPE khác nhau.

## Thiết kế phục vụ và giới hạn truy vấn

| Bảng | Khóa dòng | Nội dung |
|---|---|---|
| `transport_demand_hourly_v1` | `ZZZ#YYYYMMDDHH` | Lịch sử/cờ chất lượng có sẵn; giữ nguyên |
| `transport_demand_forecast_v1` | `ZZZ#YYYYMMDDHH#stage4_final#1` | `p` dự báo/baseline; `q` đủ feature; `m` origin/version/horizon/mode/thời gian tạo |
| `transport_demand_summary_v1` | `D#YYYYMMDD#ZZZ` hoặc `M#YYYYMM#ZZZ` | `d:summary` JSON đếm/ngày/tháng, số giờ nguồn thiếu/DST; `m:version` |

Không lưu đáp án tương lai trong bảng forecast; lấy `d:target_trip_count` từ bảng lịch sử khi đánh giá. Origin hour là giờ quan sát cuối đã hoàn tất (giờ đích trừ một giờ), không phải timestamp phát hành dự báo. Horizon cố định 1 giờ. Float ghi repr để đọc lại chính xác; nhãn và metric giữ số thực, không làm tròn trước tính lỗi. Các bảng mới max_versions=1, batch 500, WAL bật, khóa xác định để chạy lại không tạo dòng trùng. Không xóa bảng lịch sử.

Prepare đọc Parquet đã được Spark nghiệm thu, kiểm tra SHA256, tạo snapshot phục vụ riêng trên D. Tổng hợp ngày/tháng ở bước phục vụ bằng pandas trên lưới theo giờ; không xử lý lại chuyến raw và không tuyên bố đây là một job Spark mới. Load đọc theo batch và đối chiếu toàn bộ khóa/ô sau khi ghi. Không đọc raw từ Web, không collect 128 triệu chuyến, không scan toàn bộ 6,9 triệu dòng mỗi lần lọc.

Lịch sử một vùng tối đa 744 giờ; tổng hợp ngày tối đa 8.153 dòng; tổng hợp tháng 9.468 dòng; bản đồ dùng 263 point reads. Cache dữ liệu 300 giây, trạng thái 60 giây. Nút kiểm tra lại xóa cache; không biến lỗi HBase thành dữ liệu giả. App chỉ lắng nghe localhost, không mở ra Internet.

## Kiểm tra và bằng chứng

Unit tests kiểm tra phạm vi, zero/null, DST, metric trên cùng tập hợp lệ, trường hợp WAPE không xác định, khóa qua năm và payload forecast không chứa nhãn. Kiểm thử ứng dụng dùng HBase thật; kiểm tra các trang, đổi vùng/ngày, CSV, lỗi kết nối và màn hình nhỏ. Bằng chứng tại `artifacts/metrics/stage5_*.json`; bản tổng kết riêng ghi kết quả thực tế sau nghiệm thu.

Nguồn tham khảo: [Streamlit navigation](https://docs.streamlit.io/develop/api-reference/navigation/st.navigation), [Streamlit charts](https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart), [TLC trip records và ranh giới vùng](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page).

Hai video TikTok chưa truy cập được trong công cụ, nên không tuyên bố đã kiểm tra theo toàn bộ nội dung video. Các yêu cầu đã áp dụng: chữ/đơn vị rõ, không giả realtime/accuracy, màu chuỗi nhất quán, thiếu không thành 0, loading/error/empty, bộ lọc có giới hạn, hỗ trợ bàn phím và kiểm tra bố cục nhỏ. Người dùng có thể cung cấp các lỗi cụ thể để đối chiếu thêm.
