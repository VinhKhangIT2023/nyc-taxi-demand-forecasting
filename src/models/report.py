"""Create reproducible report figures and stage summary from accepted metrics."""
import csv
import json
import os
from pathlib import Path

os.environ.setdefault('MPLCONFIGDIR', str(Path('.tools/stage4-tmp/matplotlib').resolve()))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    metrics = Path('artifacts/metrics')
    accepted = json.loads((metrics / 'stage4_acceptance.json').read_text())
    if not accepted['complete']:
        raise ValueError('Stage 4 has not passed acceptance')
    selection = json.loads((metrics / 'stage4_selection.json').read_text())
    final = json.loads((metrics / 'stage4_final.json').read_text())
    features = json.loads((metrics / 'stage4_features.json').read_text())
    pilot = json.loads((metrics / 'stage4_pilot.json').read_text())
    figures = Path('reports/figures')
    figures.mkdir(parents=True, exist_ok=True)
    labels = [f'{r["model"]}\n{r["experiment"]}\ndepth={r["depth"] or "—"}' for r in selection['candidates']]
    fig, ax = plt.subplots(figsize=(12, 5), layout='constrained')
    ax.bar(range(len(labels)), [r['metrics']['mae'] for r in selection['candidates']],
           color=['#2980b9' if r['model'] == 'random_forest' else '#7f8c8d' for r in selection['candidates']])
    ax.set_xticks(range(len(labels)), labels, fontsize=8)
    ax.set_ylabel('MAE (trips / zone-hour)')
    ax.set_title('2024 validation: pooled error on identical eligible targets')
    ax.grid(axis='y', alpha=.2)
    fig.savefig(figures / 'stage4_validation.png', dpi=180)
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(9, 4), layout='constrained')
    for ax, measure in zip(axes, ('mae', 'rmse')):
        values = [final['baseline'][measure], final['system'][measure]]
        ax.bar(['Weekly baseline', 'Selected system'], values, color=['#7f8c8d', '#2980b9'])
        ax.set_title('2025 holdout: ' + measure.upper())
        ax.set_ylabel('trips / zone-hour')
        for i, value in enumerate(values):
            ax.annotate(f'{value:.3f}', (i, value), ha='center', va='bottom')
        ax.set_ylim(0, max(values) * 1.2)
    fig.savefig(figures / 'stage4_test_comparison.png', dpi=180)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(9, 4), layout='constrained')
    ax.plot([r['hour'] for r in final['by_hour']], [r['mae'] for r in final['by_hour']], marker='o')
    ax.set(xlabel='Target hour (NYC local clock)', ylabel='MAE (trips / zone-hour)',
           title='Selected system error by hour — 2025 holdout')
    ax.set_xticks(range(24))
    ax.grid(alpha=.2)
    fig.savefig(figures / 'stage4_hourly_error.png', dpi=180)
    plt.close(fig)
    table_path = metrics / 'stage4_validation_table.csv'
    with table_path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=['model', 'experiment', 'depth', 'n', 'mae', 'rmse', 'wape'])
        writer.writeheader()
        for row in selection['candidates']:
            writer.writerow({key: row.get(key) if key in row else row['metrics'][key] for key in writer.fieldnames})
    winner = selection['winner']
    best_a = min((r for r in selection['candidates'] if r['model'] == 'random_forest' and r['experiment'] == 'A_2024_only'), key=lambda r: r['metrics']['mae'])
    best_b = min((r for r in selection['candidates'] if r['model'] == 'random_forest' and r['experiment'] == 'B_add_2023'), key=lambda r: r['metrics']['mae'])
    history_improvement = 100 * (1 - best_b['metrics']['mae'] / best_a['metrics']['mae'])
    validation_seconds = sum(json.loads((metrics / name).read_text())['elapsed_seconds'] for name in selection['validation_sha256'])
    fallback = sum(n for method, n in final['methods'].items() if method.startswith('fallback_'))
    improvement = 100 * (1 - final['system']['mae'] / final['baseline']['mae']) if final['baseline']['mae'] else None
    lines = [
        '# Tổng kết giai đoạn 4 — Đặc trưng, huấn luyện và đánh giá', '',
        'Trạng thái: **đã nghiệm thu giai đoạn 4**. Xác minh lúc ' + accepted['verified_at_utc'] + '.', '',
        '## 1. Mục tiêu và phạm vi', '',
        'Dự báo số chuyến đón ghi nhận trong một giờ tiếp theo tại 263 vùng. Lưới dữ liệu 2023–2025; '
        'chọn mô hình bằng ba fold tháng 10–12/2024, đánh giá cuối trên 2025 sau khi khóa lựa chọn.', '',
        '## 2. Công việc và môi trường', '',
        '- Đã tạo các lag 1, 2, 24, 168 giờ và trung bình 24/168 giờ chỉ từ nhãn quá khứ hợp lệ; '
        'giữ DST/null và giá trị 0 quan sát được. Kiểm tra sửa tương lai, ranh giới năm, thiếu giờ và tách vùng đạt.',
        '- Baseline cùng giờ tuần trước và Random Forest 20 cây, depth 8/12; encoder chỉ fit trên train. '
        'Đã chạy đủ 12 lượt validation cho lịch sử A (2024) và B (thêm 2023).',
        '- RF thiếu đầu vào dùng baseline; baseline thiếu lag tuần dùng trung bình vùng từ train, rồi toàn train. '
        'So sánh trên cùng tập nhãn và thống kê lượt dự phòng.',
        '- Spark 3.5.7/Python 3.11/Java 17 trong image ML mở rộng NumPy 1.26.4. '
        'Windows Python 3.13, NumPy 2.2.6/Matplotlib 3.10.0 chỉ phục vụ kiểm tra và biểu đồ. '
        'File lớn và file tạm ghi trên D; HBase có thể dừng khi train.', '',
        '## 3. Kết quả', '',
        f'- Đặc trưng: {features["rows"]:,} dòng, {features["elapsed_seconds"]:.2f} giây; '
        f'{sum(r["bytes"] for r in features["files"].values()):,} byte Parquet.',
        f'- Pilot: {pilot["rf_training_rows"]:,} dòng train; {pilot["elapsed_seconds"]:.2f} giây tổng, '
        f'{pilot["training_seconds"]:.2f} giây fit. Pilot chỉ kiểm tra vận hành.',
        f'- Phương án khóa: **{winner["model"]}, {winner["experiment"]}, depth={winner["depth"]}**; '
        f'MAE validation gộp {winner["metrics"]["mae"]:.6f}.',
        f'- Tổng 12 job validation: {validation_seconds:.2f} giây. Train cuối: '
        f'{final["rf_training_rows"]:,} dòng đủ feature, {final["training_seconds"]:.2f} giây fit; '
        f'{final["elapsed_seconds"]:.2f} giây gồm đánh giá/lưu đầu ra.',
        f'- Test: {final["system"]["n"]:,} nhãn hợp lệ; macro MAE theo vùng {final["macro_zone_mae"]:.6f}.', '',
        '| Phương án | MAE (chuyến/vùng–giờ) | RMSE | WAPE |',
        '|---|---:|---:|---:|',
        f'| Baseline với cùng độ dài lịch sử | {final["baseline"]["mae"]:.6f} | {final["baseline"]["rmse"]:.6f} | {final["baseline"]["wape"]:.2%} |',
        f'| Hệ thống đã chọn, gồm dự phòng | {final["system"]["mae"]:.6f} | {final["system"]["rmse"]:.6f} | {final["system"]["wape"]:.2%} |', '',
        f'Chênh lệch MAE so với baseline trên 2025: {improvement:.2f}% cải thiện (âm nghĩa là kém hơn). '
        'Không dùng kết quả này để thay đổi mô hình đã khóa.', '',
        'Lượt dự báo theo phương pháp: `' + json.dumps(final['methods'], ensure_ascii=False) + '`.',
        f'RF dùng dự phòng {fallback:,} lần ({fallback / final["system"]["n"]:.2%} nếu RF là phương án phục vụ).', '',
        '## 4. Bằng chứng và đầu ra', '',
        '- [Nghiệm thu](../../artifacts/metrics/stage4_acceptance.json), '
        '[lựa chọn khóa](../../artifacts/metrics/stage4_selection.json), '
        '[đánh giá cuối](../../artifacts/metrics/stage4_final.json).',
        '- Metrics từng fold, bảng CSV validation, số liệu theo vùng/giờ/tháng và nhóm nhu cầu từ train. '
        'Lưu checksum code/config/feature/model/predictions, seed, tham số, thời gian.',
        '- Model ở `artifacts/models/stage4_final/`; '
        'predictions ở `data/processed/model_predictions_v1/test_2025/`, không push GitHub.',
        f'- Model nạp lại được đối chiếu toàn bộ {final["system"]["n"]:,} dự báo, gồm dự phòng, 0 sai lệch; toàn bộ nhãn test hợp lệ có dự báo. '
        f'{accepted["unit_tests_passed"]} unit tests và 5 nhóm kiểm tra cửa sổ Spark đạt.', '',
        '![Validation](../../reports/figures/stage4_validation.png)', '',
        '![Test](../../reports/figures/stage4_test_comparison.png)', '',
        '![Sai số theo giờ](../../reports/figures/stage4_hourly_error.png)', '',
        '## 5. Quyết định, hạn chế và bàn giao', '',
        'Phương án và dự phòng đã được người dùng duyệt, ghi quyết định 014. '
        'Bảng validation so sánh hai độ dài lịch sử; không mặc định thêm dữ liệu sẽ tốt hơn.', '',
        f'RF tốt nhất với 2024 có MAE validation {best_a["metrics"]["mae"]:.6f}; '
        f'thêm 2023 đạt {best_b["metrics"]["mae"]:.6f}, cải thiện {history_improvement:.2f}%. '
        'Lợi ích lịch sử bổ sung nhỏ trong ba fold này; chưa kiểm định ý nghĩa thống kê và không suy ra '
        'càng thêm nhiều năm càng tốt. Năm 2025 chỉ đánh giá phương án đã khóa.', '',
        'Các nhãn đã làm sạch hồi cứu, nguồn TLC không có tính sẵn có thời gian thực. '
        'Loại ngày DST khỏi nhãn test và công bố các dự báo dự phòng. Đánh giá một bước dùng giờ thực đã kết thúc, '
        'không chứng minh dự báo 24 giờ. Spark chạy một máy; chưa có khoảng bất định. '
        'Báo cáo Word/PPT hoàn chỉnh thuộc giai đoạn 6.', '',
        'Giai đoạn 5: tích hợp truy vấn lịch sử và dự báo vào HBase/Streamlit, chọn mốc lịch sử phát lại, '
        'hiển thị model/version/nguồn dự phòng và sai số. Không cần tải hoặc làm sạch lại dataset.', '',
        'Hướng dẫn: [MO_HINH.md](../MO_HINH.md). Chạy từng bước bằng `scripts/run_stage4.ps1`; '
        'giữ 2025 tách khỏi lựa chọn mô hình.', '']
    Path('docs/tong-ket/TONG_KET_GIAI_DOAN_4.md').write_text('\n'.join(lines), encoding='utf-8')
    print('Created figures, validation CSV and stage 4 summary from accepted evidence.')


if __name__ == '__main__':
    main()
