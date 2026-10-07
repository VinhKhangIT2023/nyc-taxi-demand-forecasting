# Giai đoạn 3 — Tích hợp môi trường Spark và HBase

Ngày bắt đầu: 07/10/2026. Trạng thái: đang kiểm tra môi trường, chưa nghiệm thu.

## Mục tiêu triển khai

Tiếp nối dữ liệu giai đoạn 2 để có luồng xử lý và lưu trữ thực sự: Spark đọc dữ liệu Parquet, tổng hợp thử và đối chiếu kết quả; Python ghi/đọc HBase; sau đó kết nối luồng Spark → HBase. Ưu tiên sử dụng container HBase hiện có. Các lựa chọn phiên bản, schema bảng và quy mô nạp cần được giải thích và chốt với người dùng trước khi áp dụng.

## Kiểm tra đầu tiên

Phiên công cụ ngày 07/10/2026 đã tìm thấy Docker CLI, context `desktop-linux`, nhưng không kết nối được named pipe `dockerDesktopLinuxEngine` (The system cannot find the file specified). Vì vậy chưa đọc được trạng thái container, phiên bản HBase hoặc tài nguyên Docker. Không diễn giải giá trị mặc định 0 CPU/RAM từ lệnh lỗi thành tài nguyên thực tế.

Người dùng mở Docker Desktop, đợi engine khởi động rồi chạy trong Git Bash hoặc PowerShell:

```text
docker version
docker ps -a --filter "name=hbase-demo"
```

Chỉ tiếp tục khi `docker version` có phần Server. Nếu container hiện hữu ở trạng thái Exited, khởi động bằng `docker start hbase-demo`; nếu không thấy container, kiểm tra lại context và báo lại, không tự tạo container thay thế hoặc xóa volume.

## Các bước sau khi engine sẵn sàng

### Kết quả kiểm tra ngày 07/10/2026 sau khi người dùng mở Docker

- Docker Engine kết nối được; `hbase-demo` ở trạng thái running.
- HBase 2.1.2, tiến trình dùng Java 8; image ID cục bộ `sha256:daa36a6d90b118ced866b6c76fcd918e7da73302b0e4971f506f0f61f645a9fe` (không coi đây là registry digest).
- HBase shell trả về 1 active master, 1 server, 0 dead; lệnh list thành công, có bảng cũ `users`. Chỉ đọc trạng thái/tên bảng, chưa thay đổi dữ liệu.
- Có tiến trình Thrift 1 và REST. Cổng host 9090/16010 đã được publish; chưa xác nhận giao dịch Python qua Thrift.
- `hbase.rootdir=file:////data/hbase`, nằm dưới đường dẫn mount `/data` đã ghi nhận. Chưa nghiệm thu lưu bền bằng thử ghi rồi restart; chưa chốt lưu trữ ZooKeeper.
- Docker báo 12 CPU, 8.190.042.112 byte RAM. Đây là tài nguyên Docker nhìn thấy, không phải tổng RAM máy Windows.
- Log người dùng gửi có `Master has completed initialization`; kiểm tra shell sau đó xác nhận master đáp ứng. Mã Exited (137) ở lần dừng trước không đủ để kết luận nguyên nhân thiếu RAM.
- Lệnh chạy `.venv/Scripts/python.exe -m pip show happybase thriftpy2` trong phiên công cụ bị Windows Application Control chặn. Chưa biết terminal người dùng có bị cùng lỗi hay không; cần kiểm tra `--version` trước khi tiếp tục cài client. Không vô hiệu hóa chính sách bảo vệ để vượt lỗi.

### Trình tự triển khai còn lại

