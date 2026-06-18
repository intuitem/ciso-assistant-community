import { describe, it, expect } from 'vitest';
import { get } from 'svelte/store';
import {
	slugifyFrameworkName,
	computeRefId,
	generateUrn,
	extractNodeId,
	validateDraft,
	buildTree,
	serializeDraft,
	hydrateDraft,
	createBuilderState,
	inlineCopyFromCatalogEntry,
	type Framework,
	type BuilderNode,
	type RequirementNode,
	type Question
} from './builder-state';

const FW_ID = 'a1b2c3d4-0000-0000-0000-000000000000';

describe('slugifyFrameworkName', () => {
	it('converts ASCII names with special chars', () => {
		expect(slugifyFrameworkName('My Custom SOC2 Framework!', FW_ID)).toBe(
			'my-custom-soc2-framework'
		);
	});

	it('handles accented/NFKD characters', () => {
		expect(slugifyFrameworkName('Cadre de Conformit\u00e9 ISO', FW_ID)).toBe(
			'cadre-de-conformite-iso'
		);
		expect(slugifyFrameworkName('S\u00e9curit\u00e9 de l\u2019information', FW_ID)).toBe(
			'securite-de-linformation'
		);
	});

	it('falls back to UUID prefix for CJK-only names', () => {
		expect(slugifyFrameworkName('\u60c5\u5831\u30bb\u30ad\u30e5\u30ea\u30c6\u30a3', FW_ID)).toBe(
			'a1b2c3d4'
		);
	});

	it('falls back to UUID prefix for empty string', () => {
		expect(slugifyFrameworkName('', FW_ID)).toBe('a1b2c3d4');
	});

	it('truncates at 60 chars', () => {
		const longName = 'a'.repeat(80);
		const result = slugifyFrameworkName(longName, FW_ID);
		expect(result.length).toBeLessThanOrEqual(60);
		expect(result).toBe('a'.repeat(60));
	});
});

describe('computeRefId', () => {
	it('returns "1" for the first section with no siblings', () => {
		expect(computeRefId([], null, 'section')).toBe('1');
	});

	it('returns sequential number for sections', () => {
		expect(computeRefId(['1', '2'], null, 'section')).toBe('3');
	});

	it('handles gap after deletion (max+1, not count+1)', () => {
		expect(computeRefId(['1', '3'], null, 'section')).toBe('4');
	});

	it('computes requirement ref_id with parent', () => {
		expect(computeRefId(['2.1', '2.2'], '2', 'requirement')).toBe('2.3');
	});

	it('returns parent.1 for first requirement under a parent', () => {
		expect(computeRefId([], '2', 'requirement')).toBe('2.1');
	});

	it('handles null parent fallback for requirements', () => {
		expect(computeRefId([], null, 'requirement')).toBe('1');
	});

	it('filters non-numeric siblings with parseInt guard', () => {
		expect(computeRefId(['foo', 'bar', null], null, 'section')).toBe('4');
	});

	it('computes question ref_id', () => {
		expect(computeRefId(['2.1-q1', '2.1-q3'], '2.1', 'question')).toBe('2.1-q4');
	});

	it('computes first question ref_id', () => {
		expect(computeRefId([], '2.1', 'question')).toBe('2.1-q1');
	});

	it('computes choice ref_id', () => {
		expect(computeRefId(['2.1-q1-c1'], '2.1-q1', 'choice')).toBe('2.1-q1-c2');
	});

	it('computes first choice ref_id', () => {
		expect(computeRefId([], '2.1-q1', 'choice')).toBe('2.1-q1-c1');
	});
});

describe('generateUrn', () => {
	it('generates req_node URN with default namespace', () => {
		expect(generateUrn('req_node', 'my-soc2', '1.1')).toBe('urn:custom:risk:req_node:my-soc2:1.1');
	});

	it('generates question URN with custom namespace', () => {
		expect(generateUrn('question', 'my-soc2', '1.1-q1', 'myorg')).toBe(
			'urn:myorg:risk:question:my-soc2:1.1-q1'
		);
	});

	it('generates question_choice URN', () => {
		expect(generateUrn('question_choice', 'my-soc2', '1.1-q1-c1')).toBe(
			'urn:custom:risk:question_choice:my-soc2:1.1-q1-c1'
		);
	});
});

// --- Validation tests ---

function makeFramework(overrides: Partial<Framework> = {}): Framework {
	return {
		id: 'fw-1',
		name: 'Test Framework',
		description: null,
		annotation: null,
		folder: { id: 'folder-1', str: 'Root' },
		library: null,
		min_score: 0,
		max_score: 100,
		scores_definition: null,
		implementation_groups_definition: null,
		outcomes_definition: null,
		field_visibility: {},
		locale: 'en',
		urn: null,
		...overrides
	} as Framework;
}

function makeNode(overrides: Partial<RequirementNode> = {}): RequirementNode {
	return {
		id: 'node-1',
		urn: 'urn:intuitem:risk:req_node:node-1',
		ref_id: 'REQ-1',
		name: null,
		description: null,
		annotation: null,
		parent_urn: 'urn:intuitem:risk:req_node:section-1',
		order_id: 0,
		assessable: true,
		implementation_groups: null,
		typical_evidence: null,
		weight: 1,
		importance: '',
		display_mode: 'default',
		framework: 'fw-1',
		folder: 'folder-1',
		reference_controls: [],
		threats: [],
		...overrides
	};
}

function makeQuestion(overrides: Partial<Question> = {}): Question {
	return {
		id: 'q-1',
		urn: 'urn:custom:risk:question:fw:1-q1',
		ref_id: '1-q1',
		text: 'Q?',
		annotation: null,
		type: 'number',
		config: null,
		depends_on: null,
		order: 0,
		weight: 1,
		folder: 'folder-1',
		requirement_node: 'node-1',
		choices: [],
		...overrides
	};
}

function makeChoice(id: string, order: number) {
	return {
		id,
		urn: `urn:custom:risk:question_choice:fw:1-q1-c${order}`,
		ref_id: `1-q1-c${order}`,
		value: `Choice ${order}`,
		annotation: null,
		add_score: null,
		compute_result: null,
		order,
		description: null,
		color: null,
		select_implementation_groups: null,
		folder: 'folder-1',
		question: 'q-1'
	};
}

