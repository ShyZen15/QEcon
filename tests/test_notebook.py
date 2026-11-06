"""The submission notebook must stay a true copy of the repo, and must have run clean."""
import os

import nbformat
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "QEcon_submission.ipynb")
HEADER = "%%writefile qecon_src/"


@pytest.fixture(scope="module")
def cells():
    return nbformat.read(PATH, as_version=4).cells


def code_cells(cells):
    return [c for c in cells if c.cell_type == "code"]


def embedded(cells):
    out = {}
    for cell in code_cells(cells):
        if cell.source.startswith(HEADER):
            header, _, body = cell.source.partition("\n")
            out[header[len(HEADER):]] = body
    return out


def test_every_embedded_file_matches_the_repo(cells):
    files = embedded(cells)
    assert len(files) > 30
    for path, body in files.items():
        with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
            repo = fh.read().replace("\r\n", "\n")
        assert body.strip() == repo.strip(), f"{path} changed: run python tools/build_notebook.py"


def test_every_python_module_it_needs_is_embedded(cells):
    files = embedded(cells)
    for package in ("core", "plugins", "backends"):
        for name in os.listdir(os.path.join(ROOT, package)):
            path = os.path.join(ROOT, package, name)
            if name.endswith(".py") and os.path.getsize(path):
                assert f"{package}/{name}" in files


def test_notebook_was_run_and_has_no_errors(cells):
    run = [c for c in code_cells(cells) if not c.source.startswith(HEADER)]
    assert run and all(c.execution_count for c in run)
    assert not [o for c in run for o in c.outputs if o.output_type == "error"]
    figures = sum("image/png" in o.get("data", {}) for c in run for o in c.outputs)
    assert figures == 9     # 4 scenario plots and 5 validation figures
