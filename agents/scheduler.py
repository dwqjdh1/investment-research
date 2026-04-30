from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import deque
from agents.base import Agent


class AgentScheduler:
    """轻量级Agent调度器 — 拓扑排序 + ThreadPoolExecutor并行执行"""

    def __init__(self, max_workers: int = 4):
        self._agents: dict[str, Agent] = {}
        self._deps: dict[str, list[str]] = {}  # name -> [dependency_names]
        self.max_workers = max_workers

    def register(self, agent: Agent, depends_on: list[str] | None = None) -> "AgentScheduler":
        self._agents[agent.name] = agent
        self._deps[agent.name] = depends_on or []
        return self

    def run(self, initial_context: dict) -> dict:
        context = dict(initial_context)
        batches = self._topological_sort()

        for batch in batches:
            futures = {}
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                for name in batch:
                    agent = self._agents[name]
                    if not agent.validate_input(context):
                        continue
                    futures[executor.submit(agent.execute, context)] = name

                for future in as_completed(futures):
                    name = futures[future]
                    try:
                        result = future.result()
                        context.update(result)
                    except Exception as e:
                        context[f"{name}_error"] = str(e)

        return context

    def _topological_sort(self) -> list[list[str]]:
        in_degree: dict[str, int] = {}
        children: dict[str, list[str]] = {}

        for name in self._agents:
            in_degree[name] = len(self._deps.get(name, []))
            children.setdefault(name, [])

        for name, deps in self._deps.items():
            for dep in deps:
                children.setdefault(dep, []).append(name)

        queue = deque([n for n, d in in_degree.items() if d == 0])
        batches = []

        while queue:
            batch = list(queue)
            batches.append(batch)
            queue.clear()

            for name in batch:
                for child in children.get(name, []):
                    in_degree[child] -= 1
                    if in_degree[child] == 0:
                        queue.append(child)

        return batches
