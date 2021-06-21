import subprocess  # nosec
from pathlib import Path

import pandas as pd


def test_export_connection_status(testdata_folder: Path, tmp_path: Path) -> None:

    runpath = tmp_path / Path("output")
    ert_config_file = tmp_path / "config.ert"

    input_file = (
        testdata_folder
        / "reek_history_match"
        / "realization-0"
        / "iter-0"
        / "share"
        / "results"
        / "tables"
        / "summary.parquet"
    ).resolve()
    assert input_file.exists()

    output_file = runpath / "output.parquet"

    ert_config = f"""
ECLBASE          something
RUNPATH          {runpath}
NUM_REALIZATIONS 1
QUEUE_OPTION     LSF MAX_RUNNING 1
QUEUE_SYSTEM     LOCAL
FORWARD_MODEL    EXPORT_CONNECTION_STATUS(<INPUT>={input_file}, <OUTPUT>={output_file})
"""

    ert_config_file.write_text(ert_config)

    subprocess.check_output(["ert", "test_run", ert_config_file], cwd=tmp_path)  # nosec

    assert output_file.exists()

    df = pd.read_parquet(output_file)
    assert list(df.columns) == ["DATE", "WELL", "I", "J", "K", "OP/SH"]
