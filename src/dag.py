from dataclasses import dataclass

from src.models import Task


class CycleError(Exception):
    def __init__(self, path: list[str]):
        self.path = path
        super().__init__(f"Cycle detected: {' -> '.join(path)}")


@dataclass
class DAG:
    tasks: dict[str, Task]
    children: dict[str, list[str]]
    in_degree: dict[str, int]


def build_dag(tasks: list[Task]) -> DAG:
    tasks_by_id: dict[str, Task] = {}
    for t in tasks:
        if t.id in tasks_by_id:
            raise ValueError(f"Duplicate task id: '{t.id}'")
        tasks_by_id[t.id] = t
    children: dict[str, list[str]] = {t.id: [] for t in tasks}
    in_degree = {t.id: len(t.dependencies) for t in tasks}
    for t in tasks:
        for dep in t.dependencies:
            if dep not in tasks_by_id:
                raise ValueError(f"Task '{t.id}' depends on unknown task '{dep}'")
            children[dep].append(t.id)
    return DAG(tasks=tasks_by_id, children=children, in_degree=in_degree)


def detect_cycle(dag: DAG) -> list[str] | None:
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {node: WHITE for node in dag.tasks}
    path: list[str] = []

    def visit(node: str) -> list[str] | None:
        color[node] = GRAY
        path.append(node)
        for child in dag.children[node]:
            if color[child] == GRAY:
                return path[path.index(child):] + [child]
            if color[child] == WHITE:
                found = visit(child)
                if found is not None:
                    return found
        color[node] = BLACK
        path.pop()
        return None

    for node in dag.tasks:
        if color[node] == WHITE:
            found = visit(node)
            if found is not None:
                return found
    return None


def resolve_waves(dag: DAG) -> list[list[Task]]:
    cycle = detect_cycle(dag)
    if cycle is not None:
        raise CycleError(cycle)

    in_degree = dict(dag.in_degree)  # copy: the sort consumes these counts
    ready = [node for node, d in in_degree.items() if d == 0]
    waves: list[list[Task]] = []
    while ready:
        waves.append([dag.tasks[node] for node in ready])
        next_ready = []
        for node in ready:
            for child in dag.children[node]:
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    next_ready.append(child)
        ready = next_ready
    return waves
