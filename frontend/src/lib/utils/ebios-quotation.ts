// Client mirror of backend/ebios_rm/quotation.py, so the graph editor shows the
// roll-up of unsaved changes. Keep both in sync; grids come from the backend.

export const UNRATED = -1;

export interface QuotationStep {
	id: string;
	antecedents: string[];
	logicOperator: 'AND' | 'OR' | null;
	probability: number;
	difficulty: number;
}

export interface StepQuotation {
	probability: number;
	difficulty: number | null;
	likelihood: number;
	critical: boolean;
}

export interface Quotation {
	likelihood: number;
	steps: Record<string, StepQuotation>;
}

export interface RatingLevel {
	name: string;
	description?: string;
	default?: boolean;
}

// Scales and grids of the study's matrix, as served by `studies/{id}/rating-kit/`.
export interface RatingKit {
	success_probability: RatingLevel[];
	technical_difficulty: RatingLevel[];
	likelihood_grid: number[][];
	ro_to: Record<string, any>;
}

function combine(values: number[], useMax: boolean): number {
	if (!values.length || values.includes(UNRATED)) return UNRATED;
	return useMax ? Math.max(...values) : Math.min(...values);
}

function topologicalOrder(byId: Map<string, QuotationStep>): string[] {
	const order: string[] = [];
	const seen = new Set<string>();
	const visit = (id: string) => {
		if (seen.has(id)) return;
		seen.add(id);
		for (const antecedent of byId.get(id)!.antecedents) {
			if (byId.has(antecedent)) visit(antecedent);
		}
		order.push(id);
	};
	for (const id of byId.keys()) visit(id);
	return order;
}

export function computeQuotation(
	steps: QuotationStep[],
	method: string,
	grid: number[][]
): Quotation {
	const byId = new Map(steps.map((step) => [step.id, step]));
	const advanced = method === 'advanced';
	const order = topologicalOrder(byId);
	const probability: Record<string, number> = {};
	const difficulty: Record<string, number> = {};

	for (const id of order) {
		const step = byId.get(id)!;
		const antecedents = step.antecedents.filter((a) => byId.has(a));
		const isAnd = step.logicOperator === 'AND';

		let p = step.probability;
		if (antecedents.length && p !== UNRATED) {
			const upstream = combine(
				antecedents.map((a) => probability[a]),
				!isAnd
			);
			p = upstream === UNRATED ? UNRATED : Math.min(p, upstream);
		}
		probability[id] = p;

		if (advanced) {
			let d = step.difficulty;
			if (antecedents.length && d !== UNRATED) {
				const upstream = combine(
					antecedents.map((a) => difficulty[a]),
					isAnd
				);
				d = upstream === UNRATED ? UNRATED : Math.max(d, upstream);
			}
			difficulty[id] = d;
		}
	}

	const stepLikelihood = (id: string): number => {
		if (!advanced) return probability[id];
		const p = probability[id];
		const d = difficulty[id];
		if (p === UNRATED || d === UNRATED) return UNRATED;
		return grid[p]?.[d] ?? UNRATED;
	};
	const rank = (id: string): number[] =>
		advanced ? [stepLikelihood(id), probability[id], -difficulty[id]] : [probability[id]];
	const best = (ids: string[]) =>
		ids.reduce((a, b) => {
			const ra = rank(a);
			const rb = rank(b);
			for (let i = 0; i < ra.length; i++) {
				if (rb[i] !== ra[i]) return rb[i] > ra[i] ? b : a;
			}
			return a;
		});

	const hasSuccessor = new Set(steps.flatMap((step) => step.antecedents));
	const finalSteps = order.filter((id) => !hasSuccessor.has(id));
	const finalValues = finalSteps.map(stepLikelihood);
	let likelihood = UNRATED;
	const critical = new Set<string>();
	if (finalValues.length && !finalValues.includes(UNRATED)) {
		likelihood = Math.max(...finalValues);
		const stack = [best(finalSteps)];
		while (stack.length) {
			const id = stack.pop()!;
			if (critical.has(id)) continue;
			critical.add(id);
			const step = byId.get(id)!;
			const antecedents = step.antecedents.filter((a) => byId.has(a));
			if (!antecedents.length) continue;
			if (step.logicOperator === 'AND') stack.push(...antecedents);
			else stack.push(best(antecedents));
		}
	}

	return {
		likelihood,
		steps: Object.fromEntries(
			order.map((id) => [
				id,
				{
					probability: probability[id],
					difficulty: advanced ? difficulty[id] : null,
					likelihood: stepLikelihood(id),
					critical: critical.has(id)
				}
			])
		)
	};
}
