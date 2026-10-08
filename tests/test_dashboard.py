"""Serving boundaries, unavailable labels, zero demand and forecast provenance."""
from datetime import date, datetime, timedelta
import unittest
from unittest.mock import patch

import pandas as pd

from src.dashboard import service as api
from src.dashboard.prepare import encoded


class DashboardTest(unittest.TestCase):
    def test_range_rejects_future_reversed_and_large_scans(self):
        for a,b in [(date(2026,1,1),date(2026,1,1)),
                    (date(2025,2,1),date(2025,1,1)),
                    (date(2025,1,1),date(2025,2,1))]:
            with self.assertRaises(ValueError):api.check_range(a,b)
        api.check_range(date(2025,1,1),date(2025,1,31))

    def test_ineligible_and_unavailable_are_not_zero_labels(self):
        frame=pd.DataFrame({'actual':[0,10,None,50], 'prediction':[2,8,5,30],
                            'baseline':[1,10,4,40], 'eligible':[True,True,False,False]})
        valid=api.evaluated(frame)
        self.assertEqual(len(valid),2)
        values=api.metrics(valid)
        self.assertEqual(values['n'],2)
        self.assertEqual(values['mae'],2)
        self.assertEqual(values['rmse'],2)
        self.assertEqual(values['wape'],0.4)
        self.assertEqual(api.metrics(valid,'baseline')['mae'],0.5)

    def test_all_zero_wape_is_undefined(self):
        frame=pd.DataFrame({'actual':[0,0], 'prediction':[1,2]})
        self.assertIsNone(api.metrics(frame)['wape'])
        self.assertIsNone(api.metrics(frame.iloc[:0]))

    def test_keys_sort_across_year_and_zone_validation(self):
        a=api.forecast_key(161,datetime(2025,12,31,23))
        b=api.forecast_key(161,datetime(2026,1,1))
        self.assertLess(a,b)
        self.assertEqual(a,b'161#2025123123#stage4_final#1')
        for z in (0,264,'161'):
            with self.assertRaises(ValueError):api.hourly_key(z,datetime(2025,1,1))

    def test_forecast_payload_has_no_future_actual(self):
        hour=datetime(2025,1,1)
        row=dict(PULocationID=161,pickup_hour=hour,origin_hour=hour-timedelta(hours=1),
                 prediction=3.141592653589793,baseline_prediction=4,method='random_forest',
                 features_complete=True,model_version='stage4_final',target_trip_count=1000)
        key,cells=encoded('forecasts',row,{'built_at_utc':'2026-10-08T00:00:00+00:00'})
        self.assertEqual(float(cells[b'p:value']),row['prediction'])
        self.assertEqual(cells[b'm:mode'],b'historical_replay')
        self.assertFalse(any(b'actual' in k or b'target' in k for k in cells))
        row['origin_hour']=hour
        with self.assertRaises(ValueError):encoded('forecasts',row,{'built_at_utc':'x'})

    def test_dst_recorded_is_preserved_but_target_is_missing(self):
        values={b'd:recorded_trip_count':b'7',b'q:model_eligible':b'0',
                b'q:dst_day':b'1',b'q:source_hour_missing':b'0'}
        row=api.decode_hourly(b'161#2025030902',values)
        self.assertEqual(row['recorded'],7)
        self.assertIsNone(row['actual'])
        self.assertFalse(row['eligible'])
        self.assertTrue(row['dst'])

    def test_history_requires_complete_hours(self):
        with patch.object(api,'scan',return_value=[]):
            with self.assertRaisesRegex(ValueError,'0/24'):
                api.history(161,date(2025,1,1),date(2025,1,1))

    def test_nonfinite_predictions_are_rejected(self):
        with self.assertRaises(ValueError):
            api.metrics(pd.DataFrame({'actual':[5], 'prediction':[float('inf')]}))

    def test_missing_forecast_for_valid_hour_is_a_storage_error(self):
        actual=pd.DataFrame({'zone':[161],'hour':[datetime(2025,1,1)],'actual':[0],'eligible':[True]})
        predictions=pd.DataFrame(columns=['zone','hour','prediction'])
        with patch.object(api,'history',return_value=actual), patch.object(api,'forecasts',return_value=predictions):
            with self.assertRaisesRegex(ValueError,'Thiếu dự báo'):
                api.joined(161,date(2025,1,1),date(2025,1,1))


if __name__=='__main__':unittest.main()
