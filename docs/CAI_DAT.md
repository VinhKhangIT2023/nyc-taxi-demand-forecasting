# Thiết lập môi trường Windows VSCode Docker và GitHub

## 1. Trạng thái đã kiểm tra

### Môi trường hiện hành từ 07/10/2026

Người dùng đã duyệt chuyển Python Windows sang bản chính thức có chữ ký do Smart App Control chặn bản standalone cũ. Đã cài **CPython 3.13.16 x64** cho tài khoản người dùng tại `C:\Users\ADMIN\AppData\Local\Programs\Python\Python313\`, không đổi PATH, không gỡ Python 3.14. Bộ cài từ python.org có chữ ký hợp lệ Python Software Foundation; SHA256 `fb4f9f5d438b2396da0086dc70b935c530cb578e37adc6d354f7ad2037fee83b` khớp trang phát hành.

`.venv` hiện được tạo mới bằng Python 3.13.16. Môi trường 3.11 cũ được giữ trong `.tools/venv311-blocked-backup/` chỉ để tham chiếu, không chạy hoặc di chuyển ngược để sử dụng. Python nền cũ `.python/` vẫn còn nhưng không được dùng cho venv hiện hành. Smart App Control giữ bật. Xóa dự án không gỡ Python 3.13 đã cài ngoài dự án; gỡ riêng qua Installed apps nếu không còn dùng.

Cách tạo trên máy khác có Python 3.13.16 chính thức (chỉ tạo khi chưa có `.venv`):

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-stage3-windows.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Trong VSCode chọn `.venv/Scripts/python.exe`, đóng terminal cũ và mở terminal mới. Gọi executable tường minh nếu chưa kích hoạt. `python` ngoài venv vẫn có thể trả về 3.14; đó không phải lỗi. File `requirements-stage3-windows.txt` khóa thư viện đã kiểm tra cho xử lý dữ liệu và client HBase, chưa phải toàn bộ dashboard. Spark trong Docker vẫn là môi trường riêng theo kế hoạch; không áp dụng Python Windows 3.13 cho Spark một cách tự động.

### Lịch sử thiết lập và đề xuất ban đầu (được thay thế bởi mục hiện hành ở trên)

Cập nhật: theo yêu cầu của người dùng, Python 3.11.17 đã được cài riêng tại `.python/cpython-3.11.17-windows-x86_64-none/`; `.venv` được tạo từ Python này. Không cần cài Python 3.11 toàn máy theo phương án ban đầu bên dưới. Công cụ tải là uv cục bộ trong `.tools/uv/`, dùng bản CPython độc lập của Astral. `.tools/`, `.python/`, `.uv-cache/` và `.venv/` đều được Git bỏ qua.

Trong VSCode chọn **Python: Select Interpreter → Enter interpreter path → .venv/Scripts/python.exe**. Kiểm tra bằng `.\.venv\Scripts\python.exe --version`. Đã cài PyArrow 19.0.1 để khảo sát, ghi phiên bản trong `requirements-profile.txt`; chưa cài toàn bộ thư viện ứng dụng. Python 3.14 của người dùng không bị thay thế.

Xóa toàn bộ thư mục dự án sẽ xóa cả Python nền cục bộ và venv; chỉ xóa `.venv` sẽ giữ lại `.python`. Docker container và volume nằm ngoài thư mục nên không được xóa theo. Không di chuyển hoặc gửi nguyên venv sang máy khác: tạo lại môi trường ở đường dẫn mới.

Các đoạn dưới mô tả kế hoạch cài ban đầu và các bước triển khai ứng dụng tiếp theo; lệnh `py -3.11 -m venv` có thể thay bằng `.\.python\cpython-3.11.17-windows-x86_64-none\python.exe -m venv .venv` khi cần tạo lại venv cục bộ.

Ngày 05/10/2026, kết quả người dùng chạy trong PowerShell xác nhận Docker CLI hoạt động và có container `hbase-demo`, image `dajobe/hbase`. Cổng host 9090 và 16010 được ánh xạ vào cùng cổng container, trên mọi địa chỉ IPv4/IPv6. Có volume Docker gắn tại `/data`. Ưu tiên dùng lại container này; xem `docker/README.md` để kiểm tra tiếp.

Chưa xác nhận container đang chạy, dịch vụ Thrift hoạt động, phiên bản HBase hoặc cấu hình dữ liệu thực sự trỏ vào `/data`. Phiên terminal của công cụ hỗ trợ vẫn chưa nhận `docker` trên PATH; điều này khác với terminal người dùng. Chưa tạo `.venv` hoặc cài package; Python của người dùng chưa được xác minh. Không sử dụng Python nội bộ của công cụ hỗ trợ làm Python nền cho dự án của nhóm.

## 2. Cần cài gì

| Công cụ | Vai trò | Cài ở đâu |
|---|---|---|
| Python 3.11 x64 | venv, ứng dụng, notebook | Windows; hai bạn thống nhất cùng nhánh 3.11 |
| VSCode | Viết và chạy code | Windows, đã tìm thấy |
| Python và Pylance extensions | Interpreter, gợi ý kiểu | VSCode |
| Jupyter extension | Khảo sát notebook nếu dùng | VSCode |
| Git | Quản lý phiên bản | Windows, đã tìm thấy |
| Docker Desktop với Linux containers/WSL2 | Chạy HBase và Spark | Dùng bản đã có, kiểm tra hoạt động trước |
| Spark/PySpark + JDK | ETL, mô hình Spark ML | Trong container Spark |
| HBase + JDK tương thích | Lưu kết quả | Trong container HBase |
| Word và PowerPoint hoặc công cụ xuất tương thích | Báo cáo Word, slide PPT | Dùng phần mềm sẵn có |

Python lấy từ [python.org](https://www.python.org/downloads/windows/). Chọn Python 3.11 cho dự án, bật launcher/PATH nếu trình cài hỗ trợ. Sau khi cài mở lại VSCode và terminal. Không cần Anaconda, Hadoop/Spark cài trực tiếp Windows hoặc một cơ sở dữ liệu SQL khác cho phạm vi ban đầu.

Đề xuất môi trường Spark: PySpark 3.5.7, Python 3.11, JDK 17 trong container riêng. [Spark 3.5.7](https://spark.apache.org/docs/3.5.7/) liệt kê Java 8/11/17 và Python từ 3.8. Đây là lựa chọn cố định cho đồ án, không phải tuyên bố phiên bản mới nhất. JDK của HBase cần chọn theo ma trận phiên bản HBase riêng, không mặc định lấy JDK của Spark.

Mục tiêu tài nguyên để lập kế hoạch, chưa phải số đo máy hiện tại: máy 16 GB RAM sẽ dễ làm hơn; dự trù 20–30 GB ổ trống ban đầu cho image, dữ liệu và đầu ra rồi đo lại sau khi tải. Máy 8 GB nên chạy từng bước, Spark `local[2]`, ít dữ liệu, tắt container không dùng. Chưa xác minh RAM hoặc dung lượng ổ hiện tại.

## 3. Tạo venv trong VSCode

Mở đúng thư mục `D:\BaiTapVeNha\BigData\DoAn_BigData` bằng File → Open Folder. Mở terminal PowerShell mới rồi chạy từng lệnh:

```powershell
py -3.11 --version
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -c "import sys; print(sys.executable)"
```

Nếu không có `py` nhưng `python --version` trả về đúng 3.11, thay lệnh tạo môi trường bằng `python -m venv .venv`. Nếu cả hai chưa nhận, sửa cài đặt/PATH hoặc chọn interpreter đã cài trong VSCode; không dùng một Python ngẫu nhiên.

Trong VSCode: Ctrl+Shift+P → **Python: Select Interpreter** → chọn `.venv\Scripts\python.exe`. Khi mở notebook, chọn kernel của chính `.venv`. Cấu hình trong `.vscode/settings.json` đã gợi ý thư mục `.venv` cho workspace.

Có thể kích hoạt để dùng lệnh ngắn:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip --version
```