function makeSectionWithQuestion(question: Question): BuilderNode {
	return makeSection({}, [
		{
			node: makeNode({}),
			questions: [{ question }],
			children: [],
			depth: 1
		}
	]);
}

function makeSection(
	nodeOverrides: Partial<RequirementNode> = {},
	children: BuilderNode['children'] = []
): BuilderNode {
	return {
		node: makeNode({
			id: 'section-1',
			urn: 'urn:intuitem:risk:req_node:section-1',
			ref_id: 'SEC-1',
			parent_urn: null,
			assessable: false,
			name: 'Section 1',
			...nodeOverrides
		}),
		questions: [],
		children,
		depth: 0
	};
}

describe('validateDraft', () => {
	it('returns no errors when all fields are valid', () => {
		const fw = makeFramework();
		const sections = [
			makeSection({}, [
				{ node: makeNode({ name: 'Valid name' }), questions: [], children: [], depth: 0 }
			])
		];
		expect(validateDraft(fw, sections)).toHaveLength(0);
	});

	it('rejects name exceeding 200 characters', () => {
		const fw = makeFramework();
		const sections = [
			makeSection({}, [
				{
					node: makeNode({ name: 'A'.repeat(201) }),
					questions: [],
					children: [],
					depth: 0
				}
			])
		];
		const errors = validateDraft(fw, sections);
		expect(errors.length).toBeGreaterThan(0);
		expect(errors.find((e) => e.key === 'node-node-1')!.message).toContain('201/200');
	});

	it('rejects ref_id exceeding 100 characters', () => {
		const fw = makeFramework();
		const sections = [
			makeSection({}, [
				{
					node: makeNode({ ref_id: 'R'.repeat(101) }),
					questions: [],
					children: [],
					depth: 0
				}
			])
		];
		const errors = validateDraft(fw, sections);
		expect(errors.length).toBeGreaterThan(0);
		expect(errors.find((e) => e.key === 'node-node-1')!.message).toContain(
			'ref_id is 101 characters'
		);
	});

	it('rejects URN exceeding 255 characters', () => {
		const fw = makeFramework();
		const sections = [
			makeSection({}, [
				{
					node: makeNode({ urn: 'urn:' + 'x'.repeat(252) }),
					questions: [],
					children: [],
					depth: 0
				}
			])
		];
		const errors = validateDraft(fw, sections);
		expect(errors.length).toBeGreaterThan(0);
		expect(errors.find((e) => e.key === 'node-node-1')!.message).toContain('URN is 256 characters');
	});

	it('rejects empty framework name', () => {
		const fw = makeFramework({ name: '' });
		const sections = [makeSection()];
		const errors = validateDraft(fw, sections);
		expect(errors.find((e) => e.key === 'publish')!.message).toBe('Framework name is required.');
	});

	it('rejects number slider with min >= max', () => {
		const fw = makeFramework();
		const q = makeQuestion({
			type: 'number',
			config: { widget: 'slider', min: 10, max: 5, step: 1 }
		});
		const errors = validateDraft(fw, [makeSectionWithQuestion(q)]);
		expect(errors.find((e) => e.key === 'question-q-1')!.message).toContain(
			'Slider min must be less than max'
		);
	});

	it('rejects number slider with non-positive step', () => {
		const fw = makeFramework();
		const q = makeQuestion({
			type: 'number',
			config: { widget: 'slider', min: 0, max: 10, step: 0 }
		});
		const errors = validateDraft(fw, [makeSectionWithQuestion(q)]);
		expect(errors.find((e) => e.key === 'question-q-1')!.message).toContain(
			'Slider step must be greater than 0'
		);
	});

	it('rejects number slider with step larger than range', () => {
		const fw = makeFramework();
		const q = makeQuestion({
			type: 'number',
			config: { widget: 'slider', min: 0, max: 10, step: 20 }
		});
		const errors = validateDraft(fw, [makeSectionWithQuestion(q)]);
		expect(errors.find((e) => e.key === 'question-q-1')!.message).toContain(
			'Slider step cannot exceed (max − min)'
		);
	});

	it('accepts a valid number slider', () => {
		const fw = makeFramework();
		const q = makeQuestion({
			type: 'number',
			config: { widget: 'slider', min: 0, max: 100, step: 5 }
		});
		const errors = validateDraft(fw, [makeSectionWithQuestion(q)]);
		expect(errors.filter((e) => e.key === 'question-q-1')).toHaveLength(0);
	});

	it('rejects unique_choice slider with fewer than 2 choices', () => {
		const fw = makeFramework();
		const q = makeQuestion({
			type: 'unique_choice',
			config: { widget: 'slider' },
			choices: [makeChoice('c-1', 1)]
		});
		const errors = validateDraft(fw, [makeSectionWithQuestion(q)]);
		expect(errors.find((e) => e.key === 'question-q-1')!.message).toContain(
			'Slider needs at least 2 choices'
		);
	});

	it('accepts a valid unique_choice slider', () => {
		const fw = makeFramework();
		const q = makeQuestion({
			type: 'unique_choice',
			config: { widget: 'slider' },
			choices: [makeChoice('c-1', 1), makeChoice('c-2', 2)]
		});
		const errors = validateDraft(fw, [makeSectionWithQuestion(q)]);
		expect(errors.filter((e) => e.key === 'question-q-1')).toHaveLength(0);
	});

	it('ignores config validation for non-slider widgets', () => {
		const fw = makeFramework();
		const q = makeQuestion({
			type: 'number',
			config: null
		});
		const errors = validateDraft(fw, [makeSectionWithQuestion(q)]);
		expect(errors.filter((e) => e.key === 'question-q-1')).toHaveLength(0);
	});
});

