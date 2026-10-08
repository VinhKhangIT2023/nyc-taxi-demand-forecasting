"""Check existing Spark ML image with synthetic data; never read taxi labels."""
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile

from pyspark.ml import Pipeline, PipelineModel
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.regression import RandomForestRegressor
from pyspark.sql import SparkSession


def main():
    output = Path('/workspace/artifacts/metrics/stage4_spark_smoke.json')
    report = {'complete': False, 'scope': 'synthetic infrastructure check, not a taxi experiment',
              'checked_at_utc': datetime.now(timezone.utc).isoformat()}
    spark = SparkSession.builder.appName('stage4-infrastructure-smoke').getOrCreate()
    spark.sparkContext.setLogLevel('WARN')
    try:
        data = spark.createDataFrame([(float(i), float(i * 2)) for i in range(24)], ['x', 'label'])
        pipeline = Pipeline(stages=[VectorAssembler(inputCols=['x'], outputCol='features'),
                                    RandomForestRegressor(numTrees=2, maxDepth=2, seed=42)])
        model = pipeline.fit(data)
        before = [(row.x, row.prediction) for row in model.transform(data).orderBy('x').collect()]
        with tempfile.TemporaryDirectory(dir='/workspace/.tools') as folder:
            model.save(folder + '/model')
            loaded = PipelineModel.load(folder + '/model')
            after = [(row.x, row.prediction) for row in loaded.transform(data).orderBy('x').collect()]
        if before != after:
            raise ValueError('Model reload changed predictions')
        report.update(complete=True, spark_version=spark.version, rows=len(before),
                      save_reload_predictions_equal=True)
    except Exception as error:
        report['error'] = str(error)
        raise
    finally:
        output.write_text(json.dumps(report, indent=2) + '\n')
        spark.stop()
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
