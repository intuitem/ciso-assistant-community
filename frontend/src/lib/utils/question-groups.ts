export interface QuestionGroup {
	refId: string;
	name: string;
	description: string;
	annotation: string;
	typicalEvidence: string;
	order: string[];
}

interface QuestionGroupDefinition {
	ref_id?: unknown;
	name?: unknown;
	description?: unknown;
	annotation?: unknown;
	typical_evidence?: unknown;
}

interface GroupedQuestion {
	question_group?: unknown;
}

/** False and 0 are valid answers; only empty answer containers are unanswered. */
export function hasQuestionAnswer(answer: unknown, attachmentCount = 0): boolean {
	if (attachmentCount > 0) return true;
	if (answer === undefined || answer === null) return false;
	if (typeof answer === 'string') return answer.trim() !== '';
	if (Array.isArray(answer)) return answer.length > 0;
	return true;
}

function text(value: unknown): string {
	return typeof value === 'string' ? value.trim() : '';
}

/**
 * Build presentation groups from the canonical model:
 * - framework.question_groups_definition owns reusable group metadata;
 * - requirement.questions_properties.groups_order chooses its local order;
 * - each question references a group through question_group.
 *
 * Metadata must cover every question exactly once before the paged UI hides
 * anything. Invalid or partial metadata therefore falls back to the ordinary
 * all-questions view.
 */
export function normalizeQuestionGroups(
	groupsOrder: unknown,
	definitions: unknown,
	questions: Record<string, unknown>
): QuestionGroup[] {
	const questionEntries = Object.entries(questions ?? {});
	if (!Array.isArray(groupsOrder) || groupsOrder.length === 0 || !Array.isArray(definitions)) {
		return [];
	}

	const orderedRefIds = groupsOrder.map(text);
	if (
		orderedRefIds.some((refId) => !refId) ||
		new Set(orderedRefIds).size !== orderedRefIds.length
	) {
		return [];
	}

	const definitionsByRefId = new Map<string, QuestionGroupDefinition>();
	for (const candidate of definitions) {
		if (!candidate || typeof candidate !== 'object') continue;
		const definition = candidate as QuestionGroupDefinition;
		const refId = text(definition.ref_id);
		if (!refId || definitionsByRefId.has(refId)) return [];
		definitionsByRefId.set(refId, definition);
	}

	const groups: QuestionGroup[] = [];
	for (const refId of orderedRefIds) {
		const definition = definitionsByRefId.get(refId);
		if (!definition) return [];
		groups.push({
			refId,
			name: text(definition.name) || refId,
			description: text(definition.description),
			annotation: text(definition.annotation),
			typicalEvidence: text(definition.typical_evidence),
			order: []
		});
	}

	const groupsByRefId = new Map(groups.map((group) => [group.refId, group]));
	for (const [urn, rawQuestion] of questionEntries) {
		if (!rawQuestion || typeof rawQuestion !== 'object') return [];
		const question = rawQuestion as GroupedQuestion;
		const group = groupsByRefId.get(text(question.question_group));
		if (!group) return [];
		group.order.push(urn);
	}

	return groups.every((group) => group.order.length > 0) ? groups : [];
}