describe('buildTree', () => {
	it('preserves a single top-level assessable node as one root node (no wrapper)', () => {
		const n: RequirementNode = {
			id: 'n1',
			urn: 'urn:x:req_node:fw:1',
			ref_id: '1',
			name: 'Top-level assessable',
			description: null,
			annotation: null,
			parent_urn: null,
			order_id: 0,
			assessable: true,
			implementation_groups: null,
			visibility_expression: null,
			typical_evidence: null,
			weight: 1,
			importance: '',
			display_mode: 'default',
			framework: 'fw-1',
			folder: 'folder-1'
		};
		const tree = buildTree([n], []);
		expect(tree).toHaveLength(1);
		expect(tree[0].node.id).toBe('n1');
		expect(tree[0].node.assessable).toBe(true);
		expect(tree[0].children).toHaveLength(0);
	});

	it('preserves an assessable parent with assessable children', () => {
		const parent: RequirementNode = {
			id: 'p1',
			urn: 'urn:x:req_node:fw:1',
			ref_id: '1',
			name: 'Assessable parent',
			description: null,
			annotation: null,
			parent_urn: null,
			order_id: 0,
			assessable: true,
			implementation_groups: null,
			visibility_expression: null,
			typical_evidence: null,
			weight: 1,
			importance: '',
			display_mode: 'default',
			framework: 'fw-1',
			folder: 'folder-1'
		};
		const child: RequirementNode = {
			...parent,
			id: 'c1',
			urn: 'urn:x:req_node:fw:1.1',
			ref_id: '1.1',
			parent_urn: 'urn:x:req_node:fw:1',
			order_id: 0
		};
		const tree = buildTree([parent, child], []);
		expect(tree).toHaveLength(1);
		expect(tree[0].node.id).toBe('p1');
		expect(tree[0].node.assessable).toBe(true);
		expect(tree[0].children).toHaveLength(1);
		expect(tree[0].children[0].node.id).toBe('c1');
	});
});

import { createBuilderState } from './builder-state';

describe('addNode', () => {
	function newStore() {
		const fw = makeFramework();
		return createBuilderState(fw, [], []);
	}

	it('creates a non-assessable group when preset is "group"', () => {
		const s = newStore();
		s.addNode({ parent: null, preset: 'group' });
		const roots = get(s.rootNodes);
		expect(roots).toHaveLength(1);
		expect(roots[0].node.assessable).toBe(false);
		expect(roots[0].node.display_mode).toBe('default');
	});

	it('creates an assessable leaf when preset is "requirement"', () => {
		const s = newStore();
		s.addNode({ parent: null, preset: 'requirement' });
		const roots = get(s.rootNodes);
		expect(roots[0].node.assessable).toBe(true);
		expect(roots[0].node.display_mode).toBe('default');
	});

	it('creates a splash node when preset is "splash"', () => {
		const s = newStore();
		s.addNode({ parent: null, preset: 'splash' });
		const roots = get(s.rootNodes);
		expect(roots[0].node.assessable).toBe(false);
		expect(roots[0].node.display_mode).toBe('splash');
	});

	it('nests a child under a given parent', () => {
		const s = newStore();
		s.addNode({ parent: null, preset: 'group' });
		const parentId = get(s.rootNodes)[0].node.id;
		s.addNode({ parent: parentId, preset: 'requirement' });
		const roots = get(s.rootNodes);
		expect(roots[0].children).toHaveLength(1);
		expect(roots[0].children[0].node.assessable).toBe(true);
	});

	it('defaults to a blank node (non-assessable leaf) when preset is omitted', () => {
		const s = newStore();
		s.addNode({ parent: null });
		const roots = get(s.rootNodes);
		expect(roots[0].node.assessable).toBe(false);
		expect(roots[0].node.display_mode).toBe('default');
	});
});

describe('serializeDraft round-trip', () => {
	it('does not emit the same node twice for a flat framework', () => {
		const fw = makeFramework();
		const n: RequirementNode = {
			id: 'n1',
			urn: 'urn:x:req_node:fw:1',
			ref_id: '1',
			name: 'Top-level assessable',
			description: null,
			annotation: null,
			parent_urn: null,
			order_id: 0,
			assessable: true,
			implementation_groups: null,
			visibility_expression: null,
			typical_evidence: null,
			weight: 1,
			importance: '',
			display_mode: 'default',
			framework: 'fw-1',
			folder: 'folder-1'
		};
		const tree = buildTree([n], []);
		const draft = serializeDraft(fw, tree);
		const ids = draft.nodes.map((x) => x.id);
		expect(new Set(ids).size).toBe(ids.length);
		expect(ids).toEqual(['n1']);
	});
});

describe('reference controls & threats round-trip', () => {
	it('preserves node links and inline collections through serialize/hydrate', () => {
		const fw = makeFramework({
			inline_reference_controls: [
				{
					id: 'rc-1',
					urn: 'urn:custom:risk:reference_control:fw:c1',
					ref_id: 'C1',
					name: 'Inline C1',
					description: null,
					annotation: null,
					category: 'policy',
					csf_function: 'govern',
					typical_evidence: null,
					translations: null
				}
			],
			inline_threats: [
				{
					id: 't-1',
					urn: 'urn:custom:risk:threat:fw:t1',
					ref_id: 'T1',
					name: 'Inline T1',
					description: null,
					annotation: null,
					translations: null
				}
			]
		});
		const node = makeNode({
			parent_urn: null,
			reference_controls: [
				'urn:custom:risk:reference_control:fw:c1',
				'urn:intuitem:risk:function:doc-pol:a.5.1'
			],
			threats: ['urn:custom:risk:threat:fw:t1']
		});
		const tree = buildTree([node], []);

		const draft = serializeDraft(fw, tree);
		expect(draft.nodes[0].reference_controls).toEqual(node.reference_controls);
		expect(draft.nodes[0].threats).toEqual(node.threats);
		expect(draft.reference_controls).toHaveLength(1);
		expect(draft.threats).toHaveLength(1);

		const { frameworkPatch, nodes } = hydrateDraft(draft, fw.id);
		expect(nodes[0].reference_controls).toEqual(node.reference_controls);
		expect(nodes[0].threats).toEqual(node.threats);
		expect(frameworkPatch.inline_reference_controls).toHaveLength(1);
		expect(frameworkPatch.inline_threats).toHaveLength(1);
		expect(frameworkPatch.inline_reference_controls?.[0].urn).toBe(
			'urn:custom:risk:reference_control:fw:c1'
		);
	});
});

