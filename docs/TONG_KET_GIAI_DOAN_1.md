# Tổng kết giai đoạn 1 — Chuẩn bị dự án và môi trường Python

Ngày tổng hợp hồi cứu: 07/10/2026. Trạng thái: đã hoàn thành phần chuẩn bị dự án/Python làm nền cho xử lý dữ liệu. Hạ tầng Spark/HBase tích hợp chưa thuộc kết quả đã hoàn thành này.

## 1. Mục tiêu và phạm vi

Xác định bài toán dự báo lượt đón theo vùng/giờ, chuẩn bị cấu trúc làm việc và môi trường Python riêng trong dự án; ghi nhận yêu cầu môn học và hướng triển khai.

## 2. Công việc đã thực hiện

- Đọc yêu cầu đồ án, ghi nhận công nghệ đăng ký Apache HBase; lập kế hoạch sản phẩm, báo cáo Word, slide và demo.
- Tổ chức các thư mục code, dữ liệu, cấu hình, kiểm thử, tài liệu và kết quả.
- Cài CPython 3.11.17 tại `.python/`, tạo `.venv/`; đặt uv và cache trong dự án theo yêu cầu người dùng.
- Cài PyArrow 19.0.1 cho bước khảo sát/xử lý Parquet, lưu phiên bản trong `requirements-profile.txt`.
- Cấu hình VSCode gợi ý interpreter của venv; thêm `.gitignore` để bỏ qua môi trường, dữ liệu lớn và cấu hình riêng.
- Ghi nhận container HBase có sẵn từ kết quả lệnh do người dùng cung cấp: `hbase-demo`, image `dajobe/hbase`, cổng 9090 và 16010, volume gắn `/data`.

## 3. Kết quả đạt được

Có workspace và Python riêng dùng được để thực thi pipeline. Việc pipeline giai đoạn 2 chạy thành công bằng `.venv/Scripts/python.exe` là bằng chứng môi trường Python đã được sử dụng thực tế. Chọn Yellow Taxi NYC TLC để khảo sát, bắt đầu tháng 01/2024 trước khi mở rộng theo quyết định sau đó.

## 4. Đầu ra và kiểm chứng

| File hoặc thư mục | Vai trò / bằng chứng |
|---|---|
| [KE_HOACH.md](KE_HOACH.md) | Bài toán, yêu cầu, kiến trúc dự kiến, lịch và hồ sơ nộp |
| [CAI_DAT.md](CAI_DAT.md) | Cách dùng Python riêng, VSCode và môi trường dự kiến |
| [QUYET_DINH.md](QUYET_DINH.md) | Quyết định nguồn dữ liệu, Python và PyArrow |
| [requirements-profile.txt](../requirements-profile.txt) | Phiên bản thư viện xử lý dữ liệu |
| [.vscode/settings.json](../.vscode/settings.json) | Interpreter workspace và cấu hình editor |
| [.gitignore](../.gitignore) | Loại dữ liệu/môi trường khỏi Git |

## 5. Quyết định và lý do

Python được đặt trong thư mục dự án để có thể xóa cùng dự án; venv vẫn cần bản Python nền ở `.python`. Bắt đầu với một tháng dữ liệu để kiểm tra cách đọc và chất lượng trước khi mở rộng. Chọn PyArrow cho khảo sát Parquet theo lô. Những lựa chọn này được ghi trong nhật ký quyết định.

## 6. Vấn đề và giới hạn

Chưa xác minh tích hợp HBase put/get/scan, chưa triển khai Spark hoặc Docker Compose. Có container không đồng nghĩa ứng dụng đã kết nối HBase. Cấu hình tự kích hoạt venv không chứng minh mọi terminal người dùng đang dùng venv; các lệnh xử lý dùng đường dẫn Python tường minh. Bản tổng kết này không xác nhận đã cài toàn bộ thư viện ứng dụng hay mọi máy thành viên đã chạy được.

## 7. Bàn giao

Môi trường đã phục vụ giai đoạn 2: tải, khảo sát, xử lý và kiểm tra dữ liệu. Xem [tổng kết giai đoạn 2](TONG_KET_GIAI_DOAN_2.md). Phần chuẩn bị GitHub được hướng dẫn riêng; không coi việc hướng dẫn push là bằng chứng đã push thành công.
