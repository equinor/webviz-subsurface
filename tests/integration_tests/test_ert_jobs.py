import subprocess
from pathlib import Path

# ERT_CONFIG = """
# ECLBASE     something
# RUNPATH     /private/olind/webviz/webviz-subsurface-testdata/reek_history_match/realization-0/iter-0/
# NUM_REALIZATIONS    1
# QUEUE_OPTION   LSF MAX_RUNNING 1
# QUEUE_SYSTEM LOCAL
# FORWARD_MODEL EXPORT_CONNECTION_STATUS(<INPUT>=share/results/tables/summary.parquet, <OUTPUT>=output.parquet)
# """

def test_export_connection_status(testdata_folder: Path, tmp_path: Path) -> None:

    ert_config = f"""
ECLBASE     something\n
RUNPATH     {testdata_folder}/reek_history_match/realization-0/iter-0/\n
NUM_REALIZATIONS    1\n
QUEUE_OPTION   LSF MAX_RUNNING 1\n
QUEUE_SYSTEM LOCAL\n
FORWARD_MODEL EXPORT_CONNECTION_STATUS(<INPUT>=share/results/tables/summary.parquet, <OUTPUT>=output.parquet)\n
"""
    ert_config_file = tmp_path / "ert" / "config.ert"
    with open(ert_config_file, "w") as file:
        file.write(ert_config)

    subprocess.call(  # nosec
        ["ert", "test_run", ert_config_file]
    )