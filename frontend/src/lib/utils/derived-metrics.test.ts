import { describe, expect, it } from 'vitest';
import {
	aliasOf,
	datasetNameProblem,
	effectiveCombine,
	excludedOf,
	foldersWithSeveral,
	formulaKind,
	formulaKey,
	keepOrFirst,
	levelIndex,
	levelStarter,
	renameLiteral,
	stringLiterals,
	syncLevels,
	unknownLevels,
	latestTrend,
	samplesOnPeriods,
	sparkline,
	sparkRange,
	moveItem,
	quickFormulas,
	renameReference,
	pickInstance,
	pickedOf,
	setCombine,
	setIncluded,
	formulaScope,
	inputReferences,
	sampleMoment,
	sanitizeDatasetName
} from './derived-metrics';

describe('datasetNameProblem', () => {
	it('accepts a fresh identifier', () => {
		expect(datasetNameProblem('active', ['controls'])).toBeNull();
	});

	it('refuses a name another dataset has', () => {
		// Datasets are keyed by name: a duplicate replaced the other one on save.
		expect(datasetNameProblem('controls', ['controls', 'late'])).toBe('taken');
	});

	it('refuses an empty name', () => {
		expect(datasetNameProblem('', ['controls'])).toBe('required');
	});

	it('refuses what the backend refuses', () => {
		expect(datasetNameProblem('1st', [])).toBe('invalid');
		expect(datasetNameProblem('metrics', [])).toBe('invalid');
		expect(datasetNameProblem('previous', [])).toBe('invalid');
	});
});

describe('sanitizeDatasetName', () => {
	it('keeps identifier characters only', () => {
		expect(sanitizeDatasetName('late controls!')).toBe('late_controls_');
	});
});

describe('aliasOf', () => {
	it('mirrors the backend default aliases', () => {
		expect(aliasOf({ fn: 'count' })).toBe('count');
		expect(aliasOf({ fn: 'count', group_by: 'status' })).toBe('by_status');
		expect(aliasOf({ fn: 'avg', field: 'priority' })).toBe('avg_priority');
		expect(aliasOf({ fn: 'max', field: 'eta', group_by: 'status' })).toBe('max_eta_by_status');
		expect(aliasOf({ fn: 'count', as: 'total' })).toBe('total');
	});
});

describe('metric formulas', () => {
	it('offer the inputs and previous to the expression', () => {
		expect(
			inputReferences([
				{ key: 'clicks', definition: 'a', combine: 'one' },
				{ key: 'trained', definition: 'b', combine: 'sum' }
			])
		).toEqual(['clicks', 'trained', 'previous']);
		expect(inputReferences(null)).toEqual([]);
		expect(inputReferences([{ key: '' }])).toEqual([]);
	});

	it('read other metrics only when inputs are set', () => {
		expect(formulaKind([{ key: 'x', definition: 'a', combine: 'one' }])).toBe('metrics');
		expect(formulaKind([])).toBe('objects');
		expect(formulaKind(null)).toBe('objects');
	});

	it('name inputs with the dataset rules', () => {
		expect(datasetNameProblem('now', [])).toBe('invalid');
		expect(datasetNameProblem('clicks', ['clicks'])).toBe('taken');
	});
});

describe('sampleMoment', () => {
	it('plots a period sample at its period start, not at its UTC end', () => {
		// November, stamped at its last instant: shown as December 1st in Paris.
		expect(
			sampleMoment({
				timestamp: '2025-11-30T23:59:59.999999Z',
				period_start: '2025-11-01T00:00:00Z'
			})
		).toBe('2025-11-01T00:00:00Z');
	});

	it('plots any other sample at its timestamp', () => {
		expect(sampleMoment({ timestamp: '2026-10-05T09:00:00Z', period_start: null })).toBe(
			'2026-10-05T09:00:00Z'
		);
		expect(sampleMoment({ timestamp: '2026-10-05T09:00:00Z' })).toBe('2026-10-05T09:00:00Z');
	});
});

