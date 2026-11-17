import { describe, expect, it } from 'vitest';
import { UNRATED, computeQuotation, type QuotationStep } from './ebios-quotation';

// Default 4-level crossing grid served by the backend (fiche méthode 8 resampled).
const GRID = [
	[1, 1, 0, 0],
	[2, 2, 1, 0],
	[3, 2, 2, 1],
	[3, 3, 2, 1]
];

// Same vectors as backend/ebios_rm/tests/test_quotation.py.
function diamond(
	operator: 'AND' | 'OR' | null,
	probabilities: number[],
	difficulties = [UNRATED, UNRATED, UNRATED, UNRATED]
): QuotationStep[] {
	const ids = ['recon', 'phishing', 'watering', 'exfiltration'];
	const antecedents = [[], ['recon'], ['recon'], ['phishing', 'watering']];
	return ids.map((id, i) => ({
		id,
		antecedents: antecedents[i],
		logicOperator: i === 3 ? operator : null,
		probability: probabilities[i],
		difficulty: difficulties[i]
	}));
}

const critical = (q: ReturnType<typeof computeQuotation>) =>
	new Set(Object.entries(q.steps).flatMap(([id, s]) => (s.critical ? [id] : [])));

describe('standard roll-up', () => {
	const grid = GRID;

	it('keeps the best OR alternative', () => {
		const q = computeQuotation(diamond('OR', [3, 1, 2, 3]), 'standard', grid);
		expect(q.likelihood).toBe(2);
		expect(critical(q)).toEqual(new Set(['recon', 'watering', 'exfiltration']));
	});

	it('needs every AND antecedent', () => {
		const q = computeQuotation(diamond('AND', [3, 1, 2, 3]), 'standard', grid);
		expect(q.steps.exfiltration.probability).toBe(1);
		expect(critical(q).size).toBe(4);
	});

	it('leaves the mode unrated when a step is not rated', () => {
		const q = computeQuotation(diamond('OR', [3, UNRATED, 2, 3]), 'standard', grid);
		expect(q.likelihood).toBe(UNRATED);
		expect(critical(q).size).toBe(0);
	});
});

describe('advanced roll-up', () => {
	const grid = GRID;

	it('takes the easiest OR alternative and crosses at the end', () => {
		const q = computeQuotation(diamond('OR', [3, 3, 3, 3], [0, 3, 1, 0]), 'advanced', grid);
		expect(q.steps.exfiltration.difficulty).toBe(1);
		expect(q.likelihood).toBe(grid[3][1]);
		expect(critical(q)).toEqual(new Set(['recon', 'watering', 'exfiltration']));
	});

	it('takes the hardest AND antecedent', () => {
		const q = computeQuotation(diamond('AND', [3, 3, 3, 3], [0, 3, 1, 0]), 'advanced', grid);
		expect(q.likelihood).toBe(grid[3][3]);
	});
});