describe('indentNode', () => {
	function newStore() {
		return createBuilderState(makeFramework(), [], []);
	}

	it('indents a root node under its previous sibling', () => {
		const s = newStore();
		s.addNode({ parent: null, preset: 'group' }); // idx 0
		s.addNode({ parent: null, preset: 'requirement' }); // idx 1
		const roots = get(s.rootNodes);
		const id = roots[1].node.id;
		const prevUrn = roots[0].node.urn;

		const ok = s.indentNode(id);
		expect(ok).toBe(true);
		const after = get(s.rootNodes);
		expect(after).toHaveLength(1);
		expect(after[0].node.id).toBe(roots[0].node.id);
		expect(after[0].children).toHaveLength(1);
		expect(after[0].children[0].node.id).toBe(id);
		expect(after[0].children[0].node.parent_urn).toBe(prevUrn);
		expect(after[0].children[0].depth).toBe(1);
	});

	it('is a no-op for the first sibling (no previous sibling to nest under)', () => {
		const s = newStore();
		s.addNode({ parent: null, preset: 'requirement' });
		const id = get(s.rootNodes)[0].node.id;
		const ok = s.indentNode(id);
		expect(ok).toBe(false);
		expect(get(s.rootNodes)).toHaveLength(1);
	});

	it('indents a nested node under its previous sibling', () => {
		const s = newStore();
		s.addNode({ parent: null, preset: 'group' });
		const group = get(s.rootNodes)[0].node.id;
		s.addNode({ parent: group, preset: 'requirement' });
		s.addNode({ parent: group, preset: 'requirement' });
		const targetId = get(s.rootNodes)[0].children[1].node.id;
		const prevUrn = get(s.rootNodes)[0].children[0].node.urn;

		const ok = s.indentNode(targetId);
		expect(ok).toBe(true);
		const roots = get(s.rootNodes);
		expect(roots[0].children).toHaveLength(1);
		expect(roots[0].children[0].children).toHaveLength(1);
		expect(roots[0].children[0].children[0].node.id).toBe(targetId);
		expect(roots[0].children[0].children[0].node.parent_urn).toBe(prevUrn);
		expect(roots[0].children[0].children[0].depth).toBe(2);
	});
});

describe('outdentNode', () => {
	function newStore() {
		return createBuilderState(makeFramework(), [], []);
	}

	it('promotes a nested node to be a sibling of its parent', () => {
		const s = newStore();
		s.addNode({ parent: null, preset: 'group' });
		const group = get(s.rootNodes)[0].node.id;
		s.addNode({ parent: group, preset: 'requirement' });
		const targetId = get(s.rootNodes)[0].children[0].node.id;

		const ok = s.outdentNode(targetId);
		expect(ok).toBe(true);
		const roots = get(s.rootNodes);
		expect(roots).toHaveLength(2);
		// Outdented node lands immediately after its former parent
		expect(roots[1].node.id).toBe(targetId);
		expect(roots[1].node.parent_urn).toBeNull();
		expect(roots[1].depth).toBe(0);
		// Former parent has no more children
		expect(roots[0].children).toHaveLength(0);
	});

	it('is a no-op for a root node (nothing to outdent to)', () => {
		const s = newStore();
		s.addNode({ parent: null, preset: 'requirement' });
		const id = get(s.rootNodes)[0].node.id;
		const ok = s.outdentNode(id);
		expect(ok).toBe(false);
		expect(get(s.rootNodes)).toHaveLength(1);
	});

	it('promotes a deeply nested node to its grandparent', () => {
		const s = newStore();
		s.addNode({ parent: null, preset: 'group' });
		const top = get(s.rootNodes)[0].node.id;
		s.addNode({ parent: top, preset: 'group' });
		const mid = get(s.rootNodes)[0].children[0].node.id;
		s.addNode({ parent: mid, preset: 'requirement' });
		const targetId = get(s.rootNodes)[0].children[0].children[0].node.id;

		const ok = s.outdentNode(targetId);
		expect(ok).toBe(true);
		const roots = get(s.rootNodes);
		// Target moves from depth 2 (inside mid) to depth 1 (as sibling of mid under top)
		expect(roots).toHaveLength(1);
		expect(roots[0].children).toHaveLength(2);
		expect(roots[0].children[1].node.id).toBe(targetId);
		expect(roots[0].children[1].node.parent_urn).toBe(get(s.rootNodes)[0].node.urn);
		expect(roots[0].children[1].depth).toBe(1);
	});
});

describe('toggleAssessable', () => {
	function newStore() {
		return createBuilderState(makeFramework(), [], []);
	}

	it('flips a group node to assessable', () => {
		const s = newStore();
		s.addNode({ parent: null, preset: 'group' });
		const id = get(s.rootNodes)[0].node.id;
		expect(get(s.rootNodes)[0].node.assessable).toBe(false);
		s.toggleAssessable(id);
		expect(get(s.rootNodes)[0].node.assessable).toBe(true);
	});

	it('flips an assessable node back to non-assessable', () => {
		const s = newStore();
		s.addNode({ parent: null, preset: 'requirement' });
		const id = get(s.rootNodes)[0].node.id;
		s.toggleAssessable(id);
		expect(get(s.rootNodes)[0].node.assessable).toBe(false);
	});

	it('works on nested nodes', () => {
		const s = newStore();
		s.addNode({ parent: null, preset: 'group' });
		const parentId = get(s.rootNodes)[0].node.id;
		s.addNode({ parent: parentId, preset: 'group' });
		const childId = get(s.rootNodes)[0].children[0].node.id;
		s.toggleAssessable(childId);
		expect(get(s.rootNodes)[0].children[0].node.assessable).toBe(true);
	});
});

