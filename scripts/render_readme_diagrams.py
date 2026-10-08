"""Generate the architecture SVG using only the Python standard library."""
from html import escape
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / 'docs' / 'assets'
INK, MUTED = '#e2e8f0', '#a8b7cc'
BLUE, GREEN, PURPLE, ORANGE = '#60a5fa', '#4ade80', '#c4b5fd', '#fbbf24'


class Diagram:
    def __init__(self, height, title, desc):
        self.parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="{height}" viewBox="0 0 1120 {height}" role="img" aria-labelledby="title desc">',
                      f'<title id="title">{escape(title)}</title><desc id="desc">{escape(desc)}</desc>',
                      '<defs><linearGradient id="bg" x2="1" y2="1"><stop stop-color="#101b30"/><stop offset="1" stop-color="#0b1220"/></linearGradient><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10z" fill="#7891b5"/></marker></defs>',
                      f'<rect width="1120" height="{height}" rx="24" fill="url(#bg)"/><g font-family="Segoe UI, Arial, sans-serif">']

    def text(self, x, y, value, size=18, color=INK, weight=400, mono=False):
        family = ' font-family="Consolas, monospace"' if mono else ''
        self.parts.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{color}"{family}>{escape(value)}</text>')

    def rect(self, x, y, w, h, fill, stroke='none', rx=16):
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}"/>')

    def card(self, x, y, w, h, color, tag, title):
        self.rect(x, y, w, h, '#162238', '#2b3d56')
        self.rect(x + 18, y + 18, 5, 33, color, rx=2)
        self.text(x + 36, y + 35, tag, 14, color, 700)
        self.text(x + 20, y + 75, title, 24, INK, 600)

    def path(self, value, arrow=False, color='#3b506e'):
        extra = ' marker-end="url(#arrow)"' if arrow else ''
        if arrow:
            color = '#7891b5'
        self.parts.append(f'<path d="{value}" fill="none" stroke="{color}" stroke-width="2.5" stroke-linejoin="round"{extra}/>')

    def save(self, name):
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / name).write_text('\n'.join(self.parts + ['</g></svg>']) + '\n', encoding='utf-8')


def architecture():
    d = Diagram(744, 'Kiến trúc NYC Taxi Demand Forecasting', 'TLC → làm sạch → lưới vùng–giờ → Spark ML → HBase → dashboard. HBase cũng lưu lịch sử và tổng hợp. Nhãn thực tế được đọc riêng khi kiểm chứng.')
    d.text(36, 48, 'TỪ CHUYẾN ĐI ĐẾN DỰ BÁO', 27, INK, 700)
    d.text(36, 79, '36 tháng dữ liệu · xử lý batch · kiểm chứng trên lịch sử năm 2025', 18, MUTED)
    cards = [
        (36, 114, BLUE, 'NGUỒN', 'NYC TLC · Yellow Taxi', ['01/2023 → 12/2025', '128.202.548 chuyến nguồn', 'Parquet + danh mục 263 vùng']),
        (395, 114, GREEN, 'XỬ LÝ', 'Làm sạch & tổng hợp', ['PyArrow + Spark', '126.994.028 chuyến sạch', 'Kiểm tra schema, giờ, vùng, DST']),
        (754, 114, PURPLE, 'LỊCH SỬ', 'Lưới vùng × giờ', ['6.917.952 dòng · 263 vùng', 'Phân biệt số 0 và giá trị thiếu', 'Chuyến chi tiết vẫn giữ ở Parquet']),
        (754, 414, PURPLE, 'MÔ HÌNH', 'Spark ML · Random Forest', ['Baseline: cùng giờ tuần trước', 'RF: 20 cây · maxDepth 12', 'Train 2023–2024 · test 2025', 'Đặc trưng chỉ dùng quá khứ']),
        (395, 414, ORANGE, 'PHỤC VỤ', 'Apache HBase', ['Lịch sử · dự báo · tổng hợp', 'Khóa vùng / thời gian', 'Thrift · batch put · scan giới hạn', 'Lưu bền trong Docker volume']),
        (36, 414, BLUE, 'GIAO DIỆN', 'Streamlit · Plotly', ['5 trang · Light / Dark', 'Dự báo 1 giờ + số thực tế', 'Bản đồ · bộ lọc · xuất CSV', 'Phát lại lịch sử · không trực tiếp']),
    ]
    for x, y, color, tag, title, lines in cards:
        d.card(x, y, 330, 196 if y == 114 else 218, color, tag, title)
        for i, value in enumerate(lines):
            d.text(x + 20, y + 107 + i * 29, value, 17 if i > 1 else 18, color if i == 1 else MUTED if i == len(lines) - 1 else INK, 600 if i == 1 else 400)
    for path in ['M366 210 H391', 'M725 210 H750', 'M919 310 V410', 'M810 310 V345 H560 V410', 'M754 526 H729', 'M395 526 H370']:
        d.path(path, arrow=True)
    d.text(935, 373, 'đặc trưng', 15, MUTED)
    d.text(582, 336, 'lịch sử + tổng hợp', 15, MUTED)
    d.path('M36 664 H1084')
    d.text(36, 695, 'BATCH', 14, GREEN, 700)
    d.text(105, 695, 'Dự báo tính sẵn; chọn giờ trên Web không huấn luyện lại.', 17, MUTED)
    d.text(36, 724, 'KIỂM CHỨNG', 14, BLUE, 700)
    d.text(150, 724, 'Đọc nhãn thực tế riêng, không đưa nhãn tương lai vào đặc trưng.', 17, MUTED)
    d.save('architecture.svg')


if __name__ == '__main__':
    architecture()
    print('Rendered docs/assets/architecture.svg.')
