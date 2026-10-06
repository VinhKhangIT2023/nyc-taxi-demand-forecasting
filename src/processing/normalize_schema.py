"""Common schema for 2023–2025; preserve the new 2025 fee as nullable."""
import pyarrow as pa
import pyarrow.parquet as pq


def common_schema():
    fields = [('VendorID', pa.int64()), ('tpep_pickup_datetime', pa.timestamp('us')),
              ('tpep_dropoff_datetime', pa.timestamp('us')), ('passenger_count', pa.float64()),
              ('trip_distance', pa.float64()), ('RatecodeID', pa.float64()),
              ('store_and_fwd_flag', pa.large_string()), ('PULocationID', pa.int64()),
              ('DOLocationID', pa.int64()), ('payment_type', pa.int64())]
    fields += [(name, pa.float64()) for name in ['fare_amount', 'extra', 'mta_tax', 'tip_amount',
               'tolls_amount', 'improvement_surcharge', 'total_amount', 'congestion_surcharge', 'Airport_fee', 'cbd_congestion_fee', 'duration_minutes']]
    from src.processing.finalize_trial import FLAGS
    fields += [(name, pa.bool_()) for name in FLAGS]
    return pa.schema(fields)


def normalize(table):
    names = ['Airport_fee' if name == 'airport_fee' else name for name in table.column_names]
    if len(set(names)) != len(names):
        raise ValueError('Conflicting airport fee aliases')
    table = table.rename_columns(names)
    # Not supplied by older source schemas; absence is not a recorded zero fee.
    if 'cbd_congestion_fee' not in names:
        table = table.append_column('cbd_congestion_fee', pa.nulls(table.num_rows, type=pa.float64()))
        names = table.column_names
    target = common_schema()
    if set(names) != set(target.names):
        raise ValueError(f'Unexpected fields: {set(names) ^ set(target.names)}')
    # safe=True rejects integer-to-float values outside the exactly representable range.
    return table.select(target.names).cast(target, safe=True)


def normalize_file(source, destination):
    if destination.exists():
        raise FileExistsError(destination)
    source_rows = 0
    with pq.ParquetFile(source) as reader, pq.ParquetWriter(destination, common_schema()) as writer:
        for batch in reader.iter_batches(batch_size=32768):
            result = normalize(pa.Table.from_batches([batch]))
            writer.write_table(result)
            source_rows += result.num_rows
    assert pq.ParquetFile(destination).metadata.num_rows == source_rows