Nếu PowerShell chặn Activate.ps1, tiếp tục dùng đường dẫn `.\.venv\Scripts\python.exe` như trên; không cần đổi execution policy toàn máy. Kích hoạt là tiện ích cho terminal, không phải điều kiện bắt buộc để dùng venv.

Tạo cấu hình riêng, nếu chưa có `.env`:

```powershell
Copy-Item .env.example .env
```

`requirements.txt` hiện là danh sách đề xuất có khoảng phiên bản, chưa được cài và kiểm thử. Sau khi import và chạy ứng dụng thành công, tạo file khóa cho môi trường Windows:

```powershell
.\.venv\Scripts\python.exe -m pip freeze | Out-File -Encoding utf8 requirements-lock.txt
```

Hiếu dùng Python cùng nhánh rồi cài `requirements-lock.txt`. Môi trường Spark trong Linux phải có lock riêng sau khi xây container thành công; không sao chép venv Windows hoặc đóng băng môi trường Windows làm lock mặc định cho Linux.

## 4. Tận dụng Docker thế nào

**Nên tận dụng Docker** để hai máy thống nhất HBase/Spark và tránh cấu hình Java/Hadoop trực tiếp Windows. Venv vẫn cần cho ứng dụng và notebook chạy trên Windows; venv và Docker phục vụ hai môi trường khác nhau.

Mở Docker Desktop đang có, đợi engine sẵn sàng rồi kiểm tra trong terminal mới:

