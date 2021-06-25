import subprocess  # nosec
from pathlib import Path
import json

import pandas as pd
import pyarrow as pa
import pyarrow.feather as feather


def _create_minimal_ert_config_file(tmp_path: Path, forward_model_string: str) -> Path:
    runpath = tmp_path / Path("output")
    ert_config_file = tmp_path / "config.ert"

    ert_config_file.write_text(
        f"""
ECLBASE          something
RUNPATH          {runpath}
NUM_REALIZATIONS 1
QUEUE_OPTION     LSF MAX_RUNNING 1
QUEUE_SYSTEM     LOCAL
FORWARD_MODEL    {forward_model_string}
"""
    )

    return ert_config_file


def test_export_connection_status(testdata_folder: Path, tmp_path: Path) -> None:

    input_file = (
        testdata_folder
        / "reek_history_match"
        / "realization-0"
        / "iter-0"
        / "eclipse"
        / "model"
        / "5_R001_REEK-0.UNSMRY"
    ).resolve()
    assert input_file.exists()

    output_file = tmp_path / "output.parquet"

    ert_config_file = _create_minimal_ert_config_file(
        tmp_path,
        f"EXPORT_CONNECTION_STATUS(<INPUT>={input_file}, <OUTPUT>={output_file})",
    )

    subprocess.check_output(["ert", "test_run", ert_config_file], cwd=tmp_path)  # nosec
    assert output_file.exists()

    df = pd.read_parquet(output_file)
    assert list(df.columns) == ["DATE", "WELL", "I", "J", "K", "OP/SH"]


def test_smry2arrow(testdata_folder: Path, tmp_path: Path) -> None:

    input_file = (
        testdata_folder
        / "reek_history_match"
        / "realization-0"
        / "iter-0"
        / "eclipse"
        / "model"
        / "5_R001_REEK-0.UNSMRY"
    ).resolve()
    assert input_file.exists()

    output_file = tmp_path / "output.arrow"

    ert_config_file = _create_minimal_ert_config_file(
        tmp_path, f"SMRY2ARROW(<INPUT>={input_file}, <OUTPUT>={output_file})"
    )

    subprocess.check_output(["ert", "test_run", ert_config_file], cwd=tmp_path)  # nosec
    assert output_file.exists()

    table = feather.read_table(output_file)
    assert table.shape == (291, 471)

    sample_date = table["DATE"][0]
    assert sample_date.type == pa.timestamp("ms")

    schema = table.schema
    field = schema.field("FOPT")
    field_meta = json.loads(field.metadata[b"smry_meta"])
    assert field.type == pa.float32()
    assert field_meta["unit"] == "SM3"
    assert field_meta["is_total"] == True
    assert field_meta["is_rate"] == False
    assert field_meta["is_historical"] == False

    field = schema.field("FOPR")
    field_meta = json.loads(field.metadata[b"smry_meta"])
    assert field.type == pa.float32()
    assert field_meta["unit"] == "SM3/DAY"
    assert field_meta["is_total"] == False
    assert field_meta["is_rate"] == True
    assert field_meta["is_historical"] == False

    field = schema.field("FOPTH")
    field_meta = json.loads(field.metadata[b"smry_meta"])
    assert field.type == pa.float32()
    assert field_meta["unit"] == "SM3"
    assert field_meta["is_total"] == True
    assert field_meta["is_rate"] == False
    assert field_meta["is_historical"] == True
