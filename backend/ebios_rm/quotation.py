"""
Operating mode likelihood from elementary action ratings (EBIOS RM fiche méthode 8).

Standard method: Pr_cumul(step) = Min(Pr(step), Max(Pr_cumul(antecedents))).
Advanced method: the same probability roll-up, plus
Diff_cumul(step) = Max(Diff(step), Min(Diff_cumul(antecedents))), the two being
crossed at the final steps through the likelihood grid.

The fiche only defines alternative antecedents (OR). An AND step needs all of its
antecedents, so it takes the weakest one: Min of probabilities, Max of difficulties.
A step that is not rated, or depends on one that is not, has no cumulative value (-1).
"""

from dataclasses import dataclass, field

UNRATED = -1

# Fiche méthode 8 crossing grid on 5-level scales: likelihood = GRID[probability][difficulty].
FICHE_LIKELIHOOD_GRID = [
    [1, 1, 1, 0, 0],
    [2, 2, 2, 1, 0],
    [3, 3, 2, 2, 1],
    [4, 3, 3, 2, 1],
    [4, 4, 3, 2, 1],
]


def default_likelihood_grid(size: int) -> list[list[int]]:
    """Fiche grid resampled to a size x size scale."""
    if size < 2:
        return [[0] * size for _ in range(size)]
    last = len(FICHE_LIKELIHOOD_GRID) - 1

    def to_fiche(level: int) -> int:
        return round(level * last / (size - 1))

    return [
        [
            round(FICHE_LIKELIHOOD_GRID[to_fiche(p)][to_fiche(d)] * (size - 1) / last)
            for d in range(size)
        ]
        for p in range(size)
    ]


@dataclass
class Step:
    id: str
    antecedents: list[str]
    logic_operator: str | None
    probability: int = UNRATED
    difficulty: int = UNRATED


@dataclass
class Quotation:
    likelihood: int = UNRATED
    probability: dict[str, int] = field(default_factory=dict)
    difficulty: dict[str, int] = field(default_factory=dict)
    step_likelihood: dict[str, int] = field(default_factory=dict)
    critical_path: set[str] = field(default_factory=set)
    order: list[str] = field(default_factory=list)
    final_step: str | None = None

    @property
    def effort(self) -> int:
        """Cumulative difficulty of the most likely final step; lower is less effort."""
        return self.difficulty.get(self.final_step, UNRATED)

    def critical_steps(self) -> list[str]:
        return [step_id for step_id in self.order if step_id in self.critical_path]


def _combine(values: list[int], use_max: bool) -> int:
    if not values or UNRATED in values:
        return UNRATED
    return max(values) if use_max else min(values)


def compute(steps: list[Step], method: str, grid: list[list[int]] | None = None):
    """Roll the ratings up the step graph; steps must form a DAG."""
    by_id = {step.id: step for step in steps}
    advanced = method == "advanced"
    result = Quotation()
    order = _topological_order(by_id)
    result.order = order

    for step_id in order:
        step = by_id[step_id]
        antecedents = [a for a in step.antecedents if a in by_id]
        is_and = step.logic_operator == "AND"

        probability = step.probability
        if antecedents and probability != UNRATED:
            upstream = _combine(
                [result.probability[a] for a in antecedents], use_max=not is_and
            )
            probability = UNRATED if upstream == UNRATED else min(probability, upstream)
        result.probability[step_id] = probability

        if advanced:
            difficulty = step.difficulty
            if antecedents and difficulty != UNRATED:
                upstream = _combine(
                    [result.difficulty[a] for a in antecedents], use_max=is_and
                )
                difficulty = (
                    UNRATED if upstream == UNRATED else max(difficulty, upstream)
                )
            result.difficulty[step_id] = difficulty

    for step_id in order:
        result.step_likelihood[step_id] = _step_likelihood(result, step_id, grid)

    has_successor = {a for step in steps for a in step.antecedents}
    final_steps = [s for s in order if s not in has_successor]
    final_values = [result.step_likelihood[s] for s in final_steps]
    if final_values and UNRATED not in final_values:
        result.likelihood = max(final_values)
        result.final_step = max(final_steps, key=_ranker(result, advanced))
        result.critical_path = _critical_path(
            by_id, result, result.final_step, advanced
        )
    return result


def _step_likelihood(result: Quotation, step_id: str, grid) -> int:
    probability = result.probability[step_id]
    if step_id not in result.difficulty:
        return probability
    difficulty = result.difficulty[step_id]
    if UNRATED in (probability, difficulty) or not grid:
        return UNRATED
    try:
        return grid[probability][difficulty]
    except IndexError:
        return UNRATED


def _ranker(result: Quotation, advanced: bool):
    def rank(step_id):
        if advanced:
            return (
                result.step_likelihood[step_id],
                result.probability[step_id],
                -result.difficulty[step_id],
            )
        return (result.probability[step_id], 0, 0)

    return rank


def _critical_path(by_id, result: Quotation, final_step, advanced) -> set[str]:
    """Steps behind the most likely final step: every AND branch, the best OR branch."""
    rank = _ranker(result, advanced)
    path: set[str] = set()
    stack = [final_step]
    while stack:
        step_id = stack.pop()
        if step_id in path:
            continue
        path.add(step_id)
        step = by_id[step_id]
        antecedents = [a for a in step.antecedents if a in by_id]
        if not antecedents:
            continue
        if step.logic_operator == "AND":
            stack.extend(antecedents)
        else:
            stack.append(max(antecedents, key=rank))
    return path


def _topological_order(by_id: dict[str, Step]) -> list[str]:
    order: list[str] = []
    state: dict[str, bool] = {}
    for root in by_id:
        stack = [(root, False)]
        while stack:
            step_id, expanded = stack.pop()
            if expanded:
                state[step_id] = True
                order.append(step_id)
                continue
            if step_id in state:
                continue
            state[step_id] = False
            stack.append((step_id, True))
            for antecedent in by_id[step_id].antecedents:
                if antecedent in by_id and antecedent not in state:
                    stack.append((antecedent, False))
    return order


def quote_operating_mode(operating_mode):
    """Quotation of a saved operating mode under its study's method, None for express/manual."""
    study = operating_mode.ebios_rm_study
    method = study.quotation_method
    if method not in ("standard", "advanced"):
        return None
    steps = [
        Step(
            id=str(kill_chain.id),
            antecedents=[str(a.id) for a in kill_chain.antecedents.all()],
            logic_operator=kill_chain.logic_operator,
            probability=kill_chain.success_probability,
            difficulty=kill_chain.technical_difficulty,
        )
        for kill_chain in operating_mode.kill_chain_steps.prefetch_related(
            "antecedents"
        )
    ]
    return compute(steps, method, study.rating_kit()["likelihood_grid"])
