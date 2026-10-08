"""Bounded HBase reads; predictions and actual observations stay separate."""
from datetime import date, datetime, timedelta
import json
import math
import os
from pathlib import Path

import happybase
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads((ROOT / 'configs/stage5_dashboard.json').read_text())
START, END = date(2023, 1, 1), date(2025, 12, 31)
METHODS = {'random_forest': 'Random Forest', 'fallback_weekly': 'Dự phòng: cùng giờ tuần trước',
           'fallback_train_zone_mean': 'Dự phòng: trung bình vùng train',
           'fallback_train_global_mean': 'Dự phòng: trung bình toàn train'}


def connection():
    return happybase.Connection(os.getenv('HBASE_HOST', '127.0.0.1'),
        port=int(os.getenv('HBASE_PORT', '19090')), timeout=10000,
        transport='buffered', protocol='binary')


def check_range(start, end, max_days=None):
    if not isinstance(start, date) or not isinstance(end, date) or not START <= start <= end <= END:
        raise ValueError('Chọn khoảng ngày hợp lệ trong 2023–2025.')
    if (end-start).days + 1 > (max_days or CONFIG['max_days']):
        raise ValueError('Mỗi truy vấn chi tiết tối đa 31 ngày; xu hướng tháng bao phủ cả 36 tháng.')


def hourly_key(zone, hour):
    if type(zone) is not int or not 1 <= zone <= 263:
        raise ValueError('Mã vùng phải thuộc 1–263.')
    if not isinstance(hour, datetime) or hour.tzinfo or hour.minute or hour.second or hour.microsecond:
        raise ValueError('Cần giờ địa phương không offset, đúng đầu giờ.')
    return f'{zone:03d}#{hour:%Y%m%d%H}'.encode('ascii')


def forecast_key(zone, hour):
    return hourly_key(zone, hour) + b'#' + CONFIG['model_version'].encode() + b'#1'


def decode_hourly(key, cells):
    return {'zone': int(key[:3]), 'hour': datetime.strptime(key[4:].decode(), '%Y%m%d%H'),
        'recorded': int(cells[b'd:recorded_trip_count']) if b'd:recorded_trip_count' in cells else None,
        'actual': int(cells[b'd:target_trip_count']) if b'd:target_trip_count' in cells else None,
        'eligible': cells[b'q:model_eligible'] == b'1',
        'dst': cells[b'q:dst_day'] == b'1', 'missing': cells[b'q:source_hour_missing'] == b'1'}


def decode_forecast(key, cells):
    return {'zone': int(key[:3]), 'hour': datetime.strptime(key[4:14].decode(), '%Y%m%d%H'),
        'prediction': float(cells[b'p:value']), 'baseline': float(cells[b'p:baseline']),
        'method': cells[b'm:method'].decode(), 'features_complete': cells[b'q:features_complete'] == b'1',
        'model_version': cells[b'm:model_version'].decode(),
        'origin_hour': datetime.fromisoformat(cells[b'm:origin_hour'].decode())}


def scan(table_name, start, stop, limit):
    c = connection()
    try:
        result = list(c.table(table_name).scan(row_start=start, row_stop=stop, limit=limit+1, batch_size=500))
        if len(result) > limit:
            raise ValueError('Truy vấn vượt giới hạn cấu hình.')
        return result
    finally:
        c.close()


def status():
    c = connection()
    try:
        names = set(c.tables())
        required = [CONFIG[k] for k in ('hourly_table', 'forecast_table', 'summary_table')]
        missing = [n for n in required if n.encode() not in names]
        if missing:
            raise ValueError('Thiếu bảng phục vụ: ' + ', '.join(missing) + '. Chạy bước Load giai đoạn 5.')
        accepted = ROOT / 'artifacts/metrics/stage5_storage.json'
        if not accepted.exists() or not json.loads(accepted.read_text())['complete']:
            raise ValueError('Bảng phục vụ chưa nạp và đối chiếu đầy đủ. Chạy bước Load trước.')
        return {'connected': True, 'host': os.getenv('HBASE_HOST', '127.0.0.1'),
                'port': int(os.getenv('HBASE_PORT', '19090'))}
    finally:
        c.close()


