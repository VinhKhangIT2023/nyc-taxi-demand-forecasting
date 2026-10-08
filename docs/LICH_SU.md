# Lịch sử khảo sát và triển khai

Gộp từ 8 tài liệu thử nghiệm ngày 08/10/2026 để giảm số file; giữ nội dung để truy vết. Các trạng thái và lệnh bên dưới mô tả thời điểm thử nghiệm, có thể đã được thay thế. Hướng dẫn hiện hành: [cài đặt](CAI_DAT.md), [dữ liệu](DU_LIEU.md), [vận hành](VAN_HANH.md), [mô hình](MO_HINH.md). Kết quả cuối cùng nằm trong [tổng kết từng giai đoạn](tong-ket/).

- [CAI_DAT_CU](#cai-dat-cu)
- [DU_LIEU_2023](#du-lieu-2023)
- [DU_LIEU_THU_NGHIEM_V1](#du-lieu-thu-nghiem-v1)
- [GIAI_DOAN_3](#giai-doan-3)
- [KHAO_SAT_DU_LIEU](#khao-sat-du-lieu)
- [KIEM_TRA_MA_VUNG](#kiem-tra-ma-vung)
- [KIEM_TRA_THOI_LUONG](#kiem-tra-thoi-luong)
- [THIET_KE_HBASE_THU](#thiet-ke-hbase-thu)


<a id="cai-dat-cu"></a>

## CAI_DAT_CU

### Thiết lập môi trường Windows VSCode Docker và GitHub

#### 1. Trạng thái đã kiểm tra

##### Môi trường hiện hành từ 07/10/2026

Người dùng đã duyệt chuyển Python Windows sang bản chính thức có chữ ký do Smart App Control chặn bản standalone cũ. Đã cài **CPython 3.13.16 x64** cho tài khoản người dùng tại `C:\Users\ADMIN\AppData\Local\Programs\Python\Python313\`, không đổi PATH, không gỡ Python 3.14. Bộ cài từ python.org có chữ ký hợp lệ Python Software Foundation; SHA256 `fb4f9f5d438b2396da0086dc70b935c530cb578e37adc6d354f7ad2037fee83b` khớp trang phát hành.

`.venv` hiện được tạo mới bằng Python 3.13.16. Môi trường 3.11 cũ được giữ trong `.tools/venv311-blocked-backup/` chỉ để tham chiếu, không chạy hoặc di chuyển ngược để sử dụng. Python nền cũ `.python/` vẫn còn nhưng không được dùng cho venv hiện hành. Smart App Control giữ bật. Xóa dự án không gỡ Python 3.13 đã cài ngoài dự án; gỡ riêng qua Installed apps nếu không còn dùng.

Cách tạo trên máy khác có Python 3.13.16 chính thức (chỉ tạo khi chưa có `.venv`):

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-stage3-windows.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Trong VSCode chọn `.venv/Scripts/python.exe`, đóng terminal cũ và mở terminal mới. Gọi executable tường minh nếu chưa kích hoạt. `python` ngoài venv vẫn có thể trả về 3.14; đó không phải lỗi. File `requirements-stage3-windows.txt` khóa thư viện đã kiểm tra cho xử lý dữ liệu và client HBase, chưa phải toàn bộ dashboard. Spark trong Docker vẫn là môi trường riêng theo kế hoạch; không áp dụng Python Windows 3.13 cho Spark một cách tự động.

##### Lịch sử thiết lập và đề xuất ban đầu (được thay thế bởi mục hiện hành ở trên)

Cập nhật: theo yêu cầu của người dùng, Python 3.11.17 đã được cài riêng tại `.python/cpython-3.11.17-windows-x86_64-none/`; `.venv` được tạo từ Python này. Không cần cài Python 3.11 toàn máy theo phương án ban đầu bên dưới. Công cụ tải là uv cục bộ trong `.tools/uv/`, dùng bản CPython độc lập của Astral. `.tools/`, `.python/`, `.uv-cache/` và `.venv/` đều được Git bỏ qua.

Trong VSCode chọn **Python: Select Interpreter → Enter interpreter path → .venv/Scripts/python.exe**. Kiểm tra bằng `.\.venv\Scripts\python.exe --version`. Đã cài PyArrow 19.0.1 để khảo sát, ghi phiên bản trong `requirements-profile.txt`; chưa cài toàn bộ thư viện ứng dụng. Python 3.14 của người dùng không bị thay thế.

Xóa toàn bộ thư mục dự án sẽ xóa cả Python nền cục bộ và venv; chỉ xóa `.venv` sẽ giữ lại `.python`. Docker container và volume nằm ngoài thư mục nên không được xóa theo. Không di chuyển hoặc gửi nguyên venv sang máy khác: tạo lại môi trường ở đường dẫn mới.

Các đoạn dưới mô tả kế hoạch cài ban đầu và các bước triển khai ứng dụng tiếp theo; lệnh `py -3.11 -m venv` có thể thay bằng `.\.python\cpython-3.11.17-windows-x86_64-none\python.exe -m venv .venv` khi cần tạo lại venv cục bộ.

Ngày 05/10/2026, kết quả người dùng chạy trong PowerShell xác nhận Docker CLI hoạt động và có container `hbase-demo`, image `dajobe/hbase`. Cổng host 9090 và 16010 được ánh xạ vào cùng cổng container, trên mọi địa chỉ IPv4/IPv6. Có volume Docker gắn tại `/data`. Ưu tiên dùng lại container này; xem `docker/README.md` để kiểm tra tiếp.

Chưa xác nhận container đang chạy, dịch vụ Thrift hoạt động, phiên bản HBase hoặc cấu hình dữ liệu thực sự trỏ vào `/data`. Phiên terminal của công cụ hỗ trợ vẫn chưa nhận `docker` trên PATH; điều này khác với terminal người dùng. Chưa tạo `.venv` hoặc cài package; Python của người dùng chưa được xác minh. Không sử dụng Python nội bộ của công cụ hỗ trợ làm Python nền cho dự án của nhóm.

#### 2. Cần cài gì

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

#### 3. Tạo venv trong VSCode

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

#### 4. Tận dụng Docker thế nào

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

#### 5. Đưa lên GitHub

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

#### 6. Kiểm tra hoàn thành bước môi trường

- [ ] VSCode chọn đúng `.venv` và notebook dùng đúng kernel.
- [ ] Hai máy dùng cùng Python và các phiên bản dependency đã khóa.
- [ ] Docker engine hoạt động, Compose được nhận diện.
- [ ] Sau khi triển khai Docker: Spark chạy một phép tổng hợp nhỏ; HBase put/get/scan hoạt động.
- [ ] `git status` không chứa `.env`, `.venv` hoặc dữ liệu thô.
- [ ] Có thể clone ở máy còn lại và làm lại theo hướng dẫn.


<a id="du-lieu-2023"></a>

## DU_LIEU_2023

### Dữ liệu Yellow Taxi năm 2023

#### Phạm vi và nguồn

Người dùng duyệt bổ sung đủ năm 2023 để chuẩn bị so sánh việc học thêm lịch sử với phương án chỉ học từ 2024. Đã tải 12 file Yellow Taxi từ các liên kết thực tế trên [trang TLC](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page). Manifest tải lưu URL, thời điểm kiểm tra, checksum, dung lượng, số dòng và schema ở `artifacts/metrics/download_manifest_2023.json`.

File nguồn có tổng cộng 38.310.226 dòng, 635.743.618 byte. Bản tải được nhận diện bằng SHA256; không tuyên bố đã đối chiếu với checksum do TLC phát hành. Dữ liệu nguồn giữ tại `data/raw/` và không push lên GitHub.

#### Kết quả đã hoàn thành

| Nhóm | Số dòng |
|---|---:|
| Raw đủ 12 tháng | 38.310.226 |
| Ngoài tháng theo thời điểm đón | 730 |
| Vùng đón 264/265 | 387.192 |
| Thời lượng không dương | 12.750 |
| Dữ liệu chính sau xử lý | **37.909.554** |

Đối soát: 730 + 387.192 + 12.750 + 37.909.554 = 38.310.226. Mỗi tháng có audit riêng và tổng hợp ở `artifacts/metrics/processed_2023.json`. Manifest năm ghi complete=true. 12 file đầu ra dùng chung schema đã sẵn sàng đọc.

Bảng tổng hợp có 869.552 nhóm vùng × giờ quan sát; tổng số chuyến khớp dữ liệu chính. Có 261 mã vùng có chuyến trong năm. Ghép với tập tháng 01/2024 v1 hiện có được **40.861.425 dòng**; loader đã được chạy thử thành công.

Kiểm tra thời gian ghi nhận 8.759 nhãn giờ địa phương trong năm; không có nhãn 12/03/2023 lúc 02:00. Khoảng đó liên quan chuyển giờ mùa hè, không tự điền thành một giờ có 0 chuyến. Tại lần lùi đồng hồ tháng 11, timestamp thiếu offset không phân biệt được hai lần xuất hiện cùng giờ. Bảng hiện dùng nhãn giờ địa phương, chưa được quảng bá là chuỗi UTC liên tục sẵn sàng huấn luyện.

Đối chiếu quy tắc giờ mùa hè của [NIST](https://www.nist.gov/pml/time-and-frequency-division/popular-links/daylight-saving-time-dst): đây là khoảng nhảy đồng hồ từ 02:00 lên 03:00 vào Chủ nhật thứ hai tháng 3. Timestamp wall-clock cũng có thể làm thời lượng chuyến qua lần lùi đồng hồ bị nhập nhằng; nhóm cách ly thời lượng không dương không đồng nghĩa mọi chuyến đó đều không tồn tại.

Kiểm tra trùng hoàn tất cả 12 tháng trên toàn bộ 19 cột nguồn: **2 nhóm giống hệt, mỗi nhóm 2 dòng**, tương ứng 2 bản sao dư, đều thuộc ngày 13/11/2023. Chưa xóa vì không có định danh chuyến duy nhất; ghi đầy đủ giá trị để truy vết ở `artifacts/metrics/duplicate_audit_2023.json`. Nếu thử bỏ một bản sao mỗi nhóm, tác động tối đa là giảm 2 chuyến trên toàn năm; hiện giữ nhất quán chính sách không tự deduplicate. Các tháng khác không có bản sao dư giống toàn bộ cột.

Không phát hiện NaN hoặc vô cực trong các cột số trên tập đầu ra (null được thống kê riêng, không coi là NaN). Các cờ chất lượng và null vẫn được bảo toàn. Đã chạy 11 kiểm thử thành công; kiểm tra tổng số chuyến theo giờ khớp số dòng, checksum đầu vào và schema chung. Kết quả kiểm tra độ phủ tại `artifacts/metrics/coverage_2023.json`.

#### Quy tắc xử lý

Áp dụng cùng chính sách v1 đã duyệt cho tháng 01/2024, theo thứ tự:

1. Tách theo thời điểm đón thuộc tháng của file nguồn. Giữ các dòng ngoài tháng để xem lại, không tự sửa ngày hoặc chuyển sang tháng khác.
2. Tách PULocationID 264/265. Mã 1 Newark Airport vẫn được giữ.
3. Tách thời lượng không dương, giữ lý do âm hoặc bằng 0.
4. Giữ các vấn đề khác, thêm cờ chất lượng. Không biến tiền âm thành dương, không điền số hành khách, không tự đặt ngưỡng quãng đường tối đa.
5. Chuẩn hóa schema đầu ra để đọc nhiều tháng cùng nhau.

Nếu timestamp cần thiết bị thiếu hoặc mã vùng không tồn tại trong lookup, pipeline dừng thay vì tự thêm quy tắc. Quarantine của từng bước được giữ riêng; đây là các nhóm tuần tự không chồng lấp.

#### Schema dùng chung

Tháng 01/2023 dùng `airport_fee`, các tháng sau dùng `Airport_fee`. Đầu ra thống nhất `Airport_fee`. Các mã ID được nâng lên int64; passenger_count và RatecodeID dùng float64 để giữ cả kiểu double của nguồn tháng 1 và giá trị thiếu; string nâng thành large_string. Không làm tròn, không điền null. Phép cast ở chế độ safe để từ chối giá trị không thể biểu diễn chính xác. Timestamp giữ đơn vị microsecond như nguồn.

Schema cuối có 19 cột nguồn, duration_minutes và 7 cờ chất lượng. Raw và bản đầu ra trước chuẩn hóa được giữ để truy vết.

#### Cách dùng

Sau khi `dataset_manifest.json` ghi `complete: true`, thư mục chỉ chứa các file chuyến đã chuẩn hóa là:

`data/processed/yellow_2023_v1/trips/part-2023-01.parquet` đến `part-2023-12.parquet`.

Không đọc đệ quy toàn bộ `data/processed/` hoặc `data/interim/`: sẽ trộn bản lặp giữa các bước và file cách ly. Chỉ chọn `part-*.parquet` trong thư mục `trips` hoặc dùng loader có sẵn.

```powershell
.\.venv\Scripts\python.exe -m src.ingestion.load_clean_trips --year 2023
.\.venv\Scripts\python.exe -m src.ingestion.load_clean_trips --year 2023 --include-january-2024
```

Trong Python, xử lý từng lô để không nạp toàn bộ năm vào RAM:

```python
from src.ingestion.load_clean_trips import iter_clean_batches

for table in iter_clean_batches(2023, include_january_2024=True):
    # table là pyarrow.Table, schema đã thống nhất
    pass
```

`hourly_observed.csv` ở thư mục năm là số chuyến theo vùng × giờ có quan sát. Không có suy diễn rằng giờ vắng bản ghi chắc chắn bằng 0. Mô hình cần bước dựng lưới thời gian và đặc trưng riêng.

#### Chạy lại và phục hồi

```powershell
.\.venv\Scripts\python.exe -m src.ingestion.download_year --year 2023
.\.venv\Scripts\python.exe -m src.processing.process_year --year 2023
.\.venv\Scripts\python.exe -m src.ingestion.audit_year_duplicates --year 2023
```

Lệnh xử lý chỉ dùng lại bước đã có audit và checksum khớp; nếu file thay đổi hoặc bước dở dang, dừng để kiểm tra. Kiểm tra trùng chạy theo tháng và có thể dùng nhiều RAM hơn pipeline theo lô. Các dòng có cùng giá trị không tự động bị xóa vì nguồn không có khóa chuyến duy nhất. Kết quả kiểm tra trùng được báo riêng.

#### Giới hạn cần nhớ

- Danh mục vùng là bản TLC cung cấp khi tải, chưa xác nhận là snapshot lịch sử năm 2023.
- Dòng ngoài tháng nguồn được giữ trong quarantine; chưa tự phân bổ lại qua các file giáp tháng. Điều này có thể bỏ sót một số lượt đón trong tập chính và phải báo trong nghiên cứu.
- Timestamp nguồn không có offset. Giờ lặp khi đổi giờ mùa hè có thể bị gộp trong bảng wall-clock; không tự khôi phục UTC khi không có đủ thông tin. Cần chính sách DST trước mô hình chuỗi giờ liên tục.
- Lọc theo thời điểm trả là làm sạch hồi cứu, không phải mô phỏng hệ thống thời gian thực đã nhận đủ dữ liệu ngay khi giờ đón kết thúc.
- Dữ liệu phục vụ phân tích lượt đón đã ghi nhận, không đo được nhu cầu chưa phục vụ.
- Hiện chỉ có 2023 và tháng 01/2024. Chưa có đủ 2024 để chạy phép so sánh đã bàn; 2025 vẫn dành cho đánh giá tương lai. Chưa huấn luyện hoặc khẳng định mô hình tốt hơn.


<a id="du-lieu-thu-nghiem-v1"></a>

## DU_LIEU_THU_NGHIEM_V1

### Dữ liệu thử nghiệm tháng 01 năm 2024 phiên bản 1

Đã hoàn tất các quy tắc được duyệt ngày 06/10/2026. Đây là dữ liệu thử nghiệm có quy tắc rõ ràng và truy vết được, không phải cam kết mọi bản ghi đều đúng. Pipeline hiện chạy bằng PyArrow trên máy cá nhân; chưa chuyển sang Spark hoặc nạp HBase.

#### Đối soát

| Nhóm | Số dòng |
|---|---:|
| File gốc | 2.964.624 |
| Cách ly ngoài tháng theo thời điểm đón | 18 |
| Cách ly vùng 264/265 | 12.018 |
| Cách ly thời lượng không dương | 717 |
| Tập thử nghiệm v1 | 2.951.871 |

Các nhóm cách ly áp dụng tuần tự, không chồng lấp: 18 + 12.018 + 717 + 2.951.871 = 2.964.624. Trong 717 dòng của bước cuối, có 8 thời lượng âm và 709 bằng 0. Tất cả nhóm vẫn có file lưu riêng; không xóa dữ liệu raw. SHA256 đầu vào từng bước không đổi.

#### Đầu ra

Các file nằm ở `data/processed/trial_2024-01_v1/`:

- `trips.parquet`: 2.951.871 dòng, giữ nguyên 19 cột nguồn, thêm thời lượng phút và 7 cờ chất lượng.
- `duration_quarantine.parquet`: 717 dòng, có lý do `negative_duration` hoặc `zero_duration`.
- `hourly_observed.csv`: 76.190 nhóm vùng × giờ có chuyến được giữ; tổng số chuyến bằng 2.951.871. Đây là bảng quan sát thưa, chưa điền 0 cho giờ không có bản ghi, chưa phải ma trận đầu vào mô hình hoàn chỉnh.
- `duration_sensitivity.csv`: 662 nhóm vùng × giờ bị ảnh hưởng bởi quy tắc thời lượng. Chênh lệch lớn nhất là 4 chuyến trong một nhóm. Chỉ số này không tự chứng minh sai số mô hình sẽ nhỏ.
- `audit.json`: đối soát, cờ, checksum và các hạn chế. Bản sao được lưu trong `artifacts/metrics/finalized_trial_2024-01.json` để theo dõi cùng code.

Hai nhóm cách ly trước vẫn nằm trong `data/interim/pickup_month_2024-01/outside_month.parquet` và `data/interim/pickup_zones_2024-01/unspecified_zones.parquet`.

#### Cờ chất lượng trên dữ liệu được giữ

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

#### Chạy lại

Từ thư mục gốc, sau các bước tách tháng và vùng:

```powershell
.\.venv\Scripts\python.exe -m src.processing.finalize_trial
```

Lệnh từ chối ghi đè thư mục đã có. Muốn thử lại dùng `--output-dir data/processed/trial_2024-01_v1_rerun`. Tám kiểm thử thành công; đã kiểm tra tổng số dòng, giữ nguyên cột nguồn, nhóm cách ly và tác động lên số đếm theo giờ.

#### Vì sao bắt đầu bằng hai năm và khi nào mở rộng

Phạm vi đã duyệt là hướng tới 2024–2025, tải và xử lý từng bước. Hiện mới có dữ liệu chuyến tháng 01/2024 trong dự án.

Năm 2024 dùng phát triển: chia train/validation theo thứ tự thời gian và thử nhiều mốc dự báo tiến dần. Năm 2025 dùng kiểm tra cuối sau khi khóa quy tắc và mô hình. Dữ liệu một năm có đủ các tháng để khảo sát chu kỳ năm nhưng chỉ có một lần lặp của mỗi mùa, chưa đủ để khẳng định mô hình học ổn định tính mùa vụ năm.

Hai năm là giới hạn phạm vi thực nghiệm ban đầu của nhóm, không phải tiêu chuẩn ngành hoặc giới hạn của Spark/HBase. Dữ liệu nhiều năm có thể giúp học sự biến thiên qua các mùa; cũng tăng khối lượng chuẩn hóa và có thể chứa hành vi khác giai đoạn mục tiêu. Chưa có phép đo nào trong dự án chứng minh thêm dữ liệu cũ tốt hơn hoặc kém hơn.

Nếu mở rộng, ưu tiên thêm năm 2023 như một thử nghiệm có kiểm soát trước khi đụng đến toàn bộ từ 2009: so sánh mô hình học trên 2023 cộng phần train của 2024 với mô hình chỉ học phần train 2024, giữ nguyên các cửa sổ validation năm 2024, định nghĩa nhãn và ngân sách tuning. Đánh giá MAE/RMSE, độ ổn định giữa các mốc/vùng và chi phí chạy. Chọn phạm vi dựa trên validation, sau đó mới mở kết quả test 2025. Đây là đề xuất thử nghiệm tương lai, chưa tải năm 2023.

Nếu đã dùng kết quả 2025 để chỉnh mô hình hoặc chọn phạm vi, năm đó không còn là test độc lập; phải ghi rõ và dành một khoảng thời gian tương lai khác chưa sử dụng để đánh giá cuối. Không quyết định mở rộng bằng cách liên tục tối ưu trên test.

Nguồn nguyên tắc: [Forecasting Principles and Practice về đánh giá](https://otexts.com/fpp2/accuracy.html) và [xử lý giá trị thiếu và ngoại lệ](https://otexts.com/fpp2/missing-outliers.html). Các năm và ngưỡng cụ thể ở đây là quyết định của dự án, không phải quy định của các tài liệu này.


<a id="giai-doan-3"></a>

## GIAI_DOAN_3

> Hoàn thành đầy đủ ngày 08/10/2026: Spark đủ 36 tháng 2023–2025; HBase đủ 6.917.952 dòng, hai lượt nạp và phục hồi được đối chiếu từng ô, 0 sai lệch, 21/21 tests đạt. Xem [tổng kết giai đoạn 3](tong-ket/TONG_KET_GIAI_DOAN_3.md) và [hướng dẫn hiện hành](VAN_HANH.md). Các mốc thử nghiệm bên dưới là lịch sử triển khai.

### Giai đoạn 3 — Tích hợp môi trường Spark và HBase

Nhật ký dưới đây bắt đầu ngày 07/10/2026, ghi lại các bước thử trước khi mở rộng. Phạm vi hoàn thành hiện hành gồm toàn bộ dữ liệu và được nghiệm thu ngày 08/10/2026; xem tổng kết và hướng dẫn liên kết ở đầu trang.

#### Mục tiêu triển khai

Tiếp nối dữ liệu giai đoạn 2 để có luồng xử lý và lưu trữ thực sự: Spark đọc dữ liệu Parquet, tổng hợp thử và đối chiếu kết quả; Python ghi/đọc HBase; sau đó kết nối luồng Spark → HBase. Ưu tiên sử dụng container HBase hiện có. Các lựa chọn phiên bản, schema bảng và quy mô nạp cần được giải thích và chốt với người dùng trước khi áp dụng.

#### Kiểm tra đầu tiên

Phiên công cụ ngày 07/10/2026 đã tìm thấy Docker CLI, context `desktop-linux`, nhưng không kết nối được named pipe `dockerDesktopLinuxEngine` (The system cannot find the file specified). Vì vậy chưa đọc được trạng thái container, phiên bản HBase hoặc tài nguyên Docker. Không diễn giải giá trị mặc định 0 CPU/RAM từ lệnh lỗi thành tài nguyên thực tế.

Người dùng mở Docker Desktop, đợi engine khởi động rồi chạy trong Git Bash hoặc PowerShell:

```text
docker version
docker ps -a --filter "name=hbase-demo"
```

Chỉ tiếp tục khi `docker version` có phần Server. Nếu container hiện hữu ở trạng thái Exited, khởi động bằng `docker start hbase-demo`; nếu không thấy container, kiểm tra lại context và báo lại, không tự tạo container thay thế hoặc xóa volume.

#### Các bước sau khi engine sẵn sàng

##### Kết quả kiểm tra ngày 07/10/2026 sau khi người dùng mở Docker

- Docker Engine kết nối được; `hbase-demo` ở trạng thái running.
- HBase 2.1.2, tiến trình dùng Java 8; image ID cục bộ `sha256:daa36a6d90b118ced866b6c76fcd918e7da73302b0e4971f506f0f61f645a9fe` (không coi đây là registry digest).
- HBase shell trả về 1 active master, 1 server, 0 dead; lệnh list thành công, có bảng cũ `users`. Chỉ đọc trạng thái/tên bảng, chưa thay đổi dữ liệu.
- Có tiến trình Thrift 1 và REST. Cổng host 9090/16010 đã được publish; chưa xác nhận giao dịch Python qua Thrift.
- `hbase.rootdir=file:////data/hbase`, nằm dưới đường dẫn mount `/data` đã ghi nhận. Chưa nghiệm thu lưu bền bằng thử ghi rồi restart; chưa chốt lưu trữ ZooKeeper.
- Docker báo 12 CPU, 8.190.042.112 byte RAM. Đây là tài nguyên Docker nhìn thấy, không phải tổng RAM máy Windows.
- Log người dùng gửi có `Master has completed initialization`; kiểm tra shell sau đó xác nhận master đáp ứng. Mã Exited (137) ở lần dừng trước không đủ để kết luận nguyên nhân thiếu RAM.
- Lệnh chạy `.venv/Scripts/python.exe -m pip show happybase thriftpy2` trong phiên công cụ bị Windows Application Control chặn. Chưa biết terminal người dùng có bị cùng lỗi hay không; cần kiểm tra `--version` trước khi tiếp tục cài client. Không vô hiệu hóa chính sách bảo vệ để vượt lỗi.

##### Trình tự triển khai còn lại

Cập nhật lỗi Python: người dùng xác nhận CMD cũng báo Device Guard chặn `.venv/Scripts/python.exe`. Kiểm tra chữ ký cả executable venv và Python nền cho kết quả `NotSigned`. Nhật ký CodeIntegrity sự kiện 3077 xác nhận policy `{0283ac0f-fff1-49ae-ada1-8a933130cad6}` chặn cùng file từ CMD, VSCode và phiên công cụ. Chưa xác định tên/nguồn quản lý policy (lệnh đọc danh sách policy bị từ chối truy cập), vì vậy chưa kết luận Smart App Control hay chính sách tổ chức. Cần xác định quyền quản lý máy và phương án Python được chính sách cho phép trước khi thay môi trường; không tắt hoặc né chính sách. Dữ liệu đã xử lý và kết quả giai đoạn 2 được giữ nguyên.

1. Kiểm tra container, image/digest, phiên bản HBase, log, cổng Thrift và vị trí dữ liệu bền vững. Xem `docker/README.md`.
2. Trình bày cấu hình môi trường tái lập cho hai máy; giải thích các thay đổi cần thiết trước khi thực hiện.
3. Thử client Python kết nối Thrift, ghi/đọc/scan một bảng thử riêng; ghi bằng chứng và xác minh dữ liệu còn sau restart có kiểm soát.
4. Thiết lập Spark trong Docker, đọc một partition Parquet và tổng hợp vùng/giờ theo đúng chính sách giai đoạn 2; đối chiếu tổng và từng nhóm với kết quả đã có.
5. Chốt schema HBase, row key, cách biểu diễn null/cờ chất lượng và batch ghi. Nạp thử phần nhỏ, kiểm tra đọc lại và chạy lại không nhân đôi dữ liệu trước khi mở rộng.
6. Lưu cấu hình, hướng dẫn vận hành và kiểm thử tích hợp để Hiếu có thể tái lập.

Không nạp ngay toàn bộ 126.994.028 chuyến vào HBase khi chưa chốt nhu cầu truy vấn. Hướng kiến trúc hiện tại dùng Parquet cho chuyến và HBase cho dữ liệu phục vụ theo vùng/giờ. Chưa huấn luyện hoặc dùng holdout để chọn mô hình ở bước tích hợp hạ tầng.

#### Điều kiện hoàn thành

##### Cập nhật khôi phục môi trường Python — 07/10/2026

Đã hoàn tất phương án người dùng duyệt: cài Python 3.13.16 chính thức cho tài khoản Windows, kiểm tra chữ ký và checksum, thử venv riêng trước khi tạo lại `.venv`. Smart App Control vẫn bật, Python 3.14 và PATH không thay đổi. Bản venv cũ được giữ trong `.tools/venv311-blocked-backup/` để tham chiếu; không sử dụng lại tại đường dẫn đã đổi.

Venv chính mới đạt 15/15 kiểm thử, `pip check` thành công, chạy lại `src.processing.verify_stage2` nghiệm thu cả ba năm đạt. HappyBase kết nối `127.0.0.1:9090` với buffered/binary và timeout 5000 ms, lệnh `tables()` trả về `[b'users']`. Chưa ghi bảng thử hoặc restart container để kiểm tra lưu bền.

Các phiên bản lưu trong `requirements-stage3-windows.txt`. HappyBase 1.2.0 cần setuptools 80.9.0 để có `pkg_resources`; hiện còn cảnh báo API deprecated, không phải lỗi kết nối. Đây là môi trường xử lý dữ liệu và client HBase đã kiểm tra, chưa xác nhận toàn bộ dashboard. Hướng dẫn hiện hành nằm đầu CAI_DAT.md.

##### Kiểm thử HBase ghi/đọc và restart — 07/10/2026

Đã chạy `src/storage/smoke_hbase.py` qua venv Python 3.13.16. Tạo riêng bảng `bigdata_smoke_90fa76d5692c49ab94723477ac619e62`, chứa 3 dòng tổng hợp giả lập (không phải dữ liệu NYC). Ghi cùng batch hai lần với khóa và timestamp cố định: vẫn đúng 3 dòng. Point get cả 3 dòng khớp nội dung, range scan cho vùng 001 trả đúng 2 dòng. Bảng users không bị sửa.

Sau `docker restart --timeout 60 hbase-demo`, thời điểm StartedAt thay đổi từ `2026-10-07T06:48:25.780614744Z` thành `2026-10-07T07:10:48.441696005Z`; container ID và volume /data giữ nguyên. Chạy verify chỉ đọc, cả 3 dòng và range scan vẫn đúng. Bằng chứng: `artifacts/metrics/hbase_smoke.json` và `artifacts/metrics/hbase_restart.json`. Container hiện chạy lại bình thường. Bảng thử được giữ để minh họa.

Phạm vi kiểm chứng: dữ liệu tồn tại qua restart cùng container. Chưa kiểm tra tái tạo container mới từ volume, sao lưu/khôi phục hoặc mất máy; không suy rộng thành khả năng chịu lỗi của cụm phân tán. Cấu hình lưu ZooKeeper bền vững vẫn cần kiểm tra trước khi tái lập container trên máy khác.

Đọc lại phép thử hiện có (không ghi, không restart):

```powershell
.\.venv\Scripts\python.exe -m src.storage.smoke_hbase verify
```

Không chạy lại prepare với cùng file state; lệnh cố ý từ chối ghi đè bằng chứng. Nếu cần phép thử mới, chọn `--state artifacts/metrics/hbase_smoke_<ten_moi>.json`; cả prepare và verify phải dùng cùng đường dẫn đó. Thao tác restart là riêng, verify không tự restart; đối chiếu file hbase_restart.json khi dùng kết quả làm bằng chứng lưu bền.

##### Cấu hình Spark thử đề xuất để người dùng chốt

Giữ kế hoạch PySpark 3.5.7, Python 3.11 và Java 17 trong container Linux riêng. Bắt đầu `local[2]`, driver heap 2 GB, giới hạn container 4 GB RAM; Docker hiện thấy khoảng 7,63 GiB RAM nên cần theo dõi khi chạy cùng HBase. Đọc một tháng Parquet trước, đối soát vùng/giờ với đầu ra giai đoạn 2 rồi mới mở rộng. Đây là cấu hình thử chưa được build/nghiệm thu, không phải mô hình cụm nhiều máy. Chưa thay yêu cầu Spark hoặc nạp dữ liệu thật vào HBase.

##### Kết quả thử Spark — 07/10/2026

Người dùng đã duyệt cấu hình Spark thử ở trên. Đã tạo Dockerfile, Compose, `.dockerignore` và job `src/processing/spark_trial.py`; build image `bigdata-spark:3.5.7-py311` thành công. Phiên bản thực tế: Spark 3.5.7, Python 3.11.17, Java 17.0.20.1; driver 2 GiB, local[2], cgroup 2 CPU/4 GiB đúng cấu hình.

Kết quả từ raw tháng 01/2024:

| Chỉ tiêu | Spark | Đối soát giai đoạn 2 |
|---|---:|---|
| Raw | 2.964.624 | Khớp |
| Ngoài tháng | 18 | Khớp |
| Vùng 264/265 sau kiểm tra tháng | 12.018 | Khớp |
| Thời lượng không dương sau kiểm tra vùng | 717 | Khớp |
| Chuyến giữ lại | 2.951.871 | Khớp |
| Nhóm vùng–giờ quan sát | 76.190 | Khớp từng nhóm; 0 sai khác |

Bảy cờ chất lượng đều khớp. Tác vụ Python worker đạt. Spark ghi Parquet tổng hợp vào thư mục thử riêng; không thay dataset giai đoạn 2. Đã đọc lại các file bằng PyArrow Windows, kiểm tra toàn bộ 76.190 nhóm với CSV đối chứng. Thời gian job 22,76 giây không gồm build và không được coi là benchmark khả năng mở rộng.

Bằng chứng: `artifacts/metrics/spark_trial_2024-01.json`, `spark_environment.json`, `spark_output_readback.json`. Cách build/chạy: `docker/spark/README.md`. Container job tự kết thúc và được xóa bằng --rm; image và đầu ra vẫn còn, HBase vẫn chạy. Đây chưa phải luồng Spark → HBase, chưa kiểm chứng Spark cho cả 36 tháng hoặc ngày DST. Giai đoạn 3 còn phần tích hợp ghi/đọc dữ liệu thật và cấu hình lưu trữ HBase có thể tái lập; chưa thông báo hoàn thành toàn giai đoạn.

##### Tiêu chí nghiệm thu toàn giai đoạn

##### Tích hợp Spark → HBase đạt với mẫu 168 giờ

Người dùng đã duyệt bảng riêng `transport_demand_hourly_trial_v1`, row key `ZZZ#YYYYMMDDHH`, families d/q/m và cách biểu diễn null. Đã triển khai và chạy thành công: vùng 161, `[2024-01-01, 2024-01-08)`, 168 dòng; hai lượt ghi đều đối chiếu từng cell thành công, không nhân đôi dòng. Python Windows đọc lại độc lập khớp toàn bộ Parquet nguồn, 26.365 chuyến. Tổng 19 kiểm thử đạt. Chi tiết và lệnh đọc thử: [THIET_KE_HBASE_THU.md](#thiet-ke-hbase-thu).

Bằng chứng tại `artifacts/metrics/spark_hbase_trial.json` và `hbase_windows_readback.json`. Chưa nạp toàn bộ 6,9 triệu dòng. Null/DST đã có unit tests codec nhưng chưa có mẫu tích hợp HBase tương ứng. Cấu hình HBase tái lập, lưu ZooKeeper và khôi phục sang container mới vẫn chưa nghiệm thu; do đó chưa chốt hoàn thành giai đoạn 3 hoặc tạo bản tổng kết hoàn thành.

##### Checklist nghiệm thu

- Có kết quả Spark đọc/tổng hợp và đối chiếu đúng với dữ liệu giai đoạn 2.
- Có bằng chứng ghi/đọc/scan HBase và lưu bền qua restart.
- Luồng tích hợp thử có thể chạy lại, không tạo bản ghi logic trùng.
- Có hướng dẫn và cấu hình tái lập, ghi rõ chế độ chạy thực tế và giới hạn.
- Tạo `TONG_KET_GIAI_DOAN_3.md` với công việc, kết quả, bằng chứng, vấn đề còn lại trước khi thông báo hoàn thành.


<a id="khao-sat-du-lieu"></a>

## KHAO_SAT_DU_LIEU

### Khảo sát dữ liệu Yellow Taxi tháng 01 năm 2024

#### Kết quả thực tế

Đã đọc toàn bộ **2.964.624 dòng, 19 cột**, 3 row group; file gốc 49.961.641 byte. SHA256 trước/sau giống nhau. Môi trường: Python 3.11.17, PyArrow 19.0.1. Đọc theo lô 32.768 dòng, không lấy mẫu để suy ra các số liệu dưới đây.

| Quan sát | Số dòng / giá trị | Diễn giải |
|---|---:|---|
| Thiếu thời điểm đón hoặc trả | 0 ở mỗi cột | Không cần điền thiếu timestamp trong file này |
| Thiếu mã vùng đón hoặc trả | 0 ở mỗi cột | Không đồng nghĩa mọi mã vùng đều hợp lệ |
| Thiếu passenger_count | 140.162 (khoảng 4,73%) | Cần phân biệt đếm chuyến với đếm hành khách |
| Thiếu RatecodeID, store_and_fwd_flag, congestion_surcharge, Airport_fee | Mỗi cột 140.162 | Chưa kiểm tra chúng có thiếu trên cùng các dòng không |
| Thời điểm đón ngoài tháng 01/2024 | 18 | 15 trước tháng, 3 từ 01/02 trở đi |
| Trả khách trước lúc đón | 56 | Cần kiểm tra mẫu trước khi quyết định xử lý |
| Trả khách đúng lúc đón | 814 | Không tự động kết luận chuyến không tồn tại |
| Quãng đường bằng 0 | 60.371 | Cần xem cùng thời gian và các trường khác |
| Số hành khách bằng 0 | 31.465 | Là số 0 được ghi nhận, khác với null |
| Tổng tiền âm | 35.504 | Chưa xác định nguyên nhân; không sửa thành trị tuyệt đối |
| Trùng toàn bộ giá trị 19 cột | 0 bản sao dư | Không loại trừ việc cùng chuyến bị ghi khác giá trị |
| Quãng đường lớn nhất | 312.722,3 mile | Bất thường cần khảo sát; chưa đặt ngưỡng loại |

Thời điểm đón trải từ `2002-12-31 22:59:39` đến `2024-02-01 00:01:15`. Đây là timestamp thực sự có trong file mang tên 01/2024, không phải bằng chứng nguồn có dữ liệu lịch sử đầy đủ từ năm 2002. Có 2.964.606 bản ghi có thời điểm đón trong tháng 01/2024; cả 31 ngày đều có bản ghi, nhưng điều đó chưa chứng minh độ đầy đủ từng khu vực/giờ.

Đã kiểm thử chương trình bằng dữ liệu nhỏ biết trước, gồm bản trùng nằm ở hai lô khác nhau, timestamp null, trả trước đón và mốc cuối tháng loại trừ. Kiểm tra dependency bằng `pip check` thành công.

#### Quy tắc đầu tiên đã được duyệt và chạy

Đề xuất đầu tiên: khi xây tập nhu cầu tháng 01/2024, chỉ lấy thời điểm đón trong `[2024-01-01, 2024-02-01)`, chuyển 18 dòng ngoài khoảng sang dữ liệu cách ly có lý do, không xóa file gốc. Không ràng buộc thời điểm trả phải nằm trong tháng: chuyến đón cuối tháng có thể trả đầu tháng sau.

Lý do: đơn vị nhu cầu được định nghĩa theo thời điểm đón; trộn timestamp ngoài tháng sẽ làm sai phạm vi đang thử nghiệm. Đây chưa phải quy tắc tự động cho nhiều tháng; khi mở rộng cần kiểm tra bản ghi giáp tháng giữa các file để tránh bỏ sót hoặc đếm hai lần.

Đã được người dùng duyệt và thực hiện bằng `src/processing/split_pickup_month.py`. Kết quả tại `data/interim/pickup_month_2024-01/`:

- `in_month.parquet`: 2.964.606 dòng, giữ nguyên 19 cột và các giá trị.
- `outside_month.parquet`: 18 dòng, thêm cột `quarantine_reason` để giải thích vì sao cách ly.
- `audit.json`: số dòng, khoảng thời gian, phiên bản PyArrow và SHA256 đầu vào/đầu ra.

Đây là đầu ra trung gian chưa xử lý các vấn đề chất lượng khác. Có 3 kiểm thử thành công, bao gồm ranh giới tháng, giữ chuyến đón cuối tháng/trả tháng sau, giữ giá trị thiếu/âm và phát hiện trùng giữa lô trong bước khảo sát. File gốc không thay đổi.

Chạy từ thư mục gốc bằng `.\.venv\Scripts\python.exe src/processing/split_pickup_month.py`. Chương trình từ chối ghi đè thư mục đầu ra đã tồn tại; muốn chạy thử lại dùng `--output-dir data/interim/pickup_month_2024-01_rerun`. Không tự xóa đầu ra cũ.

Chưa quyết định loại các dòng thiếu passenger_count, tiền âm, quãng đường 0 hoặc thời lượng bất thường. Bước khảo sát tiếp theo đề xuất đối chiếu danh mục vùng và xem các nhóm bất thường trước khi chốt thêm quy tắc.

#### Cách chạy lại

Từ thư mục gốc, sử dụng Python của dự án:

```powershell
.\.venv\Scripts\python.exe -m pip install --no-cache-dir -r requirements-profile.txt
.\.venv\Scripts\python.exe src/ingestion/profile_yellow.py
```

Kết quả chi tiết lưu tại `artifacts/metrics/profile_2024-01.json`. Chương trình chỉ đọc dữ liệu gốc, kiểm tra SHA256 trước/sau và không tạo dữ liệu sạch. Bản ghi trùng được so sánh trên toàn bộ cột, kể cả giữa các lô; cơ sở dữ liệu SQLite tạm trên đĩa được đóng và xóa sau khi chạy xong. Cần ổ đĩa trống cho dữ liệu tạm lớn hơn file Parquet nén.

#### Ý nghĩa các cột

| Cột | Ý nghĩa và vai trò trong bài toán |
|---|---|
| VendorID | Mã đơn vị cung cấp bản ghi; phục vụ khảo sát nguồn |
| tpep_pickup_datetime | Thời điểm bắt đầu tính cước; dùng đại diện thời điểm đón |
| tpep_dropoff_datetime | Thời điểm kết thúc tính cước; kiểm tra thứ tự thời gian |
| passenger_count | Số hành khách; không phải số chuyến |
| trip_distance | Quãng đường do đồng hồ ghi nhận, đơn vị mile |
| RatecodeID | Mã biểu giá cuối chuyến |
| store_and_fwd_flag | Cờ lưu trên xe rồi mới truyền khi kết nối lại |
| PULocationID | Mã vùng đón; biến chính để tổng hợp nhu cầu |
| DOLocationID | Mã vùng trả; chưa dùng để định nghĩa nhu cầu đón |
| payment_type | Mã loại thanh toán |
| fare_amount | Tiền cước theo thời gian và quãng đường |
| extra | Các khoản phụ thu khác |
| mta_tax | Thuế MTA |
| tip_amount | Tiền tip ghi nhận; không bao gồm tip tiền mặt |
| tolls_amount | Phí cầu đường |
| improvement_surcharge | Phụ thu cải thiện dịch vụ |
| total_amount | Tổng tiền ghi nhận; không bao gồm tip tiền mặt |
| congestion_surcharge | Phụ thu ùn tắc |
| Airport_fee | Phụ thu đón tại sân bay |

Nguồn giải nghĩa: [TLC Yellow Taxi Data Dictionary](https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_yellow.pdf), bản đang công bố ngày 18/03/2025. Bảng trên mô tả 19 cột thực sự có trong file 01/2024; không thêm cột phí mới chỉ có từ năm 2025. Mã hạng mục cụ thể cần kiểm tra theo năm trước khi diễn giải.

#### Cách đọc kết quả

- `nulls` là giá trị thiếu thật; số 0 không tự động được xem là thiếu.
- Khoảng khảo sát theo thời điểm đón: từ 01/01/2024, gồm đầu mốc, đến 01/02/2024, không gồm cuối mốc. Chưa chuyển múi giờ.
- `full_row_duplicate_excess` đếm số bản sao dư sau bản đầu tiên của các hàng giống nhau toàn bộ giá trị; không chứng minh chắc chắn đó là cùng chuyến thực tế.
- Các cờ bất thường có thể chồng lấp; không cộng chúng thành tổng số dòng cần xóa.
- Mã vùng mới chỉ được thống kê, chưa đối chiếu danh mục vùng chính thức.
- Chưa quyết định ngưỡng ngoại lệ, điền thiếu hoặc loại bản ghi. Mọi quy tắc cần người dùng duyệt trước khi triển khai.


<a id="kiem-tra-ma-vung"></a>

## KIEM_TRA_MA_VUNG

### Kiểm tra mã vùng đón khách tháng 01 năm 2024

Đã đối chiếu toàn bộ 2.964.606 bản ghi sau bước giới hạn thời điểm đón. Bước kiểm tra chỉ đọc dữ liệu. Sau đó, người dùng đã duyệt bước tách mã 264/265; kết quả triển khai ghi ở cuối tài liệu.

Nguồn tham chiếu: Taxi Zone Lookup CSV liên kết từ [NYC TLC](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page), tải ngày 05/10/2026, có 265 mã không trùng. Đây là bản danh mục hiện được cung cấp, chưa xác minh là snapshot lịch sử tháng 01/2024.

| Nhóm | Số chuyến | Ý nghĩa |
|---|---:|---|
| Có tên khu vực cụ thể trong danh mục | 2.952.588 | Có thể xác định vùng theo danh mục; chưa khẳng định chuyến hợp lệ theo mọi tiêu chí |
| Mã 264: Borough Unknown, Zone N/A | 10.360 | Không xác định được khu vực cụ thể |
| Mã 265: Zone Outside of NYC | 1.658 | Nhãn ngoài NYC, không xác định được một vùng cụ thể |
| Mã null | 0 | Không có giá trị thiếu ở PULocationID |
| Mã không nằm trong danh mục | 0 | Tất cả mã đều tra được |

Có 260 mã vùng đón xuất hiện. Hai nhóm 264/265 cộng lại 12.018 chuyến, khoảng 0,4054% của tập trong tháng. Không tự suy ra khu vực từ vùng trả vì vùng trả có thể khác vùng đón.

Mã 1 có tên Newark Airport, Borough EWR, với 295 chuyến. Đây là khu vực có tên cụ thể và không được nhập chung với mã 265. Việc chỉ nghiên cứu các vùng trong NYC hay giữ các vùng có tên trong danh mục là quyết định phạm vi riêng; chưa tự loại mã 1.

#### Phương án đã được duyệt

Tách 12.018 chuyến mã 264/265 ra nhóm chưa đủ thông tin vị trí cho bài toán dự báo theo từng vùng; giữ riêng hai lý do và vẫn đưa vào báo cáo tổng số chuyến. Tập ứng viên theo vùng còn 2.952.588 dòng, chưa phải tập sạch cuối cùng.

Lý do: gộp các vị trí không xác định thành một vùng giả sẽ làm sai ý nghĩa nhu cầu theo khu vực; tự điền mã vùng có thể tạo dữ liệu không có căn cứ. Có thể giữ nhóm Unknown trên dashboard để minh bạch chất lượng nguồn, nhưng chưa đưa nhóm đó vào mô hình cho một vùng cụ thể.

Giữ mã 264/265 thành hai nhóm riêng trong phân tích tổng quan, với nhãn rõ không phải khu vực cụ thể. Sau khi người dùng đồng ý, đã tạo đầu ra riêng cho tập ứng viên và các chuyến chưa rõ vùng; không sửa file đầu vào.

#### Chạy lại và kiểm chứng

```powershell
.\.venv\Scripts\python.exe src/ingestion/check_pickup_zones.py
```

Code: `src/ingestion/check_pickup_zones.py`. Kết quả máy đọc: `artifacts/metrics/pickup_zones_2024-01.json`, gồm tần suất và tên vùng của từng mã đã xuất hiện, SHA256 hai đầu vào và hạn chế diễn giải.

Đã đối chiếu tổng các nhóm với số dòng Parquet và SHA256 trước/sau để xác nhận đầu vào không đổi. Cả 4 kiểm thử hiện tại thành công, gồm phân biệt mã không tồn tại với mã có trong bảng nhưng không rõ vị trí. Chỉ kiểm tra PULocationID; chưa kiểm tra DOLocationID hoặc các vấn đề tiền cước/thời lượng.

#### Kết quả tách đã thực hiện

| File trong data/interim/pickup_zones_2024-01 | Số dòng | Nội dung |
|---|---:|---|
| zone_candidates.parquet | 2.952.588 | Tập ứng viên theo vùng; giữ nguyên 19 cột |
| unspecified_zones.parquet | 12.018 | Toàn bộ giá trị gốc và cột quarantine_reason |
| audit.json | — | Quy tắc, số dòng, phiên bản thư viện, SHA256 đầu vào/đầu ra |

Hai lý do cách ly là `unknown_pickup_zone_264` (10.360 dòng) và `outside_nyc_unspecified_265` (1.658 dòng). Mã 1 Newark Airport được giữ. Tập ứng viên chưa phải dữ liệu sạch cuối cùng.

Đối soát từ đầu: **2.964.624 = 18 ngoài tháng + 12.018 chưa rõ vùng + 2.952.588 ứng viên**. Cả ba nhóm đều được lưu, không xóa dữ liệu raw.

Chạy từ thư mục gốc:

```powershell
.\.venv\Scripts\python.exe -m src.processing.split_pickup_zones
```

Lệnh từ chối ghi đè thư mục đầu ra đã tồn tại. Muốn chạy lại, thêm `--output-dir data/interim/pickup_zones_2024-01_rerun`. Chương trình dừng trước khi tạo đầu ra nếu gặp mã null hoặc mã ngoài danh mục vì chưa có quy tắc được duyệt cho các trường hợp đó.

Sau khi bổ sung bước tách, cả 5 kiểm thử thành công. Kiểm thử mới xác nhận giữ nguyên các giá trị null/âm ở trường khác, giữ mã 1, tách đúng 264/265 và không ghi đè kết quả có sẵn. SHA256 đầu vào/lookup không đổi.


<a id="kiem-tra-thoi-luong"></a>

## KIEM_TRA_THOI_LUONG

### Kết quả khảo sát thời lượng và phương án hoàn tất tập thử

Khảo sát trên 2.952.588 dòng ứng viên sau hai quy tắc đã duyệt: giới hạn tháng theo giờ đón và tách mã vùng 264/265. File nguồn không đổi. Kết quả đầy đủ tại `artifacts/metrics/duration_2024-01.json`.

#### Kết quả

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

#### Phương án đã quyết định

Cập nhật ngày 06/10/2026: người dùng đã duyệt phương án cách ly 717 dòng không dương, giữ các bất thường khác. Đã triển khai và đối soát tại `DU_LIEU_THU_NGHIEM_V1.md`; các đoạn đề xuất bên dưới được giữ để giải thích lựa chọn.

Phương án đề xuất: cách ly 717 dòng thời lượng không dương cho tập thử; không sửa giờ hoặc lấy trị tuyệt đối. Còn 2.951.871 dòng nếu duyệt. Giữ nguyên những dòng có tiền âm, quãng đường 0, số hành khách thiếu và thời lượng dài, nhưng thêm cờ chất lượng để so sánh độ nhạy. Không điền số hành khách vì mục tiêu hiện tại là đếm chuyến.

Đây là lựa chọn bảo thủ về tính nhất quán thời gian, không chứng minh rằng 717 dòng không phải lượt đón thật. Vì dự báo dựa vào giờ đón, khi đánh giá cần báo cáo ảnh hưởng của việc cách ly.

Phương án thay thế: cách ly thêm 16 dòng trên 24 giờ, còn 2.951.855 dòng. Ngưỡng 24 giờ mang tính quy ước cho thử nghiệm; không có căn cứ để khẳng định mọi chuyến trên ngưỡng này đều sai. Chưa áp dụng phương án nào khi chưa nhận quyết định.

#### Phạm vi dataset

Tháng 01/2024 là dữ liệu thử pipeline. Phạm vi cuối chưa chốt. Đề xuất dùng năm 2024 cho phát triển và kiểm tra thêm năm 2025 sau khi pipeline ổn định. Không tải tất cả lịch sử từ 2009 theo mặc định. Dữ liệu các năm phải kiểm tra schema, độ đầy đủ và chi phí xử lý; năm dùng đánh giá tương lai không được dùng để lựa chọn mô hình trước khi đánh giá.

#### Kiểm chứng

Chạy lại: `.\.venv\Scripts\python.exe -m src.ingestion.profile_duration`.

Đã kiểm tra SHA256 trước/sau, tổng số dòng các nhóm bằng đầu vào và 7 kiểm thử thành công. Thời lượng là hiệu timestamp nguồn, chưa chuyển múi giờ. Ví dụ là các dòng đầu nhóm và 5 chuyến dài nhất, không phải mẫu ngẫu nhiên đại diện.


<a id="thiet-ke-hbase-thu"></a>

## THIET_KE_HBASE_THU

### Thiết kế thử Spark → HBase

Trạng thái: người dùng đã duyệt phương án thử 168 giờ; phép thử tích hợp đã đạt ngày 07/10/2026. Đây chưa phải nghiệm thu toàn bộ giai đoạn 3 hoặc nạp đầy đủ dữ liệu.

#### Phạm vi thử

- Bảng riêng `transport_demand_hourly_trial_v1` (thuộc namespace default, tiền tố transport chỉ là tên bảng).
- Đầu vào: lưới đã nghiệm thu `data/processed/hourly_grid_v1/2024/zone_hours.parquet`.
- Vùng 161, từ 01/01/2024 00:00 đến trước 08/01/2024 00:00: 168 dòng, đã kiểm tra bằng loader.
- Spark đọc Parquet, lọc mẫu, ghi theo partition qua HappyBase. Không collect dữ liệu toàn năm vào driver. Chỉ mẫu 168 dòng dùng để đối chiếu đầy đủ sau ghi.
- Chưa phải schema chính thức của dashboard, không ghi vào bảng `users` hoặc bảng smoke trước đó.

#### Khóa dòng

UTF-8/ASCII `ZZZ#YYYYMMDDHH`, ví dụ `161#2024010100`. Mã vùng đệm đủ 3 chữ số giúp thứ tự từ điển ổn định. Khoảng truy vấn đầu bao gồm, cuối không bao gồm: `[161#2024010100, 161#2024010800)`.

Giờ vẫn là nhãn địa phương New York của dataset, không chuyển thành UTC. Ngày DST đã được mask ở giai đoạn 2; schema phải giữ các cờ này. Cấu trúc vùng-trước phù hợp truy vấn lịch sử một vùng; chưa tối ưu cho truy vấn tất cả vùng cùng một giờ hoặc cụm có nhiều region.

#### Cột và encoding đề xuất

| Cột HBase | Nguồn / ý nghĩa |
|---|---|
| `d:recorded_trip_count` | Số chuyến được giữ; thiếu toàn nguồn thì không có cell |
| `d:target_trip_count` | Nhãn dự báo; thiếu hoặc ngày DST thì không có cell |
| `q:source_hour_missing` | Cờ thiếu toàn nguồn |
| `q:dst_day` | Cờ cả ngày DST |
| `q:zero_recorded` | Có nguồn nhưng không có chuyến được giữ ở vùng này |
| `q:model_eligible` | Đủ điều kiện làm nhãn |
| `m:dataset_version` | `hourly_grid_v1` |
| `m:timezone` | `America/New_York` (wall-clock labels) |

Số nguyên lưu dưới dạng chuỗi thập phân UTF-8, boolean là `1`/`0`. Ba column family d/q/m có max_versions=1 trong bảng thử. Không lưu chuỗi `None`, không thay null bằng 0. Nếu một cell chuyển từ có giá trị sang null khi ghi lại, phải xóa cell cũ trong cùng mutation của dòng; nếu không sẽ còn giá trị lỗi thời.

#### Kiểm chứng dự kiến

1. Unit test codec: khóa, số 0, null, DST và mutation ghi lại; mẫu tháng 1 tự nó không chứng minh xử lý null/DST đúng.
2. Thử kết nối từ container tới HBase qua endpoint phù hợp Docker Desktop.
3. Chỉ sau khi được duyệt mới tạo bảng thử, xác minh schema nếu bảng đã tồn tại.
4. Ghi 168 dòng, đọc lại từng khóa/cell và scan đúng khoảng; so với nguồn.
5. Ghi lại cùng dữ liệu, kiểm tra vẫn 168 dòng với cùng giá trị.
6. Lưu checksum đầu vào, cấu hình, số dòng và kết quả đối soát. Dừng nếu có khác biệt.

Việc nạp toàn bộ 6,9 triệu dòng vùng–giờ, schema chính thức, điều chỉnh dung lượng hoặc đổi phiên bản HBase là quyết định riêng sau kết quả thử.

#### Kết quả đã kiểm chứng

- Spark 3.5.7 local[2] đọc lưới Parquet, lọc đúng 168 giờ rồi ghi từ hai partition qua `host.docker.internal:9090` vào bảng thử đã duyệt.
- Ghi hai lượt; mỗi lượt point get 168 khóa và scan 168 dòng đều khớp từng cell, không có khóa ngoài mẫu. Bảng vẫn có đúng 168 dòng.
- Python Windows đọc qua `127.0.0.1:9090`, giải mã độc lập và đối chiếu tất cả cột với PyArrow: 0 sai khác, 26.365 chuyến.
- 19/19 unit tests đạt, gồm 4 kiểm thử codec cho zero/null/DST và dữ liệu không nhất quán. Mẫu tháng 1 không có DST: đây là kiểm chứng codec, chưa phải nghiệm thu ghi null/DST thực tế trên HBase.
- Bằng chứng: `artifacts/metrics/spark_hbase_trial.json`, `artifacts/metrics/hbase_windows_readback.json`. Bảng users và bảng synthetic smoke được giữ nguyên.

#### Lệnh sử dụng từ thư mục gốc

HBase phải chạy và expose Thrift 9090. Trên Docker Desktop, container Spark dùng `host.docker.internal` để kết nối cổng host; `localhost` bên trong container không phải máy Windows.

Chỉ đọc và kiểm tra kết quả hiện tại trên Windows:

```powershell
.\.venv\Scripts\python.exe -m src.storage.inspect_hbase_trial
```

Chạy lại thử tích hợp (ghi lại đúng phạm vi bảng thử, không nạp năm đầy đủ):

```text
docker compose -f docker/spark/compose.yaml run --rm spark /workspace/src/storage/spark_hbase_trial.py
```

Lệnh nạp từ chối schema bảng khác hoặc khóa/metadata ngoài phạm vi thử. Lần chạy lại cập nhật file metrics của phép thử hiện tại. Cấu hình cổng hiện có phục vụ máy cá nhân; bản HBase tái lập trên máy khác cần được kiểm tra riêng trước khi tuyên bố hoàn thành giai đoạn.


## Các dấu vết thử đã được thay thế

- Việc chuyển đĩa Docker sang D mới ở bước chuẩn bị và đã được người dùng dừng; không coi trạng thái `preparing` là kết quả chuyển thành công. Đĩa Docker vẫn ở C. Bản sao trước khi thử vẫn giữ tại `D:\BaiTapVeNha\BigData\DoAn_BigData\.tools\hbase-backups\before-docker-disk-move.tar`; SHA256 `64281AF68A7ED6E89AACAA08D0CDB8CCFA1693D0EA95DC16456ECF71EF59FA55`. Ba JSON riêng về bước chuẩn bị chuyển đĩa đã được bỏ khỏi metrics vì không thuộc nghiệm thu pipeline.
- Lần tạo đặc trưng đầu tiên lỗi cast trực tiếp `TIMESTAMP_NTZ` sang `BIGINT`. Đã sửa trong code và kiểm tra thành công; JSON lỗi cũ được bỏ, giữ manifest `stage4_features.json`, kiểm tra cửa sổ và nghiệm thu giai đoạn 4.
