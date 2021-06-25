import shutil
import subprocess  # nosec
from pathlib import Path

import rstcheck
import pandas as pd

import pytest

from ert_shared.plugins.plugin_manager import ErtPluginManager

import webviz_subsurface.ert_jobs.jobs


def test_export_connection_status(testdata_folder: Path, tmp_path: Path) -> None:

    runpath = tmp_path / Path("output")
    ert_config_file = tmp_path / "config.ert"

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

    output_file = runpath / "output.parquet"

    ert_config_file.write_text(
        f"""
ECLBASE          something
RUNPATH          {runpath}
NUM_REALIZATIONS 1
QUEUE_OPTION     LSF MAX_RUNNING 1
QUEUE_SYSTEM     LOCAL
FORWARD_MODEL    EXPORT_CONNECTION_STATUS(<INPUT>={input_file}, <OUTPUT>={output_file})
"""
    )

    subprocess.check_output(["ert", "test_run", ert_config_file], cwd=tmp_path)  # nosec

    assert output_file.exists()

    df = pd.read_parquet(output_file)
    assert list(df.columns) == ["DATE", "WELL", "I", "J", "K", "OP/SH"]


@pytest.fixture
def expected_jobs():
    """dictionary of installed jobs with location to config"""
    config_location = (
        Path(__file__).absolute().parent.parent.parent
        / "webviz_subsurface"
        / "ert_jobs"
    )
    expected_job_names = ["EXPORT_CONNECTION_STATUS"]
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
    for _, job_config in expected_jobs.items():
        # Check (loosely) that double-dashes are enclosed in quotes:
        with open(job_config) as f_handle:
            for line in f_handle.readlines():
                if not line.strip().startswith("--") and "--" in line:
                    assert '"--' in line and " --" not in line


def test_executables(expected_jobs):
    """Test executables listed in job configurations exist in $PATH"""
    for _, job_config in expected_jobs.items():
        with open(job_config) as f_handle:
            executable = f_handle.readlines()[0].split()[1]
            assert shutil.which(executable)


def test_hook_implementations_job_docs():
    """For each installed job, we require the associated
    description string to be nonempty, and valid RST markup"""

    plugin_m = ErtPluginManager(plugins=[webviz_subsurface.ert_jobs.jobs])

    print(plugin_m)
    installable_jobs = plugin_m.get_installable_jobs()

    docs = plugin_m.get_documentation_for_jobs()

    assert set(docs.keys()) == set(installable_jobs.keys())

    for job_name in installable_jobs.keys():
        desc = docs[job_name]["description"]
        assert desc != ""
        assert not list(rstcheck.check(desc))
        category = docs[job_name]["category"]
        assert category != "other"
        assert category.split(".")[0] in ACCEPTED_JOB_CATEGORIES
