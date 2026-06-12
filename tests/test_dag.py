import pytest

from src.dag import build_dag, resolve_waves, detect_cycle, CycleError
from src.models import Task


def make_task(id, deps=None):
    return Task(
        id=id,
        description=f"task {id}",
        task_type="reasoning",
        complexity="low",
        dependencies=deps or [],
    )


def wave_ids(waves):
    return [{t.id for t in wave} for wave in waves]


def test_linear_chain_three_waves():
    tasks = [make_task("t1"), make_task("t2", ["t1"]), make_task("t3", ["t2"])]
    waves = resolve_waves(build_dag(tasks))
    assert wave_ids(waves) == [{"t1"}, {"t2"}, {"t3"}]


def test_independent_tasks_one_wave():
    tasks = [make_task("t1"), make_task("t2")]
    waves = resolve_waves(build_dag(tasks))
    assert wave_ids(waves) == [{"t1", "t2"}]


def test_diamond_three_waves():
    tasks = [
        make_task("t1"),
        make_task("t2", ["t1"]),
        make_task("t3", ["t1"]),
        make_task("t4", ["t2", "t3"]),
    ]
    waves = resolve_waves(build_dag(tasks))
    assert wave_ids(waves) == [{"t1"}, {"t2", "t3"}, {"t4"}]


def test_single_task_one_wave():
    waves = resolve_waves(build_dag([make_task("t1")]))
    assert wave_ids(waves) == [{"t1"}]


def test_cycle_raises_with_path():
    tasks = [make_task("t1", ["t2"]), make_task("t2", ["t1"])]
    with pytest.raises(CycleError) as exc:
        resolve_waves(build_dag(tasks))
    assert "t1" in exc.value.path and "t2" in exc.value.path


def test_detect_cycle_returns_none_for_acyclic():
    tasks = [make_task("t1"), make_task("t2", ["t1"]), make_task("t3", ["t2"])]
    assert detect_cycle(build_dag(tasks)) is None


def test_detect_cycle_returns_path_for_cyclic():
    tasks = [make_task("t1", ["t2"]), make_task("t2", ["t1"])]
    path = detect_cycle(build_dag(tasks))
    assert path is not None
    assert "t1" in path and "t2" in path


def test_duplicate_task_ids_raise():
    tasks = [make_task("t1"), make_task("t1")]
    with pytest.raises(ValueError):
        build_dag(tasks)


def test_dependency_on_unknown_task_raises():
    with pytest.raises(ValueError):
        build_dag([make_task("t1", ["ghost"])])
