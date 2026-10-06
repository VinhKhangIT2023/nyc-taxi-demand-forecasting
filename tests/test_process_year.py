import json
from pathlib import Path
import tempfile
import unittest

from src.ingestion.check_pickup_zones import digest
from src.processing.process_year import resume_step


class ResumeTest(unittest.TestCase):
    def test_refuses_changed_output_or_incomplete_step(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / 'out'
            output.mkdir()
            inputs = lambda r: []
            outputs = lambda r: [('part', r['hash'])]
            run = lambda: self.fail('Completed step should not rerun')
            with self.assertRaises(ValueError):
                resume_step(output, inputs, outputs, run)
            (output / 'part').write_text('original')
            (output / 'audit.json').write_text(json.dumps({'hash': digest(output / 'part')}))
            resume_step(output, inputs, outputs, run)
            (output / 'part').write_text('changed')
            with self.assertRaises(ValueError):
                resume_step(output, inputs, outputs, run)