```powershell
docker --version
docker compose version
docker info
```

Nếu terminal vẫn không nhận lệnh, kiểm tra đường dẫn cài Docker Desktop và PATH, rồi khởi động lại terminal/VSCode. Đối chiếu [hướng dẫn Docker Windows](https://docs.docker.com/desktop/setup/install/windows-install/) cho backend WSL2/Linux containers. Không cài chồng một bản mới trước khi kiểm tra bản sẵn có.

Thiết kế cần triển khai trong tuần 2:

- Service `hbase`: HBase standalone, lưu dữ liệu ở named volume, expose UI và Thrift qua localhost. Xác minh gateway Thrift 1 phù hợp HappyBase.
- Service `spark`: Python 3.11, JDK 17, PySpark 3.5.7; mount source, data, artifacts; chạy job theo nhu cầu.
- Streamlit ban đầu chạy trong venv Windows; có thể thêm container `app` sau khi ổn định.
- Windows kết nối HBase bằng `localhost:9090`; Spark trong Docker network kết nối `hbase:9090`. `localhost` trong container là chính container đó.
- Không mount `.venv` Windows vào container Linux. Cài thư viện bằng requirements riêng bên trong image.

File Compose/Dockerfile **chưa được tạo trong đợt lập kế hoạch này**. Sau khi xây và kiểm thử cấu hình, hướng dẫn vận hành sẽ dùng `docker compose up -d hbase`, chạy job Spark, rồi mở Streamlit. Không chạy các lệnh này lúc chưa có Compose và code.

Khóa tag/digest image sau khi thử thành công; không dùng `latest` làm cấu hình nộp bài. Gắn volume đúng thư mục dữ liệu HBase, kiểm tra dữ liệu còn sau restart. `docker compose down -v` xóa named volume nên không dùng khi cần giữ dữ liệu demo.

## 5. Đưa lên GitHub

GitHub lưu source, cấu hình và tài liệu. Không đưa `.venv`, dữ liệu lớn, `.env`, log hoặc model sinh ra lên repo. `.gitignore` đã chuẩn bị. Chỉ đưa hình/bảng kết quả cần cho báo cáo, kèm lệnh tái tạo.

Khi sẵn sàng, khởi tạo repo ở đúng thư mục gốc:

```powershell
git init
git branch -M main
git status --short
git add README.md .gitignore .gitattributes .env.example .vscode requirements.txt requirements-spark.txt docs configs data/README.md docker src notebooks scripts tests artifacts reports
git diff --cached --stat
git commit -m "docs: add project plan and initial structure"
```

Danh sách add trên có chủ đích không lấy file Word yêu cầu của môn học ở gốc. Nếu muốn đưa file đó lên, kiểm tra quyền chia sẻ và thêm riêng. Không thay file gốc bằng báo cáo nhóm.

Trên GitHub tạo repository trống, ví dụ `public-transport-demand`, không khởi tạo thêm README. Thêm Hiếu làm collaborator. Đổi `YOUR_ACCOUNT` và tên repo trong lệnh dưới cho đúng:

```powershell
git remote add origin https://github.com/YOUR_ACCOUNT/public-transport-demand.git
git push -u origin main
```

Chưa tạo repo từ xa hoặc push trong lần lập kế hoạch này. Nếu Git yêu cầu danh tính, đặt tên/email commit của chính bạn theo hướng dẫn Git; không dùng danh tính của người khác.

Quy trình phối hợp:

1. Kéo `main` mới nhất, tạo nhánh như `feat/hbase-storage` hoặc `feat/demand-model`.
2. Mỗi task có đầu vào, đầu ra và điều kiện hoàn thành; commit theo thay đổi có nghĩa.
3. Push nhánh và mở Pull Request; người còn lại review rồi merge.
4. Trước nộp, gắn tag bản đã chạy thử và ghi mã commit vào báo cáo.

Hiếu clone repo, tạo `.venv` riêng, cài file lock khi có, tạo `.env`, tải dữ liệu theo danh mục và chạy Docker theo README hoàn chỉnh. Không gửi `.venv` qua ZIP.

## 6. Kiểm tra hoàn thành bước môi trường

- [ ] VSCode chọn đúng `.venv` và notebook dùng đúng kernel.
- [ ] Hai máy dùng cùng Python và các phiên bản dependency đã khóa.
- [ ] Docker engine hoạt động, Compose được nhận diện.
- [ ] Sau khi triển khai Docker: Spark chạy một phép tổng hợp nhỏ; HBase put/get/scan hoạt động.
- [ ] `git status` không chứa `.env`, `.venv` hoặc dữ liệu thô.
- [ ] Có thể clone ở máy còn lại và làm lại theo hướng dẫn.
