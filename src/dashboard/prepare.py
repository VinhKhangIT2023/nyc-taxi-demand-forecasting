"""Prepare small serving snapshots from accepted artifacts without refitting ML."""
from datetime import datetime, timedelta, timezone
import hashlib
from itertools import zip_longest
import json
from pathlib import Path
import time
import urllib.request
import zipfile

import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq

from src.dashboard.service import ROOT, CONFIG, connection, forecast_key
from src.storage.verify_hbase_full import fingerprint

OUT = ROOT / 'data/processed/dashboard_v1'
METRICS = ROOT / 'artifacts/metrics'


def sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            result.update(block)
    return result.hexdigest()


def save(name, report):
    (METRICS / name).write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')


def prepare():
    final = json.loads((METRICS/'stage4_final.json').read_text())
    if not final['complete']:
        raise ValueError('Giai đoạn 4 chưa hoàn thành.')
    source_hashes = {}
    for name, expected in final['prediction_files_sha256'].items():
        if sha(ROOT/name) != expected:
            raise ValueError('Dự báo nguồn đã thay đổi: '+name)
        source_hashes[name] = expected
    for y in (2023,2024,2025):
        audit = json.loads((ROOT/f'data/processed/hourly_grid_v1/{y}/audit.json').read_text())
        if not audit['complete'] or sha(ROOT/audit['file']) != audit['sha256']:
            raise ValueError('Lưới nguồn thay đổi.')
        source_hashes[audit['file']] = audit['sha256']
    previous = METRICS/'stage5_prepared.json'
    if previous.exists():
        report = json.loads(previous.read_text())
        if report['complete'] and report['sources'] == source_hashes and all(sha(ROOT/p)==s for p,s in report['files'].items()):
            print('Serving snapshot already verified.', flush=True)
            return report
        raise ValueError('Snapshot khác nguồn; giữ bằng chứng cũ, không ghi đè.')
    OUT.mkdir(parents=True, exist_ok=True)
    tick = time.monotonic()
    pred = ds.dataset([str(ROOT/p) for p in final['prediction_files_sha256']], format='parquet').to_table().to_pandas()
    cols = ['PULocationID','pickup_hour','prediction','baseline_prediction','method','features_complete','origin_hour','model_version']
    pred = pred[cols].sort_values(['PULocationID','pickup_hour'])
    if len(pred)!=final['system']['n'] or pred.duplicated(['PULocationID','pickup_hour']).any():
        raise ValueError('Khóa/số dự báo không hợp lệ.')
    if not pred['model_version'].eq(CONFIG['model_version']).all():
        raise ValueError('Model version mismatch.')
    pq.write_table(pa.Table.from_pandas(pred, preserve_index=False), OUT/'forecasts.parquet', row_group_size=8192)
    del pred
    summaries = []
    for year in (2023,2024,2025):
        frame = pq.read_table(ROOT/f'data/processed/hourly_grid_v1/{year}/zone_hours.parquet',
            columns=['PULocationID','pickup_hour','recorded_trip_count','q_source_hour_missing','q_dst_day']).to_pandas()
        for kind, fmt in [('D','%Y%m%d'),('M','%Y%m')]:
            frame['period'] = frame['pickup_hour'].dt.strftime(fmt)
            grouped = frame.groupby(['period','PULocationID'], sort=True).agg(
                recorded=('recorded_trip_count',lambda s: s.sum(min_count=1)),
                hours=('pickup_hour','size'), missing=('q_source_hour_missing','sum'), dst=('q_dst_day','sum')).reset_index()
            grouped['kind'] = kind
            summaries.append(grouped)
        print(f'SUMMARY {year}', flush=True)
    summary = pd.concat(summaries, ignore_index=True).sort_values(['kind','period','PULocationID'])
    pq.write_table(pa.Table.from_pandas(summary, preserve_index=False), OUT/'summaries.parquet', row_group_size=8192)
    report = dict(complete=True, model_version=CONFIG['model_version'], forecast_rows=final['system']['n'],
        summary_rows=len(summary), recorded_sum=int(summary.loc[summary.kind=='D','recorded'].sum()),
        sources=source_hashes, files={str(p.relative_to(ROOT)):sha(p) for p in OUT.glob('*.parquet')},
        built_at_utc=datetime.now(timezone.utc).isoformat(), elapsed_seconds=round(time.monotonic()-tick,2))
    if report['recorded_sum'] != 126994028 or report['summary_rows'] != 297716:
        # 1096 dates * 263 zones + 36 months * 263 zones.
        raise ValueError(f'Summary count mismatch: {report}')
    save('stage5_prepared.json', report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('sources','files')}, indent=2))
    return report


