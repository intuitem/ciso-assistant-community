import { describe, it, expect } from 'vitest';
import { get } from 'svelte/store';
import {
	slugifyFrameworkName,
	computeRefId,
	generateUrn,
	validateDraft,
	buildTree,
	serializeDraft,
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
		...overrides
	};
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