describe('translation operations on top-level requirement nodes', () => {
	function seedTopLevelWithQuestion() {
		const fw = makeFramework({
			locale: 'en',
			available_languages: ['en', 'fr'],
			translations: {}
		});
		const node = makeNode({
			id: 'top-1',
			urn: 'urn:x:req_node:fw:1',
			ref_id: '1',
			parent_urn: null,
			name: 'Top requirement',
			translations: { fr: { name: 'Exigence racine' } }
		});
		const question: Question = {
			id: 'q-1',
			urn: 'urn:x:question:fw:1-q1',
			ref_id: '1-q1',
			text: 'Is it true?',
			annotation: null,
			type: 'unique_choice',
			config: null,
			depends_on: null,
			order: 0,
			weight: 1,
			folder: 'folder-1',
			requirement_node: 'top-1',
			translations: { fr: { text: 'Est-ce vrai ?' } },
			choices: [
				{
					id: 'c-1',
					urn: 'urn:x:question_choice:fw:1-q1-c1',
					ref_id: '1-q1-c1',
					value: 'Yes',
					annotation: null,
					add_score: null,
					compute_result: null,
					order: 0,
					description: null,
					color: null,
					select_implementation_groups: null,
					folder: 'folder-1',
					question: 'q-1',
					translations: { fr: { value: 'Oui' } }
				}
			]
		};
		return createBuilderState(fw, [node], [question]);
	}

	it('setBaseLocale swaps question and choice text on a top-level node', () => {
		const s = seedTopLevelWithQuestion();
		s.setBaseLocale('fr');
		const root = get(s.rootNodes)[0];
		expect(root.questions[0].question.text).toBe('Est-ce vrai ?');
		expect(root.questions[0].question.translations?.en?.text).toBe('Is it true?');
		expect(root.questions[0].question.choices[0].value).toBe('Oui');
		expect(root.questions[0].question.choices[0].translations?.en?.value).toBe('Yes');
	});

	it('getTranslationProgress counts questions and choices on a top-level node', () => {
		const s = seedTopLevelWithQuestion();
		// 3 translatable strings: node.name, question.text, choice.value — all already have fr.
		expect(s.getTranslationProgress('fr')).toEqual({ translated: 3, total: 3 });
	});

	it('copyFromBase seeds translations for a top-level node question and choice', () => {
		const fw = makeFramework({ locale: 'en', available_languages: ['en', 'de'] });
		const node = makeNode({
			id: 'top-1',
			urn: 'urn:x:req_node:fw:1',
			ref_id: '1',
			parent_urn: null,
			name: 'Top requirement'
		});
		const question: Question = {
			id: 'q-1',
			urn: 'urn:x:question:fw:1-q1',
			ref_id: '1-q1',
			text: 'Is it true?',
			annotation: null,
			type: 'unique_choice',
			config: null,
			depends_on: null,
			order: 0,
			weight: 1,
			folder: 'folder-1',
			requirement_node: 'top-1',
			choices: [
				{
					id: 'c-1',
					urn: 'urn:x:question_choice:fw:1-q1-c1',
					ref_id: '1-q1-c1',
					value: 'Yes',
					annotation: null,
					add_score: null,
					compute_result: null,
					order: 0,
					description: null,
					color: null,
					select_implementation_groups: null,
					folder: 'folder-1',
					question: 'q-1'
				}
			]
		};
		const s = createBuilderState(fw, [node], [question]);
		s.copyFromBase('de');
		const root = get(s.rootNodes)[0];
		expect(root.questions[0].question.translations?.de?.text).toBe('Is it true?');
		expect(root.questions[0].question.choices[0].translations?.de?.value).toBe('Yes');
	});
});

describe('question and choice CRUD on top-level requirement nodes', () => {
	function newStore() {
		return createBuilderState(makeFramework(), [], []);
	}

	it('adds a question to a top-level assessable node', () => {
		const s = newStore();
		s.addNode({ parent: null, preset: 'requirement' });
		const id = get(s.rootNodes)[0].node.id;
		s.addQuestion(id);
		expect(get(s.rootNodes)[0].questions).toHaveLength(1);
	});

	it('updates a question that lives on a top-level node', () => {
		const s = newStore();
		s.addNode({ parent: null, preset: 'requirement' });
		const id = get(s.rootNodes)[0].node.id;
		s.addQuestion(id);
		const qId = get(s.rootNodes)[0].questions[0].question.id;
		s.updateQuestion(qId, { text: 'hello' });
		expect(get(s.rootNodes)[0].questions[0].question.text).toBe('hello');
	});

	it('deletes a question from a top-level node', () => {
		const s = newStore();
		s.addNode({ parent: null, preset: 'requirement' });
		const id = get(s.rootNodes)[0].node.id;
		s.addQuestion(id);
		s.addQuestion(id);
		s.deleteQuestion(id, 0);
		expect(get(s.rootNodes)[0].questions).toHaveLength(1);
	});

	it('adds and updates a choice on a top-level node question', () => {
		const s = newStore();
		s.addNode({ parent: null, preset: 'requirement' });
		const id = get(s.rootNodes)[0].node.id;
		s.addQuestion(id);
		s.addChoice(id, 0);
		const choices = get(s.rootNodes)[0].questions[0].question.choices;
		expect(choices).toHaveLength(1);
		s.updateChoice(choices[0].id, { value: 'yes' });
		expect(get(s.rootNodes)[0].questions[0].question.choices[0].value).toBe('yes');
	});

	it('deletes a choice from a top-level node question', () => {
		const s = newStore();
		s.addNode({ parent: null, preset: 'requirement' });
		const id = get(s.rootNodes)[0].node.id;
		s.addQuestion(id);
		s.addChoice(id, 0);
		s.addChoice(id, 0);
		s.deleteChoice(id, 0, 0);
		expect(get(s.rootNodes)[0].questions[0].question.choices).toHaveLength(1);
	});

	it('reorders questions on a top-level node', () => {
		const s = newStore();
		s.addNode({ parent: null, preset: 'requirement' });
		const id = get(s.rootNodes)[0].node.id;
		s.addQuestion(id);
		s.addQuestion(id);
		const firstId = get(s.rootNodes)[0].questions[0].question.id;
		s.reorderQuestions(id, 0, 1);
		expect(get(s.rootNodes)[0].questions[1].question.id).toBe(firstId);
	});
});

describe('extractNodeId', () => {
	it('returns everything after the 5th colon', () => {
		expect(extractNodeId('urn:custom:risk:req_node:my-fw:2.1')).toBe('2.1');
	});

	it('preserves node_ids that themselves contain colons', () => {
		expect(extractNodeId('urn:custom:risk:question:my-fw:2.1:q1')).toBe('2.1:q1');
	});

	it('returns null for short or empty URNs', () => {
		expect(extractNodeId('urn:custom:risk:req_node:my-fw')).toBeNull();
		expect(extractNodeId(null)).toBeNull();
		expect(extractNodeId(undefined)).toBeNull();
	});
});