def encoded(kind, row, report):
    if kind == 'forecasts':
        hour = row['pickup_hour']
        origin = row['origin_hour']
        if hour-origin != timedelta(hours=1) or row['model_version'] != CONFIG['model_version']:
            raise ValueError('Invalid origin/version.')
        key = forecast_key(int(row['PULocationID']), hour)
        cells = {b'p:value': repr(float(row['prediction'])).encode(),
            b'p:baseline': repr(float(row['baseline_prediction'])).encode(),
            b'm:method': row['method'].encode(), b'm:model_version': row['model_version'].encode(),
            b'm:origin_hour': origin.isoformat().encode(), b'm:horizon_hours': b'1',
            b'm:mode': b'historical_replay', b'm:generated_at_utc': report['built_at_utc'].encode(),
            b'q:features_complete': b'1' if row['features_complete'] else b'0'}
    else:
        zone = int(row['PULocationID'])
        key = f'{row["kind"]}#{row["period"]}#{zone:03d}'.encode()
        item = dict(zone=zone,period=row['period'],recorded=None if row['recorded'] is None else int(row['recorded']),
            hours=int(row['hours']),missing=int(row['missing']),dst=int(row['dst']))
        cells = {b'd:summary':json.dumps(item, sort_keys=True, separators=(',',':')).encode(), b'm:version':b'dashboard_v1'}
    return key,cells


def rows(kind, report):
    last = None
    for batch in pq.ParquetFile(OUT/(kind+'.parquet')).iter_batches(batch_size=8192):
        for row in batch.to_pylist():
            key,cells = encoded(kind,row,report)
            if last is not None and key<=last:
                raise ValueError('Serving keys must be unique and ordered.')
            last=key
            yield key,cells


def load():
    prepared = json.loads((METRICS/'stage5_prepared.json').read_text())
    if not prepared['complete'] or any(sha(ROOT/p)!=s for p,s in prepared['files'].items()):
        raise ValueError('Serving snapshot failed checksum.')
    prior = METRICS/'stage5_storage.json'
    if prior.exists() and json.loads(prior.read_text()).get('complete'):
        print('Storage already verified; use Verify for read-only recheck.',flush=True)
        return
    report = dict(complete=False, mode='historical_replay', tables={}, started_at_utc=datetime.now(timezone.utc).isoformat())
    save('stage5_storage.json',report)
    c = connection()
    try:
        for kind, name, families in [('forecasts',CONFIG['forecast_table'],('p','q','m')),
                                     ('summaries',CONFIG['summary_table'],('d','m'))]:
            if name.encode() not in c.tables():
                c.create_table(name,{f:{'max_versions':1} for f in families})
            table=c.table(name)
            schema=table.families()
            if set(schema)!=set(f.encode() for f in families) or any(f['max_versions']!=1 for f in schema.values()):
                raise ValueError('Unexpected serving table schema.')
            count=0;tick=time.monotonic()
            with table.batch(batch_size=500,wal=True) as batch:
                for key,cells in rows(kind,prepared):
                    batch.put(key,cells);count+=1
                    if count%250000==0:
                        print(f'LOAD {kind} {count}',flush=True)
            report['tables'][name]={'loaded_rows':count,'load_seconds':round(time.monotonic()-tick,2)}
            save('stage5_storage.json',report)
            print(f'LOADED {name}: {count}',flush=True)
        verified=verify(prepared,c)
        report.update(complete=True, verification=verified, prepared_sha256=sha(METRICS/'stage5_prepared.json'),
            wal=True, batch_size=500, ended_at_utc=datetime.now(timezone.utc).isoformat())
        save('stage5_storage.json',report)
    finally:
        c.close()


