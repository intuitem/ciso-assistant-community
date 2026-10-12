import { getContext, setContext } from 'svelte';
import { m } from '$paraglide/messages';
import { extractNodeId, type BuilderNode, type OutcomeRule, type Question } from './builder-state';
import FIELDS from './cel-fields.json';

export type CelMode = 'framework' | 'quick_form';

export interface CelChoice {
	id: string;
	label: string;
}

export interface CelQuestion {
	id: string;
	label: string;
	type: Question['type'];
	group: string;
	choices: CelChoice[];
}

export interface CelCatalog {
	mode: CelMode;
	/** Pages (quick forms) or assessable requirements (frameworks). */
	nodes: { id: string; label: string }[];
	questions: CelQuestion[];
	/** Frameworks: nodes with children, scored as `sections[id]`. */
	sections?: { id: string; label: string }[];
	/** Frameworks: implementation groups, scored as `groups[id]`. */
	groups?: { id: string; label: string }[];
}

/** Where an expression runs: rules see `values`, visibility does not. */
export interface CelPlace {
	where: 'outcome' | 'visibility';
	/** Number rules this expression may read, as `values.<ref_id>`. */
	values?: string[];
}

export interface CelSuggestion {
	label: string;
	insert: string;
	detail?: string;
	/** Suggest again right after inserting, e.g. ids after `answers[`. */
	again?: boolean;
}

export interface CelCompletion {
	from: number;
	to: number;
	items: CelSuggestion[];
}

const CHOICE_TYPES = new Set(['unique_choice', 'multiple_choice']);

export function buildCelCatalog(
	nodes: BuilderNode[],
	mode: CelMode,
	groups: { id: string; label: string }[]
): CelCatalog {
	const catalog: CelCatalog = {
		mode,
		nodes: [],
		questions: [],
		sections: [],
		groups: mode === 'framework' ? groups : []
	};
	const walk = (list: BuilderNode[], top: boolean) => {
		for (const bn of list) {
			const nodeId = extractNodeId(bn.node.urn);
			const label = bn.node.name || bn.node.ref_id || nodeId || '';
			const listed = mode === 'quick_form' ? top : bn.node.assessable;
			if (nodeId && listed) catalog.nodes.push({ id: nodeId, label });
			if (nodeId && mode === 'framework' && bn.children.length) {
				const ref = bn.node.ref_id;
				catalog.sections?.push({
					id: nodeId,
					label: ref && ref !== label ? `${ref} ${label}` : label
				});
			}
			for (const { question } of bn.questions) {
				const id = extractNodeId(question.urn);
				if (!id) continue;
				catalog.questions.push({
					id,
					label: question.text || question.ref_id || id,
					type: question.type,
					group: label,
					choices: question.choices
						.map((c) => ({ id: extractNodeId(c.urn) ?? '', label: c.value || c.ref_id || '' }))
						.filter((c) => c.id)
				});
			}
			walk(bn.children, false);
		}
	};
	walk(nodes, true);
	return catalog;
}

/** The number rules a rule may read: those above it for a number rule, all for a yes/no one. */
export function readableValues(rules: OutcomeRule[], index: number): string[] {
	const rule = rules[index];
	return rules
		.filter((r, i) => r.kind === 'number' && r.ref_id && (rule?.kind !== 'number' || i < index))
		.map((r) => r.ref_id);
}