describe('formulaScope', () => {
	it('offers datasets with their aliases after a dot, previous and metrics', () => {
		const scope = formulaScope(
			'objects',
			{
				controls: { model: 'applied_control', aggregates: [{ fn: 'count' }] },
				active: { model: 'applied_control', aggregates: [{ fn: 'count', group_by: 'status' }] }
			},
			null
		);
		expect(scope.variables.map((v) => v.key)).toEqual([
			'controls',
			'active',
			'metrics',
			'previous'
		]);
		expect(Object.keys(scope.referenceVariables)).toEqual(['controls', 'active']);
		expect(Object.keys(scope.referenceVariables.controls as object)).toEqual(['count']);
		expect(Object.keys(scope.referenceVariables.active as object)).toEqual(['by_status']);
	});

	it('shows what the last preview answered', () => {
		const scope = formulaScope(
			'objects',
			{ controls: { model: 'applied_control', aggregates: [{ fn: 'count' }] } },
			null,
			{ datasets: { controls: { count: 34 } } }
		);
		expect(scope.referenceVariables).toEqual({ controls: { count: 34 } });
	});

	it('offers the inputs of a metric formula with their latest period values', () => {
		const scope = formulaScope(
			'metrics',
			null,
			[
				{ key: 'clicks', definition: 'a', combine: 'sum' },
				{ key: 'headcount', definition: 'b', combine: 'sum' }
			],
			{
				periods: [
					{ inputs: { clicks: 50, headcount: 900 } },
					{ inputs: { clicks: 30, headcount: 950 } }
				]
			}
		);
		expect(scope.variables.map((v) => v.key)).toEqual(['clicks', 'headcount', 'previous']);
		expect(scope.referenceVariables).toEqual({ clicks: 30, headcount: 950 });
	});
});

describe('input choices', () => {
	it('picks the instance a one-value input reads, and clears it', () => {
		const picked = pickInstance(null, 'clicks', 'fr');
		expect(picked).toEqual({ clicks: { pick: 'fr' } });
		expect(pickedOf(picked, 'clicks')).toBe('fr');
		expect(pickInstance(picked, 'clicks', null)).toBeNull();
	});

	it('stores exclusions, so instances added later are read', () => {
		let choices = setIncluded(null, 'sites', 'legacy', false);
		expect(choices).toEqual({ sites: { exclude: ['legacy'] } });
		choices = setIncluded(choices, 'sites', 'de', false);
		expect(excludedOf(choices, 'sites')).toEqual(['legacy', 'de']);
		choices = setIncluded(choices, 'sites', 'legacy', true);
		choices = setIncluded(choices, 'sites', 'de', true);
		expect(choices).toBeNull();
	});

	it('keeps the other inputs untouched', () => {
		const choices = setIncluded({ clicks: { pick: 'fr' } }, 'sites', 'legacy', false);
		expect(choices).toEqual({ clicks: { pick: 'fr' }, sites: { exclude: ['legacy'] } });
	});

	it('flags the domains contributing several instances', () => {
		expect(
			foldersWithSeveral([
				{ folder: 'ACME France' },
				{ folder: 'ACME France' },
				{ folder: 'ACME Spain' }
			])
		).toEqual(['ACME France']);
	});
});

describe('aggregate override', () => {
	it('stores only a change from the definition default', () => {
		const choices = setCombine(null, 'headcount', 'max', 'sum');
		expect(choices).toEqual({ headcount: { combine: 'max' } });
		expect(effectiveCombine(choices, 'headcount', 'sum')).toBe('max');
		expect(setCombine(choices, 'headcount', 'sum', 'sum')).toBeNull();
		expect(effectiveCombine(null, 'headcount', 'sum')).toBe('sum');
	});

	it('drops exclusions when switching to one value, and the pick when leaving it', () => {
		let choices = setIncluded(null, 'h', 'hr', false);
		choices = setCombine(choices, 'h', 'one', 'sum');
		expect(choices).toEqual({ h: { combine: 'one' } });
		choices = pickInstance(choices, 'h', 'it');
		expect(choices).toEqual({ h: { combine: 'one', pick: 'it' } });
		choices = setCombine(choices, 'h', 'avg', 'sum');
		expect(choices).toEqual({ h: { combine: 'avg' } });
	});

	it('keeps exclusions between aggregates', () => {
		let choices = setIncluded(null, 'h', 'hr', false);
		choices = setCombine(choices, 'h', 'max', 'sum');
		expect(choices).toEqual({ h: { exclude: ['hr'], combine: 'max' } });
	});
});

