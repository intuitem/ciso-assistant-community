import { describe, it, expect } from 'vitest';
import {
	addDays,
	buildBurndown,
	buildMilestones,
	buildTrajectory,
	daysBetween,
	planScenario,
	reachesResidual,
	stageCell,
	toDisplay,
	type ControlInfo,
	type Stage
} from './trajectory';

const today = '2026-09-26';

function controlMap(...controls: ControlInfo[]) {
	return new Map(controls.map((c) => [c.id, c]));
}

const control = (id: string, status: string, eta: string | null): ControlInfo => ({
	id,
	name: id,
	status,
	eta
});

describe('dates', () => {
	it('counts days across a month boundary', () => {
		expect(daysBetween('2026-09-26', '2026-10-15')).toBe(19);
	});

	it('adds days', () => {
		expect(addDays('2026-09-26', 36)).toBe('2026-11-01');
	});
});

describe('planScenario', () => {
	it('has no plan without extra controls', () => {
		expect(planScenario([], controlMap(), today).state).toBe('none');
	});

	it('is done when every extra control is active', () => {
		const plan = planScenario(['a'], controlMap(control('a', 'active', null)), today);
		expect(plan).toMatchObject({ state: 'done', date: today });
	});

	it('lands on the latest pending eta', () => {
		const controls = controlMap(
			control('a', 'in_progress', '2026-10-15'),
			control('b', 'to_do', '2026-11-30'),
			control('c', 'active', '2026-12-31')
		);
		expect(planScenario(['a', 'b', 'c'], controls, today)).toMatchObject({
			state: 'scheduled',
			date: '2026-11-30'
		});
	});

	it('is overdue when a pending control is past its eta', () => {
		const controls = controlMap(
			control('a', 'in_progress', '2026-09-10'),
			control('b', 'to_do', null)
		);
		expect(planScenario(['a', 'b'], controls, today).state).toBe('overdue');
	});

	it('is unscheduled when a pending control has no eta', () => {
		const controls = controlMap(control('a', 'to_do', null), control('b', 'to_do', '2026-10-01'));
		expect(planScenario(['a', 'b'], controls, today).state).toBe('unscheduled');
	});
});

describe('reachesResidual', () => {
	const plan = planScenario(['a'], controlMap(control('a', 'to_do', '2026-10-15')), today);

	it('stays at current before the eta', () => {
		expect(reachesResidual(plan, '2026-10-14')).toBe(false);
	});

	it('moves to residual on the eta', () => {
		expect(reachesResidual(plan, '2026-10-15')).toBe(true);
	});
});

describe('buildMilestones', () => {
	it('groups pending controls by eta and lists the scenarios waiting on them', () => {
		const shared = control('edr', 'in_progress', '2026-10-15');
		const controls = controlMap(
			shared,
			control('waf', 'to_do', '2026-11-15'),
			control('late', 'to_do', '2026-09-01'),
			control('done', 'active', '2026-10-15')
		);
		const plans = new Map([
			['r1', planScenario(['edr', 'done'], controls, today)],
			['r9', planScenario(['edr', 'waf'], controls, today)],
			['r5', planScenario(['late'], controls, today)]
		]);
		const milestones = buildMilestones(plans, today);
		expect(milestones.map((m) => [m.date, m.offset, m.scenarioIds])).toEqual([
			['2026-10-15', 19, ['r1', 'r9']],
			['2026-11-15', 50, ['r9']]
		]);
		expect(milestones[0].controls.map((c) => c.id)).toEqual(['edr']);
	});
});

describe('buildBurndown', () => {
	const scenarios = [
		scenario('a', 'R1', {
			current_proba: 2,
			current_impact: 2,
			residual_proba: 0,
			residual_impact: 0
		}),
		scenario('b', 'R2', {
			current_proba: 2,
			current_impact: 1,
			residual_proba: 1,
			residual_impact: 1
		}),
		scenario('c', 'R3', { current_proba: 1, current_impact: 2, residual_proba: -1 })
	];
	const dots = buildTrajectory(scenarios as any, grid, ['current', 'residual'], straight);
	const controls = controlMap(
		control('x', 'to_do', '2026-10-15'),
		control('y', 'active', null),
		control('z', 'to_do', '2026-11-01')
	);
	const plans = new Map([
		['a', planScenario(['x'], controls, today)],
		['b', planScenario(['y'], controls, today)],
		['c', planScenario(['z'], controls, today)]
	]);

	it('counts scenarios per level at each distinct date, keeping unrated residuals at current', () => {
		const points = buildBurndown(dots, plans, { current: 0, residual: 1 }, 3, [
			'2026-11-01',
			today,
			'2026-10-15',
			today
		]);
		expect(points).toEqual([
			{ date: today, counts: [0, 1, 2] },
			{ date: '2026-10-15', counts: [1, 1, 1] },
			{ date: '2026-11-01', counts: [1, 1, 1] }
		]);
	});
});

