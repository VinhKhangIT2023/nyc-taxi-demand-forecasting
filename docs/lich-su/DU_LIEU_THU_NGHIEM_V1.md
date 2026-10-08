> Tài liệu lịch sử: giữ để truy vết quyết định/thử nghiệm; không dùng làm hướng dẫn cài đặt hiện hành. Xem [mục lục](../README.md).

# Dữ liệu thử nghiệm tháng 01 năm 2024 phiên bản 1

Đã hoàn tất các quy tắc được duyệt ngày 06/10/2026. Đây là dữ liệu thử nghiệm có quy tắc rõ ràng và truy vết được, không phải cam kết mọi bản ghi đều đúng. Pipeline hiện chạy bằng PyArrow trên máy cá nhân; chưa chuyển sang Spark hoặc nạp HBase.

## Đối soát

| Nhóm | Số dòng |
|---|---:|
| File gốc | 2.964.624 |
| Cách ly ngoài tháng theo thời điểm đón | 18 |
| Cách ly vùng 264/265 | 12.018 |
| Cách ly thời lượng không dương | 717 |
| Tập thử nghiệm v1 | 2.951.871 |

Các nhóm cách ly áp dụng tuần tự, không chồng lấp: 18 + 12.018 + 717 + 2.951.871 = 2.964.624. Trong 717 dòng của bước cuối, có 8 thời lượng âm và 709 bằng 0. Tất cả nhóm vẫn có file lưu riêng; không xóa dữ liệu raw. SHA256 đầu vào từng bước không đổi.

## Đầu ra

Các file nằm ở `data/processed/trial_2024-01_v1/`:

- `trips.parquet`: 2.951.871 dòng, giữ nguyên 19 cột nguồn, thêm thời lượng phút và 7 cờ chất lượng.
- `duration_quarantine.parquet`: 717 dòng, có lý do `negative_duration` hoặc `zero_duration`.
- `hourly_observed.csv`: 76.190 nhóm vùng × giờ có chuyến được giữ; tổng số chuyến bằng 2.951.871. Đây là bảng quan sát thưa, chưa điền 0 cho giờ không có bản ghi, chưa phải ma trận đầu vào mô hình hoàn chỉnh.
- `duration_sensitivity.csv`: 662 nhóm vùng × giờ bị ảnh hưởng bởi quy tắc thời lượng. Chênh lệch lớn nhất là 4 chuyến trong một nhóm. Chỉ số này không tự chứng minh sai số mô hình sẽ nhỏ.
- `audit.json`: đối soát, cờ, checksum và các hạn chế. Bản sao được lưu trong `artifacts/metrics/finalized_trial_2024-01.json` để theo dõi cùng code.

Hai nhóm cách ly trước vẫn nằm trong `data/interim/pickup_month_2024-01/outside_month.parquet` và `data/interim/pickup_zones_2024-01/unspecified_zones.parquet`.

## Cờ chất lượng trên dữ liệu được giữ

| Cờ | Số dòng | Ý nghĩa |
|---|---:|---|
| q_duration_gt_24h | 16 | Thời lượng trên 24 giờ, chưa loại |
| q_distance_zero | 58.152 | Quãng đường bằng 0 |
| q_distance_negative | 0 | Quãng đường âm |
| q_fare_negative | 37.273 | Tiền cước âm |
| q_total_negative | 35.327 | Tổng tiền âm |
| q_passenger_missing | 139.657 | Thiếu số hành khách |
| q_passenger_zero | 30.998 | Số hành khách bằng 0 |

Cờ có thể chồng lấp. Không điền thiếu, lấy trị tuyệt đối tiền âm, sửa timestamp hoặc áp dụng ngưỡng quãng đường cực đại. Quãng đường rất lớn vẫn giữ nguyên để khảo sát thêm; chưa có cờ dựa trên một ngưỡng cực đại được duyệt. Cờ là thông tin chất lượng sau chuyến, không tự động đưa vào đặc trưng dự báo trước chuyến.

Lưu ý: làm sạch hồi cứu sử dụng thời điểm trả để đánh giá thời lượng. Không được mô tả pipeline này là biết đầy đủ mọi chuyến ngay khi giờ đón kết thúc; mô phỏng thời gian thực cần chính sách độ trễ dữ liệu riêng.

## Chạy lại

Từ thư mục gốc, sau các bước tách tháng và vùng:

```powershell
.\.venv\Scripts\python.exe -m src.processing.finalize_trial
```

Lệnh từ chối ghi đè thư mục đã có. Muốn thử lại dùng `--output-dir data/processed/trial_2024-01_v1_rerun`. Tám kiểm thử thành công; đã kiểm tra tổng số dòng, giữ nguyên cột nguồn, nhóm cách ly và tác động lên số đếm theo giờ.

## Vì sao bắt đầu bằng hai năm và khi nào mở rộng

Phạm vi đã duyệt là hướng tới 2024–2025, tải và xử lý từng bước. Hiện mới có dữ liệu chuyến tháng 01/2024 trong dự án.

Năm 2024 dùng phát triển: chia train/validation theo thứ tự thời gian và thử nhiều mốc dự báo tiến dần. Năm 2025 dùng kiểm tra cuối sau khi khóa quy tắc và mô hình. Dữ liệu một năm có đủ các tháng để khảo sát chu kỳ năm nhưng chỉ có một lần lặp của mỗi mùa, chưa đủ để khẳng định mô hình học ổn định tính mùa vụ năm.

Hai năm là giới hạn phạm vi thực nghiệm ban đầu của nhóm, không phải tiêu chuẩn ngành hoặc giới hạn của Spark/HBase. Dữ liệu nhiều năm có thể giúp học sự biến thiên qua các mùa; cũng tăng khối lượng chuẩn hóa và có thể chứa hành vi khác giai đoạn mục tiêu. Chưa có phép đo nào trong dự án chứng minh thêm dữ liệu cũ tốt hơn hoặc kém hơn.

Nếu mở rộng, ưu tiên thêm năm 2023 như một thử nghiệm có kiểm soát trước khi đụng đến toàn bộ từ 2009: so sánh mô hình học trên 2023 cộng phần train của 2024 với mô hình chỉ học phần train 2024, giữ nguyên các cửa sổ validation năm 2024, định nghĩa nhãn và ngân sách tuning. Đánh giá MAE/RMSE, độ ổn định giữa các mốc/vùng và chi phí chạy. Chọn phạm vi dựa trên validation, sau đó mới mở kết quả test 2025. Đây là đề xuất thử nghiệm tương lai, chưa tải năm 2023.

Nếu đã dùng kết quả 2025 để chỉnh mô hình hoặc chọn phạm vi, năm đó không còn là test độc lập; phải ghi rõ và dành một khoảng thời gian tương lai khác chưa sử dụng để đánh giá cuối. Không quyết định mở rộng bằng cách liên tục tối ưu trên test.

Nguồn nguyên tắc: [Forecasting Principles and Practice về đánh giá](https://otexts.com/fpp2/accuracy.html) và [xử lý giá trị thiếu và ngoại lệ](https://otexts.com/fpp2/missing-outliers.html). Các năm và ngưỡng cụ thể ở đây là quyết định của dự án, không phải quy định của các tài liệu này.
