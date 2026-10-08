> Tài liệu lịch sử: giữ để truy vết quyết định/thử nghiệm; không dùng làm hướng dẫn cài đặt hiện hành. Xem [mục lục](../README.md).

# Kết quả khảo sát thời lượng và phương án hoàn tất tập thử

Khảo sát trên 2.952.588 dòng ứng viên sau hai quy tắc đã duyệt: giới hạn tháng theo giờ đón và tách mã vùng 264/265. File nguồn không đổi. Kết quả đầy đủ tại `artifacts/metrics/duration_2024-01.json`.

## Kết quả

| Nhóm thời lượng | Số dòng |
|---|---:|
| Thiếu timestamp | 0 |
| Âm | 8 |
| Bằng 0 | 709 |
| Trên 0 đến 1 phút | 32.964 |
| Trên 1 đến 5 phút | 337.571 |
| Trên 5 đến 15 phút | 1.522.028 |
| Trên 15 đến 30 phút | 790.175 |
| Trên 30 đến 60 phút | 238.734 |
| Trên 1 đến 2 giờ | 27.683 |
| Trên 2 đến 6 giờ | 957 |
| Trên 6 đến 24 giờ | 1.743 |
| Trên 24 giờ | 16 |

Với các dòng có thời lượng dương: trung vị 11,63 phút, phân vị 95% là 37,93 phút, phân vị 99% là 60,43 phút. Đây là phân vị tính trên toàn bộ dữ liệu, không phải mẫu. Các khoảng trong bảng chỉ để mô tả, không phải ngưỡng loại đã chốt.

Trong 709 dòng thời lượng bằng 0, có 670 dòng quãng đường bằng 0, 2 dòng tổng tiền âm và 42 dòng tổng tiền bằng 0. Các nhóm chồng lấp. Tám dòng thời lượng âm đều có quãng đường dương và tiền cước không âm: không thể tự biết timestamp nào sai.

Ví dụ dài nhất: đón 24/01/2024 17:03:14, trả 31/01/2024 06:38:38, quãng đường 2,26 mile, tổng tiền 36,8; thời lượng khoảng 6,57 ngày. Đây là dấu hiệu cần gắn cờ, chưa đủ căn cứ để sửa timestamp. Một ví dụ thời lượng âm: đón 02/01/2024 10:00:00, trả 09:53:56 cùng ngày, quãng đường 7,2 mile.

## Phương án đã quyết định

Cập nhật ngày 06/10/2026: người dùng đã duyệt phương án cách ly 717 dòng không dương, giữ các bất thường khác. Đã triển khai và đối soát tại `DU_LIEU_THU_NGHIEM_V1.md`; các đoạn đề xuất bên dưới được giữ để giải thích lựa chọn.

Phương án đề xuất: cách ly 717 dòng thời lượng không dương cho tập thử; không sửa giờ hoặc lấy trị tuyệt đối. Còn 2.951.871 dòng nếu duyệt. Giữ nguyên những dòng có tiền âm, quãng đường 0, số hành khách thiếu và thời lượng dài, nhưng thêm cờ chất lượng để so sánh độ nhạy. Không điền số hành khách vì mục tiêu hiện tại là đếm chuyến.

Đây là lựa chọn bảo thủ về tính nhất quán thời gian, không chứng minh rằng 717 dòng không phải lượt đón thật. Vì dự báo dựa vào giờ đón, khi đánh giá cần báo cáo ảnh hưởng của việc cách ly.

Phương án thay thế: cách ly thêm 16 dòng trên 24 giờ, còn 2.951.855 dòng. Ngưỡng 24 giờ mang tính quy ước cho thử nghiệm; không có căn cứ để khẳng định mọi chuyến trên ngưỡng này đều sai. Chưa áp dụng phương án nào khi chưa nhận quyết định.

## Phạm vi dataset

Tháng 01/2024 là dữ liệu thử pipeline. Phạm vi cuối chưa chốt. Đề xuất dùng năm 2024 cho phát triển và kiểm tra thêm năm 2025 sau khi pipeline ổn định. Không tải tất cả lịch sử từ 2009 theo mặc định. Dữ liệu các năm phải kiểm tra schema, độ đầy đủ và chi phí xử lý; năm dùng đánh giá tương lai không được dùng để lựa chọn mô hình trước khi đánh giá.

## Kiểm chứng

Chạy lại: `.\.venv\Scripts\python.exe -m src.ingestion.profile_duration`.

Đã kiểm tra SHA256 trước/sau, tổng số dòng các nhóm bằng đầu vào và 7 kiểm thử thành công. Thời lượng là hiệu timestamp nguồn, chưa chuyển múi giờ. Ví dụ là các dòng đầu nhóm và 5 chuyến dài nhất, không phải mẫu ngẫu nhiên đại diện.
