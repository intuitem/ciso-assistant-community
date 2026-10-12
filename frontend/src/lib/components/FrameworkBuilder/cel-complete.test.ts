import { describe, expect, test } from 'vitest';
import { ruleIdFromLabel, ruleIdProblem, type BuilderNode } from './builder-state';
import {
	buildCelCatalog,
	celSuggestions,
	conditionExpression,
	conditionOps,
	joinCondition,
	readableValues,
	type CelCatalog
} from './cel-complete';

const NS = 'urn:test:risk:qf_page:form';

function node(id: string, questions: BuilderNode['questions'], children: BuilderNode[] = []) {
	return {
		node: { urn: `${NS}:${id}`, name: id.toUpperCase(), assessable: false },
		questions,
		children,
		depth: 0
	} as unknown as BuilderNode;
}

function question(
	id: string,
	type: string,
	text: string,
	choices: string[] = [],
	page = 'context'
): BuilderNode['questions'][number] {
	const urn = `${NS}:${page}:question:${id}`;
	return {
		question: {
			urn,
			text,
			type,
			choices: choices.map((c) => ({ urn: `${urn}:choice:${c}`, value: c.toUpperCase() }))
		}
	} as unknown as BuilderNode['questions'][number];
}

const catalog: CelCatalog = buildCelCatalog(
	[
		node('context', [
			question('internet', 'boolean', 'Internet facing?'),
			question('data', 'unique_choice', 'Data handled', ['public', 'secret']),
			question('users', 'number', 'How many users?')
		]),
		node('notes', [question('comment', 'text', 'Comment', [], 'notes')])
	],
	'quick_form',
	[]
);
const RULE = { where: 'outcome' as const, values: ['risk'] };

const at = (text: string, place = RULE, explicit = false) =>
	celSuggestions(text, text.length, catalog, place, explicit);
const labels = (text: string, place = RULE, explicit = false) =>
	at(text, place, explicit)?.items.map((i) => i.label) ?? [];

describe('catalog', () => {
	test('lists top pages and every question with its saved choice ids', () => {
		expect(catalog.nodes.map((n) => n.id)).toEqual(['context', 'notes']);
		const data = catalog.questions.find((q) => q.id === 'context:question:data');
		expect(data?.choices.map((c) => c.id)).toEqual([
			'context:question:data:choice:public',
			'context:question:data:choice:secret'
		]);
		expect(data?.group).toBe('CONTEXT');
	});

	test('a number rule reads the number rules above it, a yes/no rule all of them', () => {
		const rules = [
			{ ref_id: 'a', kind: 'number' as const, annotation: '', color: null, expression: '' },
			{ ref_id: 'b', kind: 'number' as const, annotation: '', color: null, expression: '' },
			{ ref_id: 'flag', annotation: '', color: null, expression: '' }
		];
		expect(readableValues(rules, 0)).toEqual([]);
		expect(readableValues(rules, 1)).toEqual(['a']);
		expect(readableValues(rules, 2)).toEqual(['a', 'b']);
	});
});

describe('suggestions', () => {
	test('names of the form context, filtered by what is typed', () => {
		expect(labels('res')).toEqual(['response']);
		expect(labels('', RULE, true)).toContain('values');
		expect(labels('', { where: 'visibility' }, true)).not.toContain('values');
		expect(labels('')).toEqual([]);
	});

	test('question ids after answers[, matched on the question text too', () => {
		expect(labels('answers["')).toHaveLength(4);
		const found = at('answers["inter');
		expect(found?.items.map((i) => i.label)).toEqual(['context:question:internet']);
		expect(found?.items[0].insert).toBe('"context:question:internet"].');
		expect(found?.from).toBe('answers['.length);
		expect(labels('answers["Comment')).toEqual(['notes:question:comment']);
	});

	test('answer fields put the useful one first for the question type', () => {
		expect(labels('answers["context:question:data"].')[0]).toBe('selected_choices');
		expect(labels('answers["context:question:internet"].')[0]).toBe('value');
		expect(labels('pages["context"].sc')).toEqual(['score', 'score_max']);
	});

	test('fields and values after a dotted name', () => {
		expect(labels('response.comp')).toEqual(['complete', 'scored_complete']);
		expect(labels('values.')).toEqual(['risk']);
		expect(labels('values.', { where: 'visibility' })).toEqual([]);
	});

	test('true or false after comparing a yes/no answer', () => {
		expect(labels('answers["context:question:internet"].value == ')).toEqual(['true', 'false']);
	});

	test('an open string offers each choice as a membership test', () => {
		const found = at('"sec');
		expect(found?.items.map((i) => i.insert)).toEqual([
			'"context:question:data:choice:secret" in answers["context:question:data"].selected_choices'
		]);
		expect(found?.from).toBe(0);
	});

	test('a closed string or a finished name suggests nothing', () => {
		expect(at('"yes" ')).toBeNull();
		expect(at('response')).toBeNull();
	});

	test('the framework context has its own names', () => {
		const framework = { ...catalog, mode: 'framework' as const };
		const names = celSuggestions('', 0, framework, { where: 'outcome' }, true)?.items.map(
			(i) => i.label
		);
		expect(names).toContain('assessment');
		expect(names).not.toContain('response');
	});
});

