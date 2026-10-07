"""Explicit byte contract for the approved HBase hourly trial."""
from datetime import datetime

COUNT_COLUMNS = {'recorded_trip_count': b'd:recorded_trip_count',
                 'target_trip_count': b'd:target_trip_count'}
FLAG_COLUMNS = {'q_source_hour_missing': b'q:source_hour_missing',
                'q_dst_day': b'q:dst_day', 'q_zero_recorded': b'q:zero_recorded',
                'model_eligible': b'q:model_eligible'}


def encode(row):
    zone, hour = row['PULocationID'], row['pickup_hour']
    if type(zone) is not int or not 1 <= zone <= 263:
        raise ValueError('Expected a known project zone')
    if not isinstance(hour, datetime) or hour.tzinfo is not None or (hour.minute, hour.second, hour.microsecond) != (0, 0, 0):
        raise ValueError('Expected naive wall-clock hour')
    flags = {name: row[name] for name in FLAG_COLUMNS}
    if any(type(value) is not bool for value in flags.values()):
        raise ValueError('Flags must be booleans')
    recorded, target = row['recorded_trip_count'], row['target_trip_count']
    for value in (recorded, target):
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError('Count must be a nonnegative integer or null')
    eligible = not flags['q_source_hour_missing'] and not flags['q_dst_day']
    if flags['model_eligible'] != eligible or (recorded is None) != flags['q_source_hour_missing']:
        raise ValueError('Inconsistent source/eligibility flags')
    if target != (recorded if eligible else None) or flags['q_zero_recorded'] != (recorded == 0):
        raise ValueError('Inconsistent target/zero flags')
    puts = {column: b'1' if flags[name] else b'0' for name, column in FLAG_COLUMNS.items()}
    puts.update({b'm:dataset_version': b'hourly_grid_v1', b'm:timezone': b'America/New_York'})
    deletes = []
    for name, column in COUNT_COLUMNS.items():
        if row[name] is None:
            deletes.append(column)
        else:
            puts[column] = str(row[name]).encode('ascii')
    key = f'{zone:03d}#{hour:%Y%m%d%H}'.encode('ascii')
    return key, puts, deletes
