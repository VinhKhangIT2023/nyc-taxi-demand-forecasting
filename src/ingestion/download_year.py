"""Download the 12 official Yellow Taxi files linked by TLC for a year."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
from urllib.request import Request, urlopen

import pyarrow.parquet as pq
from src.ingestion.check_pickup_zones import digest

PAGE = 'https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page'


def fetch(url):
    return urlopen(Request(url, headers={'User-Agent': 'BigData-course-project/1.0'}), timeout=120)


def download(url):
    path = Path('data/raw') / url.rsplit('/', 1)[1]
    if not path.exists():
        partial = path.with_suffix('.parquet.part')
        with fetch(url) as response, partial.open('wb') as stream:
            shutil.copyfileobj(response, stream, length=1024 * 1024)
        pq.ParquetFile(partial).close()
        partial.rename(path)
    with pq.ParquetFile(path) as parquet:
        result = {'file': path.as_posix(), 'url': url, 'bytes': path.stat().st_size,
                  'sha256': digest(path), 'rows': parquet.metadata.num_rows,
                  'schema': str(parquet.schema_arrow),
                  'checked_at_utc': datetime.now(timezone.utc).isoformat()}
    print(f"Ready {path.name}: {result['rows']:,} rows", flush=True)
    return result


def main(year):
    with fetch(PAGE) as response:
        html = response.read().decode('utf-8')
    urls = sorted(set(re.findall(r'https://d37ci6vzurychx\.cloudfront\.net/trip-data/yellow_tripdata_' + str(year) + r'-\d{2}\.parquet', html)))
    expected = {f'yellow_tripdata_{year}-{month:02d}.parquet' for month in range(1, 13)}
    if {url.rsplit('/', 1)[1] for url in urls} != expected:
        raise ValueError('Official page does not link all 12 expected months')
    records = []
    output = Path(f'artifacts/metrics/download_manifest_{year}.json')
    with ThreadPoolExecutor(max_workers=3) as pool:
        for future in as_completed([pool.submit(download, url) for url in urls]):
            records.append(future.result())
            output.write_text(json.dumps({'source_page': PAGE, 'year': year,
                'complete': len(records) == 12, 'files': sorted(records, key=lambda r: r['file'])}, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--year', type=int, required=True)
    main(parser.parse_args().year)
