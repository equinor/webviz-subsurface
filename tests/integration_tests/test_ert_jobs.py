import json
import shutil
import subprocess  # nosec
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pytest
from ert_shared.plugins.plugin_manager import ErtPluginManager
from pyarrow import feather

import webviz_subsurface.ert_jobs.jobs


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

    eclbase = (
        testdata_folder
        / "01_drogon_ahm"
        / "realization-0"
        / "iter-0"
        / "eclipse"
        / "model"
        / "DROGON-0"
    ).resolve()
    assert eclbase.with_suffix(".UNSMRY").exists()

    ert_config_file = _create_minimal_ert_config_file(
        tmp_path,
        f"WELL_CONNECTION_STATUS(<ECLBASE>={eclbase})",
    )

    subprocess.check_output(["ert", "test_run", ert_config_file], cwd=tmp_path)  # nosec
    output_file = (
        tmp_path
        / "output"
        / "share"
        / "results"
        / "tables"
        / "well_connection_status.parquet"
    )
    assert output_file.exists()

    df = pd.read_parquet(output_file)
    assert list(df.columns) == ["DATE", "WELL", "I", "J", "K", "OP/SH"]


def test_smry2arrow(testdata_folder: Path, tmp_path: Path) -> None:

    eclbase = (
        testdata_folder
        / "01_drogon_ahm"
        / "realization-0"
        / "iter-0"
        / "eclipse"
        / "model"
        / "DROGON-0"
    ).resolve()
    assert eclbase.with_suffix(".UNSMRY").exists()

    output_file = tmp_path / "output.arrow"

    ert_config_file = _create_minimal_ert_config_file(
        tmp_path, f"SMRY2ARROW(<ECLBASE>={eclbase})"
    )
    output_file = tmp_path / "output" / "share" / "results" / "tables" / "unsmry.arrow"
    subprocess.check_output(["ert", "test_run", ert_config_file], cwd=tmp_path)  # nosec

    assert output_file.exists()

    table = feather.read_table(output_file)
    assert table.shape == (243, 932)

    sample_date = table["DATE"][0]
    assert sample_date.type == pa.timestamp("ms")

    schema = table.schema
    field = schema.field("FOPT")
    field_meta = json.loads(field.metadata[b"smry_meta"])
    assert field.type == pa.float32()
    assert field_meta["unit"] == "SM3"
    assert field_meta["is_total"] is True
    assert field_meta["is_rate"] is False
    assert field_meta["is_historical"] is False

    field = schema.field("FOPR")
    field_meta = json.loads(field.metadata[b"smry_meta"])
    assert field.type == pa.float32()
    assert field_meta["unit"] == "SM3/DAY"
    assert field_meta["is_total"] is False
    assert field_meta["is_rate"] is True
    assert field_meta["is_historical"] is False

    field = schema.field("FOPTH")
    field_meta = json.loads(field.metadata[b"smry_meta"])
    assert field.type == pa.float32()
    assert field_meta["unit"] == "SM3"
    assert field_meta["is_total"] is True
    assert field_meta["is_rate"] is False
    assert field_meta["is_historical"] is True


@pytest.fixture(name="expected_jobs")
def expected_jobs_fixture():
    """dictionary of installed jobs with location to config"""
    config_location = (
        Path(__file__).absolute().parent.parent.parent
        / "webviz_subsurface"
        / "ert_jobs"
    )
    expected_job_names = ["WELL_CONNECTION_STATUS", "SMRY2ARROW"]
    return {
        name: str(config_location / "config_jobs" / name) for name in expected_job_names
    }


# Avoid category inflation. Add to this list when it makes sense:
ACCEPTED_JOB_CATEGORIES = ["modelling", "utility"]


def test_hook_implementations(expected_jobs):
    """Test that we have the correct set of jobs installed,
    nothing more, nothing less"""
    plugin_m = ErtPluginManager(plugins=[webviz_subsurface.ert_jobs.jobs])

    installable_jobs = plugin_m.get_installable_jobs()
    for wf_name, wf_location in expected_jobs.items():
        assert wf_name in installable_jobs
        assert installable_jobs[wf_name].endswith(wf_location)
        assert Path(installable_jobs[wf_name]).exists()

    assert set(installable_jobs.keys()) == set(expected_jobs.keys())

    expected_workflow_jobs = {}
    installable_workflow_jobs = plugin_m.get_installable_workflow_jobs()
    for wf_name, wf_location in expected_workflow_jobs.items():
        assert wf_name in installable_workflow_jobs
        assert installable_workflow_jobs[wf_name].endswith(wf_location)

    assert set(installable_workflow_jobs.keys()) == set(expected_workflow_jobs.keys())


def test_job_config_syntax(expected_jobs):
    """Check for syntax errors made in job configuration files"""
    for job_config in expected_jobs.values():
        # Check (loosely) that double-dashes are enclosed in quotes:
        for line in Path(job_config).read_text().splitlines():
            if not line.strip().startswith("--") and "--" in line:
                assert '"--' in line and " --" not in line


def test_executables(expected_jobs):
    """Test executables listed in job configurations exist in $PATH"""
    for job_config in expected_jobs.values():
        executable = Path(job_config).read_text().splitlines()[0].split()[1]
        assert shutil.which(executable)


def test_hook_implementations_job_docs():
    """For each installed job, we require the associated
    description string to be nonempty, and valid RST markup"""

    plugin_m = ErtPluginManager(plugins=[webviz_subsurface.ert_jobs.jobs])

    installable_jobs = plugin_m.get_installable_jobs()

    docs = plugin_m.get_documentation_for_jobs()

    assert set(docs.keys()) == set(installable_jobs.keys())

    for job_name in installable_jobs.keys():
        desc = docs[job_name]["description"]
        assert desc != ""
        category = docs[job_name]["category"]
        assert category != "other"
        assert category.split(".")[0] in ACCEPTED_JOB_CATEGORIES