function fieldDetails(mode: CelMode): Record<string, Record<string, string>> {
	const answers = {
		value: m.builderCelAnswerValue(),
		score: m.builderCelAnswerScore(),
		selected_choices: m.builderCelAnswerSelectedChoices(),
		weight: m.builderCelAnswerWeight(),
		type: m.builderCelAnswerType(),
		answered: m.builderCelAnswerAnswered()
	};
	const subset = {
		implementation_score: m.builderCelSubsetImplementationScore(),
		documentation_score: m.builderCelSubsetDocumentationScore(),
		maturity_score: m.builderCelSubsetMaturityScore(),
		scored_count: m.builderCelSubsetScoredCount(),
		total_count: m.builderCelSubsetTotalCount(),
		not_applicable_count: m.builderCelSubsetNotApplicableCount(),
		min_maturity_score: m.builderCelSubsetMinMaturityScore()
	};
	if (mode === 'quick_form') {
		return {
			roots: {
				response: m.builderCelGroupResponse(),
				pages: m.builderCelGroupPages(),
				answers: m.builderCelGroupAnswers(),
				values: m.builderCelValues(),
				computed_outcomes: m.builderCelComputedOutcomes(),
				hidden_pages: m.builderCelHiddenPages()
			},
			response: {
				score: m.builderCelResponseScore(),
				score_sum: m.builderCelScoreSum(),
				score_max: m.builderCelScoreMax(),
				answered_count: m.builderCelAnsweredQuestions(),
				total_count: m.builderCelTotalQuestions(),
				complete: m.builderCelResponseComplete(),
				scored_complete: m.builderCelResponseScoredComplete()
			},
			pages: {
				visible: m.builderCelPageVisible(),
				score: m.builderCelPageScore(),
				score_max: m.builderCelPageScoreMax(),
				answered_count: m.builderCelAnsweredQuestions(),
				total_count: m.builderCelTotalQuestions()
			},
			answers
		};
	}
	return {
		roots: {
			assessment: m.builderCelGroupAssessment(),
			requirements: m.builderCelGroupRequirements(),
			sections: m.builderCelGroupSections(),
			groups: m.builderCelGroupImplementationGroups(),
			answers: m.builderCelGroupAnswers(),
			values: m.builderCelValues(),
			computed_outcomes: m.builderCelComputedOutcomes(),
			hidden_requirements: m.builderCelHiddenRequirements()
		},
		assessment: {
			score_sum: m.builderCelScoreSum(),
			score_max: m.builderCelScoreMax(),
			answered_count: m.builderCelAnsweredCount(),
			total_count: m.builderCelTotalCount(),
			selected_implementation_groups: m.builderCelSelectedGroups(),
			implementation_score: m.builderCelAssessmentImplementationScore(),
			documentation_score: m.builderCelAssessmentDocumentationScore(),
			maturity_score: m.builderCelAssessmentMaturityScore(),
			target_score: m.builderCelAssessmentTargetScore()
		},
		requirements: {
			score: m.builderCelReqScore(),
			max_score: m.builderCelReqMaxScore(),
			result: m.builderCelReqResult(),
			status: m.builderCelReqStatus(),
			documentation_score: m.builderCelReqDocumentationScore(),
			maturity_score: m.builderCelReqMaturityScore(),
			implementation_groups: m.builderCelReqGroups()
		},
		sections: { ...subset, depth: m.builderCelSectionDepth(), ref_id: m.builderCelSectionRefId() },
		groups: subset,
		answers
	};
}

/** Answer fields in the order that suits the question: choices first for choice questions. */
function answerFields(names: string[], type: string | undefined): string[] {
	const first =
		type && CHOICE_TYPES.has(type) ? ['selected_choices', 'answered'] : ['value', 'answered'];
	return [...first.filter((f) => names.includes(f)), ...names.filter((f) => !first.includes(f))];
}

/** Names match on themselves; ids and choices also on the text they stand for. */
function matching(items: CelSuggestion[], typed: string, byDetail = false): CelSuggestion[] {
	const needle = typed.toLowerCase();
	if (!needle) return items;
	const hit = (s: CelSuggestion) =>
		[s.label, ...(byDetail ? [s.insert, s.detail ?? ''] : [])].some((t) =>
			t.toLowerCase().includes(needle)
		);
	const starts = (s: CelSuggestion) => s.label.toLowerCase().startsWith(needle);
	const found = items.filter(hit);
	return [...found.filter(starts), ...found.filter((s) => !starts(s))];
}

const COMPLETE_STRINGS = /"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'/g;

/**
 * What to suggest at `cursor` in `text`, or null. `explicit` (Ctrl+Space)
 * also suggests names before anything is typed.
 */