def history(zone, start, end):
    check_range(start, end)
    a, b = datetime.combine(start, datetime.min.time()), datetime.combine(end+timedelta(days=1), datetime.min.time())
    # The exclusive endpoint may be 2026-01-01; it is a bound, not an extra source hour.
    rows = scan(CONFIG['hourly_table'], hourly_key(zone, a), hourly_key(zone, b), 31*24)
    expected = ((end-start).days+1)*24
    if len(rows) != expected:
        raise ValueError(f'Lịch sử chưa đầy đủ: {len(rows)}/{expected} giờ. Không tự điền 0.')
    return pd.DataFrame([decode_hourly(k, v) for k, v in rows])


def forecasts(zone, start, end):
    check_range(start, end)
    a, b = datetime.combine(start, datetime.min.time()), datetime.combine(end+timedelta(days=1), datetime.min.time())
    rows = scan(CONFIG['forecast_table'], hourly_key(zone, a), hourly_key(zone, b), 31*24)
    return pd.DataFrame([decode_forecast(k, v) for k, v in rows],
        columns=['zone', 'hour', 'prediction', 'baseline', 'method', 'features_complete', 'model_version', 'origin_hour'])


def daily(start, end):
    check_range(start, end)
    rows = scan(CONFIG['summary_table'], f'D#{start:%Y%m%d}#'.encode(),
        f'D#{end+timedelta(days=1):%Y%m%d}#'.encode(), 31*263)
    expected = ((end-start).days+1)*263
    if len(rows) != expected:
        raise ValueError(f'Tổng hợp chưa đầy đủ: {len(rows)}/{expected} dòng.')
    return pd.DataFrame([json.loads(v[b'd:summary']) for _, v in rows])


def monthly():
    rows = scan(CONFIG['summary_table'], b'M#202301#', b'M#202601#', 36*263)
    if len(rows) != 36*263:
        raise ValueError('Thiếu tổng hợp 36 tháng.')
    return pd.DataFrame([json.loads(v[b'd:summary']) for _, v in rows])


def snapshot(day, hour):
    check_range(day, day)
    target = datetime.combine(day, datetime.min.time()).replace(hour=hour)
    c = connection()
    try:
        keys = [hourly_key(z, target) for z in range(1,264)]
        values = c.table(CONFIG['hourly_table']).rows(keys)
        if len(values) != 263:
            raise ValueError('Thiếu vùng trong giờ đang xem.')
        return pd.DataFrame([decode_hourly(k,v) for k,v in values])
    finally:
        c.close()


def evaluated(frame):
    # Drop unavailable labels explicitly; neither null nor DST becomes an actual zero.
    return frame.loc[frame['eligible'] & frame['actual'].notna() & frame['prediction'].notna()].copy()


def metrics(frame, column='prediction'):
    if frame.empty:
        return None
    actual = frame['actual'].to_numpy(dtype=float)
    prediction = frame[column].to_numpy(dtype=float)
    if not all(math.isfinite(x) for x in actual) or not all(math.isfinite(x) for x in prediction):
        raise ValueError('Độ đo chỉ nhận nhãn và dự báo hữu hạn.')
    error = prediction - actual
    absolute = float(abs(error).sum())
    total = float(actual.sum())
    return {'n': len(frame), 'mae': absolute/len(frame),
        'rmse': float((error**2).mean()**0.5), 'wape': absolute/total if total else None}


def joined(zone, start, end):
    actual = history(zone, start, end)
    pred = forecasts(zone, start, end)
    result = actual.merge(pred, on=['zone','hour'], how='left', validate='one_to_one')
    if start >= date(2025,1,1) and (result['eligible'] & result['prediction'].isna()).any():
        raise ValueError('Thiếu dự báo cho giờ có nhãn hợp lệ; kiểm tra lại bảng forecast.')
    return result


def zones():
    f = ROOT / 'data/reference/taxi_zone_lookup.csv'
    if not f.exists():
        raise ValueError('Chưa có danh mục Taxi Zone Lookup. Xem docs/DU_LIEU.md.')
    return pd.read_csv(f).query('LocationID <= 263')
