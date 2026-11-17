export type Stage = 'inherent' | 'current' | 'residual';

export type MatrixCell = { proba: number; impact: number };

export type Point = { x: number; y: number };

export type Orientation = { swapAxes: boolean; flipVertical: boolean };

export type Dimensions = { probabilities: number; impacts: number };

export type TrajectoryDot = {
	id: string;
	label: string;
	name: string;
	cells: (MatrixCell | null)[];
	levels: number[];
	positions: (Point | null)[];
	worsened: boolean[];
};

type ScenarioLike = {
	id: string;
	ref_id?: string | null;
	name: string;
	[key: string]: any;
};

export function stageCell(scenario: ScenarioLike, stage: Stage): MatrixCell | null {
	const proba = scenario[`${stage}_proba`]?.value ?? -1;
	const impact = scenario[`${stage}_impact`]?.value ?? -1;
	return proba >= 0 && impact >= 0 ? { proba, impact } : null;
}

export function gridSize(dims: Dimensions, orientation: Orientation) {
	return orientation.swapAxes
		? { cols: dims.probabilities, rows: dims.impacts }
		: { cols: dims.impacts, rows: dims.probabilities };
}

export function toDisplay(cell: MatrixCell, dims: Dimensions, orientation: Orientation) {
	const { rows } = gridSize(dims, orientation);
	const col = orientation.swapAxes ? cell.proba : cell.impact;
	const yIndex = orientation.swapAxes ? cell.impact : cell.proba;
	const row = orientation.flipVertical ? yIndex : rows - 1 - yIndex;
	return { row, col };
}

function slotPosition(
	row: number,
	col: number,
	slot: number,
	count: number,
	grid: { cols: number; rows: number }
): Point {
	const perRow = Math.ceil(Math.sqrt(count));
	const lines = Math.ceil(count / perRow);
	const inRow = Math.floor(slot / perRow);
	const itemsInLine = inRow === lines - 1 ? count - inRow * perRow : perRow;
	const inCol = slot % perRow;
	return {
		x: ((col + (inCol + 0.5) / itemsInLine) / grid.cols) * 100,
		y: ((row + (inRow + 0.5) / lines) / grid.rows) * 100
	};
}

export function buildTrajectory(
	scenarios: ScenarioLike[],
	riskGrid: number[][],
	stages: Stage[],
	orientation: Orientation
): TrajectoryDot[] {
	const dims = { probabilities: riskGrid.length, impacts: riskGrid[0]?.length ?? 0 };
	const grid = gridSize(dims, orientation);
	const levelOf = (cell: MatrixCell | null) =>
		cell ? (riskGrid[cell.proba]?.[cell.impact] ?? -1) : -1;

	const sorted = [...scenarios].sort((a, b) =>
		(a.ref_id || a.name).localeCompare(b.ref_id || b.name, undefined, { numeric: true })
	);

	const dots: TrajectoryDot[] = sorted.map((scenario, index) => {
		const rated = stages.map((stage) => stageCell(scenario, stage));
		const cells: (MatrixCell | null)[] = [];
		rated.forEach((cell, i) => cells.push(cell ?? (i > 0 ? cells[i - 1] : null)));
		const levels = rated.map(levelOf);
		return {
			id: scenario.id,
			label: scenario.ref_id || String(index + 1),
			name: scenario.name,
			cells,
			levels,
			positions: stages.map(() => null),
			worsened: levels.map(
				(level, i) => i > 0 && level >= 0 && levels[i - 1] >= 0 && level > levels[i - 1]
			)
		};
	});

	stages.forEach((_, s) => {
		const occupants = new Map<string, TrajectoryDot[]>();
		for (const dot of dots) {
			const cell = dot.cells[s];
			if (!cell) continue;
			const key = `${cell.proba}:${cell.impact}`;
			occupants.set(key, [...(occupants.get(key) ?? []), dot]);
		}
		for (const group of occupants.values()) {
			const { row, col } = toDisplay(group[0].cells[s]!, dims, orientation);
			group.forEach((dot, slot) => {
				dot.positions[s] = slotPosition(row, col, slot, group.length, grid);
			});
		}
	});

	return dots;
}

export type ControlInfo = {
	id: string;
	name: string;
	ref_id?: string | null;
	status: string;
	eta: string | null;
};

export type PlanState = 'done' | 'scheduled' | 'overdue' | 'unscheduled' | 'none';

export type ScenarioPlan = { state: PlanState; date: string | null; controls: ControlInfo[] };

export type Milestone = {
	date: string;
	offset: number;
	controls: ControlInfo[];
	scenarioIds: string[];
};

const DAY = 86_400_000;

const toUtc = (iso: string) => Date.parse(`${iso}T00:00:00Z`);

export function isoDay(date: Date): string {
	const pad = (n: number) => String(n).padStart(2, '0');
	return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function daysBetween(from: string, to: string): number {
	return Math.round((toUtc(to) - toUtc(from)) / DAY);
}

export function addDays(iso: string, days: number): string {
	return new Date(toUtc(iso) + days * DAY).toISOString().slice(0, 10);
}

export function planScenario(
	controlIds: string[],
	controls: Map<string, ControlInfo>,
	today: string
): ScenarioPlan {
	const linked = controlIds
		.map((id) => controls.get(id))
		.filter((c): c is ControlInfo => c !== undefined);
	if (linked.length === 0) return { state: 'none', date: null, controls: [] };
	const pending = linked.filter((c) => c.status !== 'active');
	if (pending.length === 0) return { state: 'done', date: today, controls: linked };
	if (pending.some((c) => c.eta && c.eta < today))
		return { state: 'overdue', date: null, controls: linked };
	if (pending.some((c) => !c.eta)) return { state: 'unscheduled', date: null, controls: linked };
	const date = pending
		.map((c) => c.eta!)
		.sort()
		.at(-1)!;
	return { state: 'scheduled', date, controls: linked };
}

export function reachesResidual(plan: ScenarioPlan, date: string): boolean {
	return plan.state === 'done' || (plan.state === 'scheduled' && plan.date! <= date);
}

export function buildMilestones(plans: Map<string, ScenarioPlan>, today: string): Milestone[] {
	const byDate = new Map<string, Milestone>();
	for (const [scenarioId, plan] of plans) {
		for (const control of plan.controls) {
			if (control.status === 'active' || !control.eta || control.eta < today) continue;
			const milestone = byDate.get(control.eta) ?? {
				date: control.eta,
				offset: daysBetween(today, control.eta),
				controls: [],
				scenarioIds: []
			};
			if (!milestone.controls.some((c) => c.id === control.id)) milestone.controls.push(control);
			if (!milestone.scenarioIds.includes(scenarioId)) milestone.scenarioIds.push(scenarioId);
			byDate.set(control.eta, milestone);
		}
	}
	return [...byDate.values()].sort((a, b) => a.offset - b.offset);
}

export type BurndownPoint = { date: string; counts: number[] };

export function buildBurndown(
	dots: TrajectoryDot[],
	plans: Map<string, ScenarioPlan>,
	stageIndexes: { current: number; residual: number },
	levelCount: number,
	dates: string[]
): BurndownPoint[] {
	return [...new Set(dates)].sort().map((date) => {
		const counts = Array(levelCount).fill(0);
		for (const dot of dots) {
			const plan = plans.get(dot.id);
			const current = dot.levels[stageIndexes.current];
			const residual = dot.levels[stageIndexes.residual];
			const level = plan && reachesResidual(plan, date) && residual >= 0 ? residual : current;
			if (level >= 0) counts[level] += 1;
		}
		return { date, counts };
	});
}