export function celSuggestions(
	text: string,
	cursor: number,
	catalog: CelCatalog,
	place: CelPlace,
	explicit = false
): CelCompletion | null {
	const before = text.slice(0, cursor);
	const after = text.slice(cursor);
	const spec = FIELDS[catalog.mode] as Record<string, string[]>;
	const details = fieldDetails(catalog.mode);
	const nodeScope = catalog.mode === 'quick_form' ? 'pages' : 'requirements';
	const outcome = place.where === 'outcome';
	const ids: Record<string, { id: string; label: string }[]> = {
		[nodeScope]: catalog.nodes,
		...(catalog.mode === 'framework' && outcome
			? { sections: catalog.sections ?? [], groups: catalog.groups ?? [] }
			: {})
	};
	const scopes = [...Object.keys(ids), 'answers'].join('|');
	const result = (from: number, to: number, items: CelSuggestion[]) =>
		items.length ? { from, to, items } : null;

	// pages["…  /  answers["…  /  requirements["…  /  sections["…
	let match = new RegExp(`\\b(${scopes})\\[\\s*(["']?)([^"'\\]]*)$`).exec(before);
	if (match) {
		const [, scope, quote, typed] = match;
		const from = cursor - quote.length - typed.length;
		const rest = /^[^"'\]\s]*(?:["']\s*\])?(?:\.)?/.exec(after)?.[0] ?? '';
		const items =
			scope === 'answers'
				? catalog.questions.map((q) => ({
						label: q.id,
						insert: `"${q.id}"].`,
						detail: `${q.label} · ${q.group}`,
						again: true
					}))
				: ids[scope].map((n) => ({
						label: n.id,
						insert: `"${n.id}"].`,
						detail: n.label,
						again: true
					}));
		return result(from, cursor + rest.length, matching(items, typed, true));
	}

	// answers["q"].value == …  on a yes/no question
	match = /\banswers\[\s*["']([^"']+)["']\s*\]\.value\s*[!=]=\s*(\w*)$/.exec(before);
	if (match) {
		const question = catalog.questions.find((q) => q.id === match![1]);
		if (question?.type === 'boolean') {
			const items = [
				{ label: 'true', insert: 'true', detail: m.yes() },
				{ label: 'false', insert: 'false', detail: m.no() }
			];
			return result(cursor - match[2].length, cursor, matching(items, match[2]));
		}
	}

	// pages["p"].…  /  answers["q"].…
	match = new RegExp(`\\b(${scopes})\\[\\s*["']([^"']*)["']\\s*\\]\\.(\\w*)$`).exec(before);
	if (match) {
		const [, scope, id, typed] = match;
		let names = spec[scope] ?? [];
		if (scope === 'answers') {
			names = answerFields(names, catalog.questions.find((q) => q.id === id)?.type);
		}
		const items = names.map((name) => ({
			label: name,
			insert: name,
			detail: details[scope]?.[name]
		}));
		return result(cursor - typed.length, cursor, matching(items, typed));
	}

	// response.…  /  assessment.…  /  values.…
	match = /(?<![\w.\]])(response|assessment|values)\.(\w*)$/.exec(before);
	if (match) {
		const [, root, typed] = match;
		const items =
			root === 'values'
				? place.where === 'outcome'
					? (place.values ?? []).map((name) => ({
							label: name,
							insert: name,
							detail: m.builderCelValues()
						}))
					: []
				: [...(spec[root] ?? []), ...(outcome ? (spec[`${root}_scores`] ?? []) : [])].map(
						(name) => ({
							label: name,
							insert: name,
							detail: details[root]?.[name]
						})
					);
		return result(cursor - typed.length, cursor, matching(items, typed));
	}

	// An open string: offer each choice as a whole membership test.
	match = /(["'])([^"']*)$/.exec(before.replace(COMPLETE_STRINGS, (s) => '_'.repeat(s.length)));
	if (match) {
		const typed = match[2];
		const from = cursor - typed.length - 1;
		const closing = after.startsWith(match[1]) ? 1 : 0;
		const items = catalog.questions
			.filter((q) => CHOICE_TYPES.has(q.type))
			.flatMap((q) =>
				q.choices.map((c) => ({
					label: c.label || c.id,
					insert: `"${c.id}" in answers["${q.id}"].selected_choices`,
					detail: q.label
				}))
			);
		return result(from, cursor + closing, matching(items, typed, true));
	}

	// A bare name.
	match = /(?<![\w.\]"'])([A-Za-z_]\w*)$/.exec(before);
	const typed = match?.[1] ?? '';
	if (!typed && (!explicit || /[\w.\]"']$/.test(before))) return null;
	const roots = spec[place.where === 'visibility' ? 'visibility_roots' : 'roots'] ?? [];
	const items: CelSuggestion[] = [
		...roots.map((name) => {
			const indexed = name in ids || name === 'answers';
			const dotted = name === 'response' || name === 'assessment' || name === 'values';
			return {
				label: name,
				insert: indexed ? `${name}[` : dotted ? `${name}.` : name,
				detail: details.roots?.[name],
				again: indexed || dotted
			};
		}),
		{ label: 'true', insert: 'true' },
		{ label: 'false', insert: 'false' }
	];
	const found = matching(items, typed).filter((s) => s.label !== typed);
	return result(cursor - typed.length, cursor, found);
}

// ----- Insert condition -----

export type ConditionOp =
	| 'is'
	| 'is_not'
	| 'includes'
	| 'excludes'
	| 'yes'
	| 'no'
	| 'answered'
	| 'not_answered'
	| '>'
	| '>='
	| '<'
	| '<='
	| '=='
	| '!=';

export const NUMBER_OPS: ConditionOp[] = ['>=', '>', '<=', '<', '==', '!='];

/** The conditions a question supports; empty when the builder cannot write one. */
export function conditionOps(type: Question['type'], mode: CelMode): ConditionOp[] {
	const answered: ConditionOp[] = mode === 'quick_form' ? ['answered', 'not_answered'] : [];
	switch (type) {
		case 'unique_choice':
			return ['is', 'is_not', ...answered];
		case 'multiple_choice':
			return ['includes', 'excludes', ...answered];
		case 'boolean':
			return ['yes', 'no', ...answered];
		case 'number':
			return [...NUMBER_OPS, ...answered];
		default:
			return answered;
	}
}

/** A CEL double literal: an int literal fails against a decimal answer and back. */
function doubleLiteral(value: number): string {
	const text = String(value);
	return /[.eE]/.test(text) ? text : `${text}.0`;
}

export function conditionExpression(
	question: CelQuestion,
	op: ConditionOp,
	operand: string | number | null,
	mode: CelMode
): string | null {
	const answer = `answers["${question.id}"]`;
	const member = `"${operand}" in ${answer}.selected_choices`;
	switch (op) {
		case 'is':
		case 'includes':
			return operand ? member : null;
		case 'is_not':
		case 'excludes':
			return operand ? `!(${member})` : null;
		case 'yes':
			return `${answer}.value == true`;
		case 'no':
			return `${answer}.value == false`;
		case 'answered':
			return `${answer}.answered`;
		case 'not_answered':
			return `!${answer}.answered`;
		default: {
			const value = typeof operand === 'number' ? operand : Number(operand);
			if (operand === null || operand === '' || !Number.isFinite(value)) return null;
			const test = `double(${answer}.value) ${op} ${doubleLiteral(value)}`;
			return mode === 'quick_form' ? `${answer}.answered && ${test}` : test;
		}
	}
}

/** Add `condition` to `expression`, keeping what was there grouped as written. */
export function joinCondition(expression: string, condition: string, join: '&&' | '||'): string {
	const current = expression.trim();
	if (!current) return condition;
	const grouped = join === '&&' && current.includes('||') ? `(${current})` : current;
	const added = condition.includes('||') ? `(${condition})` : condition;
	return `${grouped} ${join} ${added}`;
}

const CATALOG_KEY = Symbol('builderCelCatalog');

/** Share the catalog with the nested node blocks, read lazily so it stays current. */
export function setCelCatalogContext(read: () => CelCatalog) {
	setContext(CATALOG_KEY, read);
}

export function getCelCatalogContext(): () => CelCatalog {
	return (
		getContext<() => CelCatalog>(CATALOG_KEY) ??
		(() => ({ mode: 'framework', nodes: [], questions: [] }))
	);
}