describe('node_id uniqueness on creation', () => {
	it('disambiguates a new node_id that collides with a renamed/moved node', () => {
		const fw = makeFramework({ urn_namespace: 'custom', ref_id: 'fw' });
		// Node A's displayed ref_id was renamed to "2.9" but its URN keeps the
		// frozen node_id "2.1". Node P is the parent a new "2.1" will compute under.
		const nodeP = makeNode({
			id: 'p',
			urn: 'urn:custom:risk:req_node:fw:2',
			ref_id: '2',
			parent_urn: null
		});
		const nodeA = makeNode({
			id: 'a',
			urn: 'urn:custom:risk:req_node:fw:2.1',
			ref_id: '2.9',
			parent_urn: null
		});
		const s = createBuilderState(fw, [nodeP, nodeA], []);
		s.addNode({ parent: 'p', preset: 'requirement' });
		const parent = get(s.rootNodes).find((r) => r.node.id === 'p')!;
		const child = parent.children[0];
		// Display ref_id stays the natural "2.1"; the URN node_id is disambiguated.
		expect(child.node.ref_id).toBe('2.1');
		expect(extractNodeId(child.node.urn)).toBe('2.1-2');
	});
});

describe('node_id repair on draft load', () => {
	function draftWithDuplicateNodeIds() {
		return {
			schema_version: 1,
			framework_meta: {
				name: 'F',
				description: null,
				min_score: 0,
				max_score: 100,
				scores_definition: null,
				implementation_groups_definition: null,
				outcomes_definition: null,
				urn_namespace: 'custom',
				ref_id: 'fw'
			},
			nodes: [
				{
					id: 'a',
					urn: 'urn:custom:risk:req_node:fw:2.1',
					ref_id: '2.1',
					name: 'Alpha',
					parent_urn: null,
					order_id: 0,
					assessable: true
				},
				{
					id: 'b',
					urn: 'urn:custom:risk:req_node:fw:2.1',
					ref_id: '2.1',
					name: 'Beta',
					parent_urn: null,
					order_id: 1,
					assessable: true
				}
			],
			questions: [],
			choices: []
		};
	}

	it('gives colliding nodes distinct node_ids and marks the draft unsaved', () => {
		const s = createBuilderState(makeFramework(), [], [], draftWithDuplicateNodeIds());
		const roots = get(s.rootNodes);
		const nodeIds = roots.map((r) => extractNodeId(r.node.urn));
		expect(nodeIds).toHaveLength(2);
		expect(new Set(nodeIds).size).toBe(2); // no longer duplicated
		expect(nodeIds).toContain('2.1'); // first occurrence kept
		expect(get(s.unsaved)).toBe(true); // repair persists on next save
		expect(get(s.unpublished)).toBe(true);
	});

	it('restores the original node_id from ref_id when the URN drifted onto a sibling', () => {
		// Node B's URN was corrupted to A's, but its ref_id "2.2" is intact and
		// free — the repair must restore ":2.2" (matching the DB row) rather
		// than mint ":2.1-2", otherwise the publish-time URN lock rejects the
		// repaired draft on frameworks with audits.
		const draft = draftWithDuplicateNodeIds();
		draft.nodes[1].ref_id = '2.2';
		const s = createBuilderState(makeFramework(), [], [], draft);
		const beta = get(s.rootNodes).find((r) => r.node.name === 'Beta')!;
		expect(extractNodeId(beta.node.urn)).toBe('2.2');
	});

	it('keeps ambiguous children on the first occurrence; duplicate becomes a leaf', () => {
		const draft = draftWithDuplicateNodeIds();
		// A child pointing at the shared URN ":2.1" — genuinely ambiguous.
		draft.nodes.push({
			id: 'child',
			urn: 'urn:custom:risk:req_node:fw:2.1.1',
			ref_id: '2.1.1',
			name: 'Child',
			parent_urn: 'urn:custom:risk:req_node:fw:2.1',
			order_id: 0,
			assessable: true
		});
		const s = createBuilderState(makeFramework(), [], [], draft);
		const roots = get(s.rootNodes);
		const alpha = roots.find((r) => r.node.name === 'Alpha')!;
		const beta = roots.find((r) => r.node.name === 'Beta')!;
		// Alpha (first occurrence) keeps node_id "2.1" and the ambiguous child.
		expect(extractNodeId(alpha.node.urn)).toBe('2.1');
		expect(alpha.children).toHaveLength(1);
		expect(alpha.children[0].node.name).toBe('Child');
		// Beta (duplicate) got a fresh node_id and is now a standalone leaf.
		expect(extractNodeId(beta.node.urn)).not.toBe('2.1');
		expect(beta.children).toHaveLength(0);
	});
});

describe('URN rewrite on namespace / ref_id change', () => {
	it('rewrites node, question, depends_on and choice URNs when ref_id changes', () => {
		const fw = makeFramework({ ref_id: 'old', urn_namespace: 'custom' });
		const node = makeNode({
			urn: 'urn:custom:risk:req_node:old:1',
			ref_id: '1',
			parent_urn: null
		});
		const q: Question = {
			...makeQuestion({ requirement_node: node.id }),
			urn: 'urn:custom:risk:question:old:1-q1',
			depends_on: {
				question: 'urn:custom:risk:question:old:1-q2',
				answers: ['urn:custom:risk:question_choice:old:1-q2-c1']
			},
			choices: [
				{
					...makeChoice('c1', 1),
					urn: 'urn:custom:risk:question_choice:old:1-q1-c1',
					question: node.id
				}
			]
		};
		const store = createBuilderState(fw, [node], [q]);

		store.updateFramework({ ref_id: 'new' });

		const root = get(store.rootNodes)[0];
		expect(root.node.urn).toBe('urn:custom:risk:req_node:new:1');
		const question = root.questions[0].question;
		expect(question.urn).toBe('urn:custom:risk:question:new:1-q1');
		const dep = question.depends_on as { question: string; answers: string[] };
		expect(dep.question).toBe('urn:custom:risk:question:new:1-q2');
		expect(dep.answers[0]).toBe('urn:custom:risk:question_choice:new:1-q2-c1');
		expect(question.choices[0].urn).toBe('urn:custom:risk:question_choice:new:1-q1-c1');
	});

	it('rewrites the namespace segment too, preserving node_id', () => {
		const fw = makeFramework({ ref_id: 'fw', urn_namespace: 'custom' });
		const node = makeNode({
			urn: 'urn:custom:risk:req_node:fw:1',
			ref_id: '1',
			parent_urn: null
		});
		const store = createBuilderState(fw, [node], []);

		store.updateFramework({ urn_namespace: 'myorg' });

		expect(get(store.rootNodes)[0].node.urn).toBe('urn:myorg:risk:req_node:fw:1');
	});

	it('does not rewrite URNs when compliance assessments lock them', () => {
		const fw = makeFramework({
			ref_id: 'old',
			urn_namespace: 'custom',
			has_compliance_assessments: true
		});
		const node = makeNode({
			urn: 'urn:custom:risk:req_node:old:1',
			ref_id: '1',
			parent_urn: null
		});
		const store = createBuilderState(fw, [node], []);

		store.updateFramework({ ref_id: 'new' });

		expect(get(store.rootNodes)[0].node.urn).toBe('urn:custom:risk:req_node:old:1');
	});
});

