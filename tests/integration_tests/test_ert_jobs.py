import subprocess  # nosec
from pathlib import Path

import pandas as pd


def test_export_connection_status(testdata_folder: Path, tmp_path: Path) -> None:

    runpath = f"{testdata_folder}/reek_history_match/realization-0/iter-0"
    ert_config = f"""
ECLBASE     something\n
RUNPATH     {runpath}\n
NUM_REALIZATIONS    1\n
QUEUE_OPTION   LSF MAX_RUNNING 1\n
QUEUE_SYSTEM LOCAL\n
FORWARD_MODEL EXPORT_CONNECTION_STATUS(<INPUT>=share/results/tables/summary.parquet, <OUTPUT>=output.parquet)\n
"""

    ert_config_file = tmp_path / "config.ert"
    with open(ert_config_file, "w") as file:
        file.write(ert_config)

    subprocess.check_output(  # nosec
        ["ert", "test_run", ert_config_file], stderr=subprocess.STDOUT
    )

    output_file = Path(f"{runpath}/output.parquet")
    assert output_file.exists()

    df = pd.read_parquet(output_file)
    assert list(df.columns) == ["DATE", "WELL", "I", "J", "K", "OP/SH"]