describe('a computed metric from instances', () => {
	it('names a pick after its metric, as an identifier', () => {
		expect(formulaKey('Taux de clics – Phishing')).toBe('taux_de_clics_phishing');
		expect(formulaKey('2025 budget')).toBe('m_2025_budget');
		expect(formulaKey('Previous')).toBe('previous_value');
		expect(formulaKey('!!!')).toBe('metric');
		expect(formulaKey('Clicks', ['clicks', 'clicks_2'])).toBe('clicks_3');
	});

	it('renames whole references only', () => {
		expect(renameReference('clicks * 100.0 / clicks_2 + x.clicks', 'clicks', 'c')).toBe(
			'c * 100.0 / clicks_2 + x.clicks'
		);
		expect(renameReference('"clicks" + clicks', 'clicks', 'c')).toBe('"clicks" + c');
	});

	it('offers the common formulas over the picks', () => {
		expect(quickFormulas(['a'])).toEqual([]);
		expect(quickFormulas(['a', 'b']).map((f) => f.expression)).toEqual([
			'a * 100.0 / b',
			'a - b',
			'a + b',
			'(a + b) / 2.0'
		]);
		expect(quickFormulas(['a', 'b', 'c']).map((f) => f.kind)).toEqual(['sum', 'average']);
	});

	it('keeps the chosen domain while it is offered', () => {
		expect(keepOrFirst('b', [{ id: 'a' }, { id: 'b' }])).toBe('b');
		expect(keepOrFirst('z', [{ id: 'a' }, { id: 'b' }])).toBe('a');
		expect(keepOrFirst('z', [])).toBe('');
	});

	it('moves one pick, keeping the others in order', () => {
		expect(moveItem(['a', 'b', 'c'], 2, 0)).toEqual(['c', 'a', 'b']);
		expect(moveItem(['a', 'b', 'c'], 0, 1)).toEqual(['b', 'a', 'c']);
		expect(moveItem(['a', 'b'], 1, 5)).toEqual(['a', 'b']);
	});
});

describe('the preview chart', () => {
	const periods = [
		{ start: '2026-01-01', value: 10, skipped: false },
		{ start: '2026-02-01', value: null, skipped: true },
		{ start: '2026-03-01', value: 20, skipped: false },
		{ start: '2026-04-01', value: 15, skipped: false }
	];

	it('places numbers in their time slot, lowest at the bottom', () => {
		const chart = sparkline(periods, 100, 40, 0)!;
		expect(chart.points.map((p) => [p.x, p.y])).toEqual([
			[0, 40],
			[66.67, 0],
			[100, 20]
		]);
		expect(chart.line).toBe('M0,40 L66.67,0 L100,20');
		expect(chart.area).toBe('M0,40 L66.67,0 L100,20 L100,40 L0,40 Z');
	});

	it('draws a flat series mid-height, and nothing without a trend', () => {
		const flat = sparkline(
			[
				{ start: 'a', value: 3 },
				{ start: 'b', value: 3 }
			],
			10,
			10,
			0
		)!;
		expect(flat.points.map((p) => p.y)).toEqual([5, 5]);
		expect(sparkline([{ start: 'a', value: 3 }], 10, 10)).toBeNull();
	});

	it('puts two lines on one scale', () => {
		const now = [
			{ start: 'a', value: 0 },
			{ start: 'b', value: 10 }
		];
		const next = [
			{ start: 'a', value: 5 },
			{ start: 'b', value: 20 }
		];
		const range = sparkRange(now, next, [{ value: 'High' }, { value: 99, skipped: true }]);
		expect(range).toEqual({ min: 0, max: 20 });
		expect(sparkline(now, 10, 20, 0, range)!.points.map((p) => p.y)).toEqual([20, 10]);
		expect(sparkline(next, 10, 20, 0, range)!.points.map((p) => p.y)).toEqual([15, 0]);
		expect(sparkRange([{ value: null }])).toBeNull();
	});

	it('matches samples to periods by their start', () => {
		const matched = samplesOnPeriods(
			[{ start: '2026-01-01T00:00:00Z' }, { start: '2026-02-01T00:00:00Z' }],
			[
				// The same moment, written another way.
				{
					timestamp: '2026-01-31T10:00:00Z',
					period_start: '2026-01-01T00:00:00+00:00',
					value: '{"result": 7}'
				},
				{ timestamp: '2026-03-01T00:00:00Z', value: { result: 9 } },
				{ timestamp: '2026-02-01T00:00:00Z', value: 'not json' }
			],
			(value) => value.result
		);
		expect(matched).toEqual([
			{ start: '2026-01-01T00:00:00Z', value: 7, skipped: false },
			{ start: '2026-02-01T00:00:00Z', value: null, skipped: true }
		]);
	});

	it('tells whether the last move is good news', () => {
		expect(latestTrend(periods, true)).toEqual({ delta: -5, good: false });
		expect(latestTrend(periods, false)).toEqual({ delta: -5, good: true });
		expect(latestTrend([{ value: 1 }, { value: 1 }], true)).toEqual({ delta: 0, good: null });
		expect(latestTrend([{ value: 1 }], true)).toBeNull();
	});
});