describe('duplicate question node_id repair on hydrate', () => {
	it('de-dupes question node_ids carried by a draft', () => {
		const draft = {
			schema_version: 1,
			framework_meta: {
				name: 'X',
				description: null,
				min_score: 0,
				max_score: 100,
				scores_definition: null,
				implementation_groups_definition: null,
				outcomes_definition: null,
				urn_namespace: 'custom',
				ref_id: 'fw'
			},
			nodes: [
				{
					id: 'n1',
					urn: 'urn:custom:risk:req_node:fw:1',
					ref_id: '1',
					assessable: true,
					parent_urn: null,
					order_id: 0
				}
			],
			questions: [
				{
					id: 'q1',
					urn: 'urn:custom:risk:question:fw:1-q1',
					ref_id: '1-q1',
					requirement_node_id: 'n1',
					type: 'text',
					order: 0
				},
				{
					id: 'q2',
					urn: 'urn:custom:risk:question:fw:1-q1', // duplicate node_id
					ref_id: '1-q2',
					requirement_node_id: 'n1',
					type: 'text',
					order: 1
				}
			],
			choices: []
		};

		const store = createBuilderState(makeFramework(), [], [], draft as never);

		const urns = get(store.rootNodes)[0].questions.map((bq) => bq.question.urn);
		expect(new Set(urns).size).toBe(2);
	});
});

describe('self-heals legacy (pre-v3.18.0) seeded drafts on load', () => {
	// Mirrors the exact drafts seeded for manual repro: pre-v3.18.0 the builder
	// set node_id == ref_id with no dedup, so two questions collide on node_id.
	const legacyDraft = (questions: Record<string, unknown>[], refId = 'oldfw') => ({
		schema_version: 1,
		framework_meta: {
			name: 'X',
			description: '',
			urn_namespace: 'custom',
			ref_id: refId,
			min_score: 0,
			max_score: 100,
			scores_definition: null,
			implementation_groups_definition: null,
			outcomes_definition: null
		},
		nodes: [
			{
				id: 'n1',
				urn: 'urn:custom:risk:req_node:oldfw:1',
				ref_id: '1',
				name: 'S1',
				assessable: true,
				parent_urn: null,
				order_id: 0
			}
		],
		questions,
		choices: []
	});

	it('same-slug exact-duplicate questions get distinct URNs (Duplicate URN repro)', () => {
		const draft = legacyDraft([
			{
				id: 'q1',
				urn: 'urn:custom:risk:question:oldfw:1-q1',
				ref_id: '1-q1',
				requirement_node_id: 'n1',
				type: 'text',
				text: 'Q1',
				order: 0
			},
			{
				id: 'q2',
				urn: 'urn:custom:risk:question:oldfw:1-q1',
				ref_id: '1-q1',
				requirement_node_id: 'n1',
				type: 'text',
				text: 'Q2',
				order: 1
			}
		]);
		const store = createBuilderState(makeFramework(), [], [], draft as never);
		const urns = get(store.rootNodes)[0].questions.map((bq) => bq.question.urn);
		expect(new Set(urns).size).toBe(2);
	});

	it('divergent-slug duplicate node_ids are de-duped so a rename cannot collapse them (opaque repro)', () => {
		const draft = legacyDraft(
			[
				{
					id: 'q1',
					urn: 'urn:custom:risk:question:oldfw:1-q1',
					ref_id: '1-q1',
					requirement_node_id: 'n1',
					type: 'text',
					text: 'Q1',
					order: 0
				},
				{
					id: 'q2',
					urn: 'urn:custom:risk:question:other:1-q1',
					ref_id: '1-q2',
					requirement_node_id: 'n1',
					type: 'text',
					text: 'Q2',
					order: 1
				}
			],
			'renamedfw'
		);
		const store = createBuilderState(makeFramework(), [], [], draft as never);
		const nodeIds = get(store.rootNodes)[0].questions.map((bq) => extractNodeId(bq.question.urn));
		expect(new Set(nodeIds).size).toBe(2);
	});
});

describe('URN rewrite & repair — gap coverage', () => {
	it('re-slugs children when the name changes and ref_id is empty', () => {
		const fw = makeFramework({ name: 'Old Name', ref_id: null });
		const node = makeNode({
			urn: 'urn:custom:risk:req_node:old-name:1',
			ref_id: '1',
			parent_urn: null
		});
		const store = createBuilderState(fw, [node], []);

		store.updateFramework({ name: 'New Name' });

		expect(get(store.rootNodes)[0].node.urn).toBe('urn:custom:risk:req_node:new-name:1');
	});

	it('does not rewrite child URNs when a non-slug field changes', () => {
		const fw = makeFramework({ ref_id: 'fw' });
		const node = makeNode({
			urn: 'urn:custom:risk:req_node:fw:1',
			ref_id: '1',
			parent_urn: null
		});
		const store = createBuilderState(fw, [node], []);

		store.updateFramework({ description: 'changed' });

		expect(get(store.rootNodes)[0].node.urn).toBe('urn:custom:risk:req_node:fw:1');
	});

	it('repairs duplicate choice node_ids on hydrate', () => {
		const draft = {
			schema_version: 1,
			framework_meta: {
				name: 'X',
				description: '',
				urn_namespace: 'custom',
				ref_id: 'fw',
				min_score: 0,
				max_score: 100,
				scores_definition: null,
				implementation_groups_definition: null,
				outcomes_definition: []
			},
			nodes: [
				{
					id: 'n1',
					urn: 'urn:custom:risk:req_node:fw:1',
					ref_id: '1',
					name: 'S',
					assessable: true,
					parent_urn: null,
					order_id: 0
				}
			],
			questions: [
				{
					id: 'q1',
					urn: 'urn:custom:risk:question:fw:1-q1',
					ref_id: '1-q1',
					requirement_node_id: 'n1',
					type: 'unique_choice',
					text: 'Q',
					order: 0
				}
			],
			choices: [
				{
					id: 'c1',
					urn: 'urn:custom:risk:question_choice:fw:1-q1-c1',
					ref_id: '1-q1-c1',
					question_id: 'q1',
					value: 'A',
					order: 0
				},
				{
					id: 'c2',
					urn: 'urn:custom:risk:question_choice:fw:1-q1-c1', // duplicate node_id
					ref_id: '1-q1-c2',
					question_id: 'q1',
					value: 'B',
					order: 1
				}
			]
		};

		const store = createBuilderState(makeFramework(), [], [], draft as never);

		const choiceUrns = get(store.rootNodes)[0].questions[0].question.choices.map((c) => c.urn);
		expect(new Set(choiceUrns).size).toBe(2);
	});
});

