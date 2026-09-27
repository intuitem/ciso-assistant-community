from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Hashable, Iterable, Literal

Mode = Literal["chain", "connected"]
Side = Literal["focus", "up", "down", "any"]


@dataclass
class Walk:
    order: list = field(default_factory=list)
    hops: dict = field(default_factory=dict)
    side: dict = field(default_factory=dict)
    omitted: dict = field(default_factory=dict)
    elsewhere: dict = field(default_factory=dict)
    edges: list = field(default_factory=list)
    truncated: bool = False


def walk_asset_graph(
    focus: Hashable,
    links: Iterable[tuple[Hashable, Hashable]],
    mode: Mode = "chain",
    max_hops: int | None = None,
    limit: int | None = None,
    expand: Iterable[Hashable] = (),
    reveal: Iterable[Hashable] = (),
) -> Walk:
    parents: dict = defaultdict(set)
    children: dict = defaultdict(set)
    for child, parent in links:
        parents[child].add(parent)
        children[parent].add(child)

    def next_steps(node, side: Side):
        if mode == "connected":
            return [(n, "any") for n in parents[node] | children[node]]
        steps = []
        if side in ("focus", "up"):
            steps += [(n, "up") for n in parents[node]]
        if side in ("focus", "down"):
            steps += [(n, "down") for n in children[node]]
        return steps

    result = Walk()
    focus_side: Side = "any" if mode == "connected" else "focus"

    def include(node, side, hops):
        result.order.append(node)
        result.side[node] = side
        result.hops[node] = hops

    include(focus, focus_side, 0)
    queue = deque([focus])
    while queue:
        node = queue.popleft()
        hops = result.hops[node]
        if max_hops is not None and hops >= max_hops:
            continue
        for neighbour, side in sorted(
            next_steps(node, result.side[node]), key=lambda s: str(s[0])
        ):
            if neighbour in result.hops:
                continue
            if limit is not None and len(result.order) >= limit:
                result.truncated = True
                break
            include(neighbour, side, hops + 1)
            queue.append(neighbour)

    def all_steps(node):
        return [(n, "up") for n in parents[node]] + [
            (n, "down") for n in children[node]
        ]

    pending = [(n, next_steps) for n in expand] + [
        (n, lambda node, _side: all_steps(node)) for n in reveal
    ]
    grew = True
    while grew:
        grew = False
        for node, steps in pending:
            if node not in result.hops:
                continue
            for neighbour, side in steps(node, result.side[node]):
                if neighbour not in result.hops:
                    include(neighbour, side, result.hops[node] + 1)
                    grew = True

    included = set(result.order)
    for node in result.order:
        in_mode = {n for n, _ in next_steps(node, result.side[node])}
        missing = in_mode - included
        if missing:
            result.omitted[node] = len(missing)
        skipped = (parents[node] | children[node]) - in_mode - included
        if skipped:
            result.elsewhere[node] = len(skipped)
    result.edges = [
        (parent, child)
        for child, ps in parents.items()
        if child in included
        for parent in ps
        if parent in included
    ]
    return result