const grid = [
	[0, 0, 1],
	[0, 1, 2],
	[1, 2, 2]
];
const dims = { probabilities: 3, impacts: 3 };
const stages: Stage[] = ['inherent', 'current', 'residual'];
const straight = { swapAxes: false, flipVertical: false };

const rating = (value: number) => ({ value });

function scenario(id: string, ref_id: string, values: Record<string, number>) {
	return Object.fromEntries([
		['id', id],
		['ref_id', ref_id],
		['name', `scenario ${ref_id}`],
		...Object.entries(values).map(([key, value]) => [key, rating(value)])
	]);
}

describe('stageCell', () => {
	it('returns null when a stage is not rated', () => {
		expect(
			stageCell(scenario('a', 'R1', { current_proba: 1, current_impact: -1 }) as any, 'current')
		).toBeNull();
	});

	it('reads the probability and impact values', () => {
		expect(
			stageCell(scenario('a', 'R1', { residual_proba: 0, residual_impact: 2 }) as any, 'residual')
		).toEqual({
			proba: 0,
			impact: 2
		});
	});
});

describe('toDisplay', () => {
	it('puts the highest probability on the top row by default', () => {
		expect(toDisplay({ proba: 2, impact: 0 }, dims, straight)).toEqual({ row: 0, col: 0 });
	});

	it('puts the highest probability on the bottom row when flipped', () => {
		expect(
			toDisplay({ proba: 2, impact: 0 }, dims, { swapAxes: false, flipVertical: true })
		).toEqual({
			row: 2,
			col: 0
		});
	});

	it('puts probability on the x axis when axes are swapped', () => {
		expect(
			toDisplay({ proba: 2, impact: 0 }, dims, { swapAxes: true, flipVertical: false })
		).toEqual({
			row: 2,
			col: 2
		});
	});
});

describe('buildTrajectory', () => {
	const scenarios = [
		scenario('b', 'R2', {
			inherent_proba: 2,
			inherent_impact: 2,
			current_proba: 1,
			current_impact: 2,
			residual_proba: 0,
			residual_impact: 0
		}),
		scenario('a', 'R1', {
			inherent_proba: 2,
			inherent_impact: 2,
			current_proba: 0,
			current_impact: 0,
			residual_proba: -1,
			residual_impact: -1
		})
	];

	it('orders dots by ref_id', () => {
		expect(buildTrajectory(scenarios as any, grid, stages, straight).map((d) => d.label)).toEqual([
			'R1',
			'R2'
		]);
	});

	it('carries the last rated cell forward when a stage is not rated', () => {
		const [r1] = buildTrajectory(scenarios as any, grid, stages, straight);
		expect(r1.cells[2]).toEqual({ proba: 0, impact: 0 });
		expect(r1.levels[2]).toBe(-1);
	});

	it('spreads dots sharing a cell side by side', () => {
		const [r1, r2] = buildTrajectory(scenarios as any, grid, stages, straight);
		expect(r1.positions[0]!.y).toBeCloseTo(r2.positions[0]!.y);
		expect(r1.positions[0]!.x).toBeLessThan(r2.positions[0]!.x);
	});

	it('centres a lone dot in its cell', () => {
		const [, r2] = buildTrajectory(scenarios as any, grid, stages, straight);
		expect(r2.positions[1]!.x).toBeCloseTo((2.5 / 3) * 100);
		expect(r2.positions[1]!.y).toBeCloseTo((1.5 / 3) * 100);
	});

	it('flags a stage whose level is higher than the previous one', () => {
		const worse = scenario('c', 'R3', {
			inherent_proba: 0,
			inherent_impact: 0,
			current_proba: 0,
			current_impact: 0,
			residual_proba: 2,
			residual_impact: 2
		});
		const [dot] = buildTrajectory([worse] as any, grid, stages, straight);
		expect(dot.worsened).toEqual([false, false, true]);
	});

	it('leaves a dot without position until its first rated stage', () => {
		const late = scenario('d', 'R4', { current_proba: 1, current_impact: 1 });
		const [dot] = buildTrajectory([late] as any, grid, stages, straight);
		expect(dot.positions[0]).toBeNull();
		expect(dot.positions[1]).not.toBeNull();
		expect(dot.positions[2]).toEqual(dot.positions[1]);
	});
});
