"""Bad input must fail as a readable SpecError, never silently or with a raw traceback."""
import os

import pytest

from plugins import REGISTRY
from qecon.api import prepare, run_spec
from qecon.spec import SpecError

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANKS = os.path.join(ROOT, "specs", "banks.yaml")


@pytest.mark.parametrize("name", list(REGISTRY))
def test_shipped_specs_have_no_unknown_keys(name):
    prepare(os.path.join(ROOT, "specs", f"{name}.yaml"))


@pytest.mark.parametrize("override,where,hint", [
    ("fields.kapa=0.5", "fields.kapa", "kappa"),
    ("simulation.t_mx=3", "simulation.t_mx", "t_max"),
    ("uncertainty.gama=0.5", "uncertainty.gama", "gamma"),
    ("network.holding=[]", "network.holding", "holdings"),
    ("feilds.kappa=0.5", "feilds", "fields"),
])
def test_typo_is_rejected_with_a_suggestion(override, where, hint):
    with pytest.raises(SpecError) as e:
        prepare(BANKS, [override])
    assert where in str(e.value) and hint in str(e.value)


def test_override_into_a_single_value_is_a_spec_error():
    with pytest.raises(SpecError, match="single value"):
        prepare(BANKS, ["agents.n.x=1"])


def test_cloud_backend_points_to_the_hardware_adapter():
    with pytest.raises(SpecError, match="backends.hardware"):
        run_spec(BANKS, backend="cloud")
    with pytest.raises(SpecError, match="backends.hardware"):
        run_spec(BANKS, overrides=["simulation.backend=cloud"])


def test_huge_agent_count_is_rejected_without_allocating():
    with pytest.raises(SpecError, match="limit is"):
        prepare(BANKS, ["agents.n=100000", "agents.labels=null"])