describe('a level result', () => {
	it('reads the texts a formula returns, once each, in order', () => {
		expect(stringLiterals(`r > 80.0 ? "Good" : r > 50.0 ? 'Fair' : "Good"`)).toEqual([
			'Good',
			'Fair'
		]);
		expect(stringLiterals('r * 2')).toEqual([]);
	});

	it('follows the formula and keeps what the author did', () => {
		let levels = syncLevels([], ['Good', 'Poor']);
		expect(levels).toEqual([
			{ ref_id: 'good', name: 'Good', auto: true },
			{ ref_id: 'poor', name: 'Poor', auto: true }
		]);
		// Reordered by the author, a typed-in level added: both stay.
		levels = [levels[1], levels[0], { ref_id: 'na', name: 'N/A' }];
		levels = syncLevels(levels, ['Good', 'Poor', 'Fair']);
		expect(levels.map((l) => l.name)).toEqual(['Poor', 'Good', 'N/A', 'Fair']);
		// The formula drops Fair: it goes; N/A was typed in: it stays.
		levels = syncLevels(levels, ['Good', 'Poor']);
		expect(levels.map((l) => l.name)).toEqual(['Poor', 'Good', 'N/A']);
		// Nothing changed: the same list, so a reactive caller does not loop.
		expect(syncLevels(levels, ['Good', 'Poor'])).toBe(levels);
	});

	it('answers to a level name or reference, any case', () => {
		const levels = [
			{ ref_id: 'G', name: 'Good' },
			{ ref_id: 'P', name: 'Poor' }
		];
		expect(unknownLevels(`x ? "good" : "p"`, levels)).toEqual([]);
		expect(unknownLevels(`x ? "Bad" : "P"`, levels)).toEqual(['Bad']);
		expect(levelIndex('POOR', levels)).toBe(2);
		expect(levelIndex(1, levels)).toBe(1);
		expect(levelIndex(3, levels)).toBeNull();
		expect(levelIndex('Bad', levels)).toBeNull();
	});

	it('renames a level in the formula, quotes kept', () => {
		expect(renameLiteral(`x ? "Good" : 'Good' + "Goods"`, 'Good', 'Great')).toBe(
			`x ? "Great" : 'Great' + "Goods"`
		);
	});

	it('starts a level formula from the picks', () => {
		expect(levelStarter(['a', 'b'])).toBe('a * 100.0 / b >= 50.0 ? "High" : "Low"');
		expect(levelStarter(['a'])).toBe('a >= 50.0 ? "High" : "Low"');
		expect(levelStarter([])).toBe('');
	});
});
