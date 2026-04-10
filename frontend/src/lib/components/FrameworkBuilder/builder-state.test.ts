import { describe, it, expect } from 'vitest';
import {
	slugifyFrameworkName,
	computeRefId,
	generateUrn,
	validateDraft,
	type Framework,
	type BuilderSection,
	type RequirementNode
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
	requirements: BuilderSection['requirements'] = []
): BuilderSection {
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
		requirements,
		collapsed: false
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