describe('inline object field round-trip (pass 1: description, annotation, csf_function)', () => {
	it('serialize/hydrate preserves description, annotation and csf_function', () => {
		const fw = makeFramework({
			inline_reference_controls: [
				{
					id: 'rc-1',
					urn: 'urn:custom:risk:reference_control:fw:c1',
					ref_id: 'C1',
					name: 'Inline C1',
					description: 'a description',
					annotation: 'an annotation',
					category: 'policy',
					csf_function: 'govern',
					typical_evidence: null,
					translations: null
				}
			],
			inline_threats: [
				{
					id: 't-1',
					urn: 'urn:custom:risk:threat:fw:t1',
					ref_id: 'T1',
					name: 'Inline T1',
					description: 'threat desc',
					annotation: 'threat ann',
					translations: null
				}
			]
		});

		const draft = serializeDraft(fw, []);
		const rc = (draft.reference_controls ?? [])[0] as Record<string, unknown>;
		expect(rc.description).toBe('a description');
		expect(rc.annotation).toBe('an annotation');
		expect(rc.csf_function).toBe('govern');
		const th = (draft.threats ?? [])[0] as Record<string, unknown>;
		expect(th.description).toBe('threat desc');
		expect(th.annotation).toBe('threat ann');

		const { frameworkPatch } = hydrateDraft(draft, fw.id);
		const hrc = frameworkPatch.inline_reference_controls?.[0];
		expect(hrc?.description).toBe('a description');
		expect(hrc?.annotation).toBe('an annotation');
		expect(hrc?.csf_function).toBe('govern');
		const hth = frameworkPatch.inline_threats?.[0];
		expect(hth?.description).toBe('threat desc');
		expect(hth?.annotation).toBe('threat ann');
	});
});

describe('inline reference control typical_evidence (pass 2: list support)', () => {
	it('serialize/hydrate preserves typical_evidence as a list', () => {
		const fw = makeFramework({
			inline_reference_controls: [
				{
					id: 'rc-1',
					urn: 'urn:custom:risk:reference_control:fw:c1',
					ref_id: 'C1',
					name: 'C1',
					description: null,
					annotation: null,
					category: 'policy',
					csf_function: null,
					typical_evidence: ['Signed document', 'Review records'],
					translations: null
				}
			],
			inline_threats: []
		});

		const draft = serializeDraft(fw, []);
		const rc = (draft.reference_controls ?? [])[0] as Record<string, unknown>;
		expect(rc.typical_evidence).toEqual(['Signed document', 'Review records']);

		const { frameworkPatch } = hydrateDraft(draft, fw.id);
		expect(frameworkPatch.inline_reference_controls?.[0].typical_evidence).toEqual([
			'Signed document',
			'Review records'
		]);
	});
});

describe('inlineCopyFromCatalogEntry (copy picked existing object)', () => {
	it('clones a reference control entry into a framework-owned inline object', () => {
		const entry = {
			id: 'src-1',
			urn: 'urn:intuitem:risk:function:doc-pol:a.5.1',
			ref_id: 'A.5.1',
			name: 'Policies',
			description: 'desc',
			annotation: 'ann',
			category: 'policy',
			csf_function: 'govern',
			typical_evidence: ['Signed doc', 'Review'],
			translations: { fr: { name: 'Politiques' } },
			referenceable: false
		};
		const copy = inlineCopyFromCatalogEntry(entry, {
			urnType: 'reference_control',
			namespace: 'custom',
			slug: 'fw',
			isControl: true
		});
		expect(copy.urn).toBe('urn:custom:risk:reference_control:fw:a.5.1');
		expect(copy.ref_id).toBe('A.5.1');
		expect(copy.name).toBe('Policies');
		expect(copy.description).toBe('desc');
		expect(copy.annotation).toBe('ann');
		expect(copy.category).toBe('policy');
		expect(copy.csf_function).toBe('govern');
		expect(copy.typical_evidence).toEqual(['Signed doc', 'Review']);
		expect(copy.translations).toEqual({ fr: { name: 'Politiques' } });
	});

	it('omits control-only fields when copying a threat', () => {
		const entry = {
			id: 't',
			urn: 'urn:x:risk:threat:lib:t1',
			ref_id: 'T1',
			name: 'Threat',
			description: 'd',
			referenceable: false
		};
		const copy = inlineCopyFromCatalogEntry(entry, {
			urnType: 'threat',
			namespace: 'custom',
			slug: 'fw',
			isControl: false
		});
		expect(copy.urn).toBe('urn:custom:risk:threat:fw:t1');
		expect(copy.name).toBe('Threat');
		expect(copy.category).toBeUndefined();
		expect(copy.csf_function).toBeUndefined();
		expect(copy.typical_evidence).toBeUndefined();
	});

	it('mints a ref_id when the source has none', () => {
		const entry = { id: 'x', urn: 'urn:x', ref_id: null, name: 'No ref', referenceable: false };
		const copy = inlineCopyFromCatalogEntry(entry, {
			urnType: 'reference_control',
			namespace: 'custom',
			slug: 'fw',
			isControl: true
		});
		expect(copy.ref_id?.startsWith('imported-')).toBe(true);
		expect(copy.urn).toContain(':reference_control:fw:imported-');
	});
});