def verify(prepared=None,c=None):
    prepared=prepared or json.loads((METRICS/'stage5_prepared.json').read_text())
    owned=c is None
    c=c or connection()
    result={}
    try:
        for kind,name in [('forecasts',CONFIG['forecast_table']),('summaries',CONFIG['summary_table'])]:
            digest=hashlib.sha256();count=0;tick=time.monotonic();table=c.table(name)
            sample=[]
            for expected,actual in zip_longest(rows(kind,prepared),table.scan(batch_size=1000)):
                if expected!=actual:
                    raise AssertionError(f'Full cell comparison differs after {count} rows in {name}')
                fingerprint(digest,*actual);count+=1
                if len(sample)<3:sample.append(actual)
                if count%250000==0:print(f'VERIFY {kind} {count}',flush=True)
            # Repeat a tiny real batch: stable keys/one version, same point reads.
            if not owned:
                with table.batch(wal=True) as batch:
                    for key,cells in sample:batch.put(key,cells)
            for key,cells in sample:
                if table.row(key)!=cells:raise AssertionError('Point read mismatch.')
            result[name]=dict(rows=count,mismatches=0,content_sha256=digest.hexdigest(),
                point_reads=len(sample),elapsed_seconds=round(time.monotonic()-tick,2))
            print(f'VERIFIED {name}: {count}',flush=True)
        if owned:save('stage5_storage_recheck.json',dict(complete=True,tables=result))
        return result
    finally:
        if owned:c.close()


def geometry():
    import shapefile
    from pyproj import Transformer
    target=ROOT/'data/reference/taxi_zones.geojson'
    manifest=METRICS/'stage5_geometry.json'
    if target.exists() and manifest.exists():
        report=json.loads(manifest.read_text())
        if sha(target)==report['geojson_sha256']:
            print('Geometry already verified.',flush=True);return
        raise ValueError('Geometry changed.')
    archive=ROOT/'data/reference/taxi_zones.zip'
    request=urllib.request.Request(CONFIG['geometry_source'],headers={'User-Agent':'NYC-Taxi-Demand-Student-Project/1.0'})
    with urllib.request.urlopen(request,timeout=60) as source, archive.open('wb') as output:
        output.write(source.read(10*1024*1024))
    with zipfile.ZipFile(archive) as z:
        names=z.namelist();base=next(n[:-4] for n in names if n.endswith('.shp'))
        reader=shapefile.Reader(shp=z.open(base+'.shp'),shx=z.open(base+'.shx'),dbf=z.open(base+'.dbf'))
        prj=z.read(base+'.prj').decode()
        transformer=Transformer.from_crs(prj,'EPSG:4326',always_xy=True)
        def project(coords):
            if isinstance(coords[0],(int,float)):
                x,y=transformer.transform(coords[0],coords[1]);return [round(x,6),round(y,6)]
            return [project(c) for c in coords]
        features=[]
        for item in reader.iterShapeRecords():
            props=item.record.as_dict();zone=int(props['LocationID'])
            shape=item.shape.__geo_interface__
            shape['coordinates']=project(shape['coordinates'])
            features.append(dict(type='Feature',id=str(zone),properties={'zone':zone},geometry=shape))
    if {f['properties']['zone'] for f in features}!=set(range(1,264)):
        raise ValueError('Expected all 263 published zone boundaries.')
    target.write_text(json.dumps(dict(type='FeatureCollection',features=features),separators=(',',':')),encoding='utf-8')
    save('stage5_geometry.json',dict(complete=True,source=CONFIG['geometry_source'],archive_sha256=sha(archive),
        geojson_sha256=sha(target),features=len(features),source_crs=prj,target_crs='EPSG:4326',
        downloaded_at_utc=datetime.now(timezone.utc).isoformat()))
    print(f'Official geometry: {len(features)} features, {target.stat().st_size} bytes',flush=True)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',choices=['prepare','load','verify','geometry'])
    globals()[parser.parse_args().step]()
