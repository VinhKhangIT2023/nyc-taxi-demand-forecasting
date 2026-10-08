# Cài đặt môi trường

Thực hiện từ thư mục gốc repo. Môi trường đã kiểm thử là Python 3.13.16 chính thức trên Windows; Spark 3.5.7/Python 3.11/Java 17 chạy riêng trong Docker.

## Công cụ cần có

- Git, VSCode và extension Python/Pylance.
- Python 3.13 x64 từ [python.org](https://www.python.org/downloads/windows/), có Python Launcher; phiên bản đã nghiệm thu là 3.13.16.
- Docker Desktop với Linux containers/WSL2. Các image được cố định trong Dockerfile/Compose của repo.

Không cần cài Java/Spark trực tiếp lên Windows, không cần thêm một cơ sở dữ liệu SQL cho luồng hiện hành. Mô hình/dashboard chưa được triển khai.

## Venv và VSCode

Chỉ tạo venv mới khi chưa có `.venv`:

```powershell
py -3.13 --version
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-stage3-windows.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Chọn **Python: Select Interpreter → Enter interpreter path → .venv/Scripts/python.exe** trong VSCode, sau đó mở terminal mới. Để kích hoạt trong PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -c "import sys; print(sys.executable)"
```

Nếu PowerShell không cho chạy activation script, có thể dùng trực tiếp `.\.venv\Scripts\python.exe`; không cần thay chính sách bảo vệ máy chỉ để kích hoạt. Không dùng Python 3.14 toàn máy thay cho interpreter đã chọn mà không kiểm thử lại thư viện.

Python nền được cài ngoài repo. Xóa `.venv` hoặc xóa repo không gỡ Python đã cài trên Windows. Không copy hoặc di chuyển venv giữa các máy: tạo lại từ requirements. Môi trường thử cũ và hướng dẫn Python standalone đã được chuyển vào `lich-su/CAI_DAT_CU.md`; chúng không còn là phương án hiện hành.

## Docker và dữ liệu

1. Bật Docker Desktop và kiểm tra `docker version` có phần Server.
2. Làm theo [chuẩn bị dữ liệu](DU_LIEU.md). Dataset và lookup không đi kèm Git.
3. Build image và chạy theo [hướng dẫn vận hành](VAN_HANH.md). Spark dùng Python trong image, không dùng venv Windows.

Không sao chép đường dẫn tài khoản Windows từ máy khác vào cấu hình. Các lệnh trong repo dùng đường dẫn tương đối từ thư mục gốc.

## Git

```powershell
git status --short
git add .
git diff --cached --stat
git commit -m "Describe the change"
git push
```

Kiểm tra staged files trước khi commit. Không đưa dữ liệu raw/processed, archive, venv hoặc `.env` thật lên GitHub. Dùng `.env.example` làm mẫu cấu hình khi cần; các script hiện hành không tự động đọc mọi biến trong file `.env`.
