import { describe, expect, it } from 'vitest';
import { gridToRules, remapGrid, rulesToGrid, type OutcomeRule, type Scale } from './builder-state';

const scale = (ref_id: string, ids: string[]): Scale => ({
	ref_id,
	label: ref_id,
	levels: ids.map((id) => ({ ref_id: id, label: id }))
});
const SCALES = [scale('sev', ['low', 'mid', 'high']), scale('lik', ['rare', 'often'])];
const RATING: OutcomeRule = {
	ref_id: 'risk',
	kind: 'rating',
	dimensions: ['sev', 'lik'],
	levels: [
		{ ref_id: 'ok', label: 'OK' },
		{ ref_id: 'bad', label: 'Bad' }
	],
	grid: [
		['ok', 'ok'],
		['ok', 'bad'],
		['bad', 'bad']
	]
} as OutcomeRule;

describe('rating grids', () => {
	it('keep each cell by level id when a level is deleted or moved', () => {
		const deleted = [scale('sev', ['low', 'high']), SCALES[1]];
		expect(remapGrid(RATING, SCALES, deleted)).toEqual([
			['ok', 'ok'],
			['bad', 'bad']
		]);
		const moved = [scale('sev', ['high', 'low', 'mid']), SCALES[1]];
		expect(remapGrid(RATING, SCALES, moved)).toEqual([
			['bad', 'bad'],
			['ok', 'ok'],
			['ok', 'bad']
		]);
	});

	it('convert to rules and back without losing a cell', () => {
		const rules = gridToRules(RATING, SCALES);
		expect(rules.map((r) => r.level)).toEqual(['ok', 'bad']);
		expect(rules[1].when).toContain('dims.sev.level == "high" && dims.lik.level == "rare"');
		expect(rulesToGrid({ ...RATING, grid: undefined, rules }, SCALES)).toEqual(RATING.grid);
	});

	it('refuse to draw rules written by hand', () => {
		const rules = [{ level: 'bad', when: 'dims.sev.rank >= 2.0' }];
		expect(rulesToGrid({ ...RATING, grid: undefined, rules }, SCALES)).toBeNull();
	});
});