Cập nhật lỗi Python: người dùng xác nhận CMD cũng báo Device Guard chặn `.venv/Scripts/python.exe`. Kiểm tra chữ ký cả executable venv và Python nền cho kết quả `NotSigned`. Nhật ký CodeIntegrity sự kiện 3077 xác nhận policy `{0283ac0f-fff1-49ae-ada1-8a933130cad6}` chặn cùng file từ CMD, VSCode và phiên công cụ. Chưa xác định tên/nguồn quản lý policy (lệnh đọc danh sách policy bị từ chối truy cập), vì vậy chưa kết luận Smart App Control hay chính sách tổ chức. Cần xác định quyền quản lý máy và phương án Python được chính sách cho phép trước khi thay môi trường; không tắt hoặc né chính sách. Dữ liệu đã xử lý và kết quả giai đoạn 2 được giữ nguyên.

1. Kiểm tra container, image/digest, phiên bản HBase, log, cổng Thrift và vị trí dữ liệu bền vững. Xem `docker/README.md`.
2. Trình bày cấu hình môi trường tái lập cho hai máy; giải thích các thay đổi cần thiết trước khi thực hiện.
3. Thử client Python kết nối Thrift, ghi/đọc/scan một bảng thử riêng; ghi bằng chứng và xác minh dữ liệu còn sau restart có kiểm soát.
4. Thiết lập Spark trong Docker, đọc một partition Parquet và tổng hợp vùng/giờ theo đúng chính sách giai đoạn 2; đối chiếu tổng và từng nhóm với kết quả đã có.
5. Chốt schema HBase, row key, cách biểu diễn null/cờ chất lượng và batch ghi. Nạp thử phần nhỏ, kiểm tra đọc lại và chạy lại không nhân đôi dữ liệu trước khi mở rộng.
6. Lưu cấu hình, hướng dẫn vận hành và kiểm thử tích hợp để Hiếu có thể tái lập.

Không nạp ngay toàn bộ 126.994.028 chuyến vào HBase khi chưa chốt nhu cầu truy vấn. Hướng kiến trúc hiện tại dùng Parquet cho chuyến và HBase cho dữ liệu phục vụ theo vùng/giờ. Chưa huấn luyện hoặc dùng holdout để chọn mô hình ở bước tích hợp hạ tầng.

## Điều kiện hoàn thành

### Cập nhật khôi phục môi trường Python — 07/10/2026

Đã hoàn tất phương án người dùng duyệt: cài Python 3.13.16 chính thức cho tài khoản Windows, kiểm tra chữ ký và checksum, thử venv riêng trước khi tạo lại `.venv`. Smart App Control vẫn bật, Python 3.14 và PATH không thay đổi. Bản venv cũ được giữ trong `.tools/venv311-blocked-backup/` để tham chiếu; không sử dụng lại tại đường dẫn đã đổi.

Venv chính mới đạt 15/15 kiểm thử, `pip check` thành công, chạy lại `src.processing.verify_stage2` nghiệm thu cả ba năm đạt. HappyBase kết nối `127.0.0.1:9090` với buffered/binary và timeout 5000 ms, lệnh `tables()` trả về `[b'users']`. Chưa ghi bảng thử hoặc restart container để kiểm tra lưu bền.

Các phiên bản lưu trong `requirements-stage3-windows.txt`. HappyBase 1.2.0 cần setuptools 80.9.0 để có `pkg_resources`; hiện còn cảnh báo API deprecated, không phải lỗi kết nối. Đây là môi trường xử lý dữ liệu và client HBase đã kiểm tra, chưa xác nhận toàn bộ dashboard. Hướng dẫn hiện hành nằm đầu CAI_DAT.md.

### Checklist nghiệm thu còn lại

- Có kết quả Spark đọc/tổng hợp và đối chiếu đúng với dữ liệu giai đoạn 2.
- Có bằng chứng ghi/đọc/scan HBase và lưu bền qua restart.
- Luồng tích hợp thử có thể chạy lại, không tạo bản ghi logic trùng.
- Có hướng dẫn và cấu hình tái lập, ghi rõ chế độ chạy thực tế và giới hạn.
- Tạo `TONG_KET_GIAI_DOAN_3.md` với công việc, kết quả, bằng chứng, vấn đề còn lại trước khi thông báo hoàn thành.