describe('framework scores', () => {
	const tree = [
		{
			node: {
				urn: 'urn:test:risk:req_node:fw:gv',
				ref_id: 'GV',
				name: 'Govern',
				assessable: false
			},
			questions: [],
			children: [
				{
					node: { urn: 'urn:test:risk:req_node:fw:gv.oc-1', ref_id: 'GV.OC-1', assessable: true },
					questions: [],
					children: [],
					depth: 1
				}
			],
			depth: 0
		}
	] as unknown as BuilderNode[];
	const framework = buildCelCatalog(tree, 'framework', [{ id: 'B', label: 'basic' }]);
	const rule = { where: 'outcome' as const };
	const visibility = { where: 'visibility' as const };
	const at = (text: string, place: typeof rule | typeof visibility = rule) =>
		celSuggestions(text, text.length, framework, place)?.items.map((i) => i.label) ?? [];

	test('nodes with children are sections, requirements stay assessable nodes', () => {
		expect(framework.sections).toEqual([{ id: 'gv', label: 'GV Govern' }]);
		expect(framework.nodes.map((n) => n.id)).toEqual(['gv.oc-1']);
	});

	test('section and group ids, then their fields', () => {
		expect(at('sections["')).toEqual(['gv']);
		expect(at('groups["')).toEqual(['B']);
		expect(at('groups["B"].mat')).toEqual(['maturity_score', 'min_maturity_score']);
		expect(at('sections["gv"].de')).toEqual(['depth']);
	});

	test('the audit scores are for rules only', () => {
		expect(at('assessment.maturity')).toEqual(['maturity_score']);
		expect(at('assessment.maturity', visibility)).toEqual([]);
		expect(at('sections["', visibility)).toEqual([]);
		expect(at('sec', visibility)).toEqual([]);
		expect(at('sec')).toEqual(['sections']);
	});
});

describe('insert condition', () => {
	const q = (id: string) => catalog.questions.find((x) => x.id === `context:question:${id}`)!;

	test('operators follow the question type', () => {
		expect(conditionOps('boolean', 'quick_form')).toEqual([
			'yes',
			'no',
			'answered',
			'not_answered'
		]);
		expect(conditionOps('text', 'framework')).toEqual([]);
	});

	test('writes the expression for each kind of question', () => {
		expect(conditionExpression(q('internet'), 'yes', null, 'quick_form')).toBe(
			'answers["context:question:internet"].value == true'
		);
		expect(
			conditionExpression(q('data'), 'is_not', 'context:question:data:choice:secret', 'quick_form')
		).toBe(
			'!("context:question:data:choice:secret" in answers["context:question:data"].selected_choices)'
		);
		expect(conditionExpression(q('users'), '>=', 100, 'quick_form')).toBe(
			'answers["context:question:users"].answered && double(answers["context:question:users"].value) >= 100.0'
		);
		expect(conditionExpression(q('users'), '<', '2.5', 'framework')).toBe(
			'double(answers["context:question:users"].value) < 2.5'
		);
		expect(conditionExpression(q('data'), 'is', null, 'quick_form')).toBeNull();
		expect(conditionExpression(q('users'), '>', null, 'quick_form')).toBeNull();
	});

	test('joins keep what was written grouped', () => {
		expect(joinCondition('', 'b', '&&')).toBe('b');
		expect(joinCondition('a', 'b', '||')).toBe('a || b');
		expect(joinCondition('a || b', 'c', '&&')).toBe('(a || b) && c');
	});
});

describe('rule ids', () => {
	test('come from the label, as a name CEL can read, free among the others', () => {
		expect(ruleIdFromLabel('Inherent risk', [])).toBe('inherent_risk');
		expect(ruleIdFromLabel('Données sensibles !', [])).toBe('donnees_sensibles');
		expect(ruleIdFromLabel('3rd party', [])).toBe('rule_3rd_party');
		expect(ruleIdFromLabel('', ['rule'])).toBe('rule_2');
		expect(ruleIdFromLabel('High', ['high', 'high_2'])).toBe('high_3');
	});

	test('report what the server would refuse', () => {
		expect(ruleIdProblem('', [])).toBe('outcomeRuleIdRequired');
		expect(ruleIdProblem('inherent-risk', [])).toBe('outcomeRuleIdInvalid');
		expect(ruleIdProblem('high', ['high'])).toBe('outcomeRuleIdDuplicate');
		expect(ruleIdProblem('high', ['low'])).toBeNull();
	});
});
