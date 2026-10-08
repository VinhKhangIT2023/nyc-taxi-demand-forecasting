"""Read-only acceptance checks using real HBase and independent Parquet labels."""
from datetime import date, datetime
import json
import math
import time

import pyarrow.dataset as ds
import pyarrow.parquet as pq

from src.dashboard import service as api


def main():
    started=time.monotonic()
    api.status()
    prepared=json.loads((api.ROOT/'artifacts/metrics/stage5_prepared.json').read_text())
    final=json.loads((api.ROOT/'artifacts/metrics/stage4_final.json').read_text())
    features=ds.dataset(str(api.ROOT/final['predictions_directory']),format='parquet',partitioning='hive')
    checks=[]
    for zone,day in [(161,date(2025,1,7)),(132,date(2025,3,10)),(1,date(2025,12,31)),
                     (263,date(2025,1,1)),(161,date(2025,3,9)),(161,date(2025,11,2))]:
        frame=api.joined(zone,day,day)
        valid=api.evaluated(frame)
        start=datetime.combine(day,datetime.min.time())
        end=start.replace(hour=23)
        expected=features.to_table(filter=(ds.field('PULocationID')==zone)&
            (ds.field('pickup_hour')>=start)&(ds.field('pickup_hour')<=end)).to_pandas()
        if len(valid)!=len(expected):raise AssertionError('Coverage mismatch.')
        if not valid.empty:
            merged=valid.merge(
                expected.rename(columns={'PULocationID':'zone','pickup_hour':'hour'}),on=['zone','hour'],suffixes=('_hbase','_source'),validate='one_to_one')
            for a,b in [('prediction_hbase','prediction_source'),('baseline','baseline_prediction'),('actual','target_trip_count')]:
                if not merged[a].eq(merged[b]).all():raise AssertionError('Prediction/actual value mismatch.')
            independent=expected.rename(columns={'target_trip_count':'actual'})
            for column in ('prediction','baseline'):
                wanted=api.metrics(independent,'prediction' if column=='prediction' else 'baseline_prediction')
                got=api.metrics(valid,column)
                for key in ('n','mae','rmse','wape'):
                    if got[key] is None or wanted[key] is None:
                        if got[key]!=wanted[key]:raise AssertionError('Filtered metric mismatch.')
                    elif not math.isclose(got[key],wanted[key],rel_tol=1e-12,abs_tol=1e-12):
                        raise AssertionError('Filtered metric mismatch.')
        elif not frame.dst.all():
            raise AssertionError('Expected known DST exclusion.')
        checks.append({'zone':zone,'day':day.isoformat(),'hours':len(frame),'valid_forecasts':len(valid),
                       'methods':{str(k):int(v) for k,v in valid.method.value_counts().items()}})
    # Aggregate counts are checked against the immutable serving source, not hardcoded display text.
    actual=api.daily(date(2024,12,25),date(2025,1,7)).sort_values(['period','zone']).reset_index(drop=True)
    summary=pq.read_table(api.ROOT/'data/processed/dashboard_v1/summaries.parquet').to_pandas()
    expected=summary.loc[(summary.kind=='D')&(summary.period>='20241225')&(summary.period<='20250107')].sort_values(['period','PULocationID']).reset_index(drop=True)
    if not actual.recorded.eq(expected.recorded).all():raise AssertionError('Daily serving summary mismatch.')
    monthly=api.monthly()
    if len(monthly)!=36*263 or int(monthly.recorded.sum())!=prepared['recorded_sum']:
        raise AssertionError('36-month totals mismatch.')
    report=dict(complete=True,hbase_daily_rows_checked=len(actual),monthly_rows_checked=len(monthly),
        monthly_recorded_sum=int(monthly.recorded.sum()),cases=checks,elapsed_seconds=round(time.monotonic()-started,2))
    (api.ROOT/'artifacts/metrics/stage5_queries.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
