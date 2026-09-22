export interface QuestionGroup {
	description: string;
	order: string[];
}

/** False and 0 are valid answers; only empty answer containers are unanswered. */
export function hasQuestionAnswer(answer: unknown, attachmentCount = 0): boolean {
	if (attachmentCount > 0) return true;
	if (answer === undefined || answer === null) return false;
	if (typeof answer === 'string') return answer.trim() !== '';
	if (Array.isArray(answer)) return answer.length > 0;
	return true;
}

function orderedGroupEntries(groups: unknown): [string, unknown][] {
	if (Array.isArray(groups)) {
		return groups.map((group, index) => [String(index + 1), group]);
	}
	if (!groups || typeof groups !== 'object') return [];
	return Object.entries(groups as Record<string, unknown>).sort(([left], [right]) =>
		left.localeCompare(right, undefined, { numeric: true })
	);
}

/**
 * Validate presentation-only question groups before hiding any questions.
 * Invalid or incomplete metadata falls back to the legacy all-questions view.
 */
export function normalizeQuestionGroups(
	groups: unknown,
	questions: Record<string, unknown>
): QuestionGroup[] {
	const questionUrns = Object.keys(questions ?? {});
	if (questionUrns.length === 0) return [];

	const knownQuestions = new Set(questionUrns);
	const coveredQuestions = new Set<string>();
	const normalized: QuestionGroup[] = [];

	for (const [, candidate] of orderedGroupEntries(groups)) {
		if (!candidate || typeof candidate !== 'object') return [];
		const group = candidate as Record<string, unknown>;
		if (!Array.isArray(group.order) || group.order.length === 0) return [];

		const order: string[] = [];
		for (const rawUrn of group.order) {
			if (typeof rawUrn !== 'string') return [];
			const urn = rawUrn.trim();
			if (!knownQuestions.has(urn) || coveredQuestions.has(urn)) return [];
			coveredQuestions.add(urn);
			order.push(urn);
		}

		normalized.push({
			description: typeof group.description === 'string' ? group.description.trim() : '',
			order
		});
	}

	return normalized.length > 0 && coveredQuestions.size === questionUrns.length ? normalized : [];
}
