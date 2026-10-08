"""Record stage 5 acceptance only after real storage, query and UI checks pass."""
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from src.dashboard.prepare import sha
from src.dashboard.service import ROOT


def main():
    evidence={}
    for name in ['stage5_prepared.json','stage5_storage.json','stage5_storage_recheck.json','stage5_queries.json',
                 'stage5_geometry.json','stage5_browser.json','stage5_error_state.json']:
        path=ROOT/'artifacts/metrics'/name
        item=json.loads(path.read_text(encoding='utf-8'))
        if not item['complete']:raise ValueError('Incomplete evidence: '+name)
        evidence[name]=sha(path)
    final=json.loads((ROOT/'artifacts/metrics/stage4_final.json').read_text())
    if any(sha(ROOT/name)!=expected for name,expected in final['model_files_sha256'].items()):
        raise ValueError('Stage 4 model changed.')
    temporary=ROOT/'.tools/stage5-tmp'
    temporary.mkdir(parents=True,exist_ok=True)
    os.environ['TMP']=os.environ['TEMP']=str(temporary)
    import tempfile
    tempfile.tempdir=str(temporary)
    output=io.StringIO()
    result=unittest.TextTestRunner(stream=output).run(unittest.defaultTestLoader.discover(str(ROOT/'tests')))
    print(output.getvalue())
    if not result.wasSuccessful():raise ValueError('Unit tests failed.')
    checked=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True,text=True)
    if checked.returncode:raise ValueError(checked.stdout+checked.stderr)
    sources=[ROOT/'src/dashboard'/f for f in ['app.py','service.py','prepare.py','verify.py','acceptance.py']]
    sources += [ROOT/'configs/stage5_dashboard.json',ROOT/'.streamlit/config.toml',
                ROOT/'requirements.txt',ROOT/'requirements/requirements-stage5-windows-lock.txt',ROOT/'scripts/run_stage5.ps1']
    report=dict(complete=True,stage=5,checked_at_utc=datetime.now(timezone.utc).isoformat(),
        scope='HBase-backed historical replay; one-hour forecasts and actual comparison, 2025',
        unit_tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),
        python_version=sys.version.split()[0],pip_check=checked.stdout.strip(),
        model_unchanged=True,evidence_sha256=evidence,
        implementation_sha256={str(p.relative_to(ROOT)):sha(p) for p in sources},
        limitations=['Historical replay, not live streaming','Forecasts are precomputed from the accepted model',
                      'One-hour horizon only','TikTok videos were inaccessible; clip-specific requirements not verified'])
    (ROOT/'artifacts/metrics/stage5_acceptance.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
