import subprocess
from pathlib import Path

ERT_CONFIG = """
DEFINE <USER>              test
DEFINE <SCRATCH>           webviz/webviz-subsurface-testdata/reek_history_match
DEFINE <CASE_DIR>          reek_history_match
RUNPATH     <SCRATCH>/<USER>/<CASE_DIR>/realization-%d/iter-0/

NUM_REALIZATIONS    1
--MAX_RUNTIME         18000
--MIN_REALIZATIONS    1
--MAX_SUBMIT          1
QUEUE_SYSTEM LOCAL

FORWARD_MODEL EXPORT_CONNECTION_STATUS(<INPUT>=share/results/tables/summary.parquet, <OUTPUT>=output.parquet)

"""

def test_export_connection_status(testdata_folder: Path) -> None:
    subprocess.call(  # nosec
        ["ert", "test_run", "config.ert"],
        cwd=testdata_folder / "webviz_examples",
    )