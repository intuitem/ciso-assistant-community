import { describe, it, expect } from 'vitest';
import {
	validateDraft,
	type Framework,
	type BuilderSection,
	type RequirementNode
} from './builder-state';

/** Create a minimal framework for testing */
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
	};
}

/** Create a minimal requirement node for testing */
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

/** Create a section with optional requirements */
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
				{
					node: makeNode({ name: 'Valid name' }),
					questions: [],
					children: [],
					depth: 0
				}
			])
		];

		const errors = validateDraft(fw, sections);
		expect(errors).toHaveLength(0);
	});

	it('rejects name exceeding 200 characters', () => {
		const fw = makeFramework();
		const longName = 'A'.repeat(201);
		const sections = [
			makeSection({}, [
				{
					node: makeNode({ name: longName }),
					questions: [],
					children: [],
					depth: 0
				}
			])
		];

		const errors = validateDraft(fw, sections);
		expect(errors.length).toBeGreaterThan(0);
		const nodeError = errors.find((e) => e.key === 'node-node-1');
		expect(nodeError).toBeDefined();
		expect(nodeError!.message).toContain('Name exceeds 200 characters');
		expect(nodeError!.message).toContain('201/200');
	});

	it('rejects ref_id exceeding 100 characters', () => {
		const fw = makeFramework();
		const longRefId = 'R'.repeat(101);
		const sections = [
			makeSection({}, [
				{
					node: makeNode({ ref_id: longRefId }),
					questions: [],
					children: [],
					depth: 0
				}
			])
		];

		const errors = validateDraft(fw, sections);
		expect(errors.length).toBeGreaterThan(0);
		const nodeError = errors.find((e) => e.key === 'node-node-1');
		expect(nodeError).toBeDefined();
		expect(nodeError!.message).toContain('ref_id is 101 characters');
	});

	it('rejects URN exceeding 255 characters', () => {
		const fw = makeFramework();
		const longUrn = 'urn:' + 'x'.repeat(252);
		const sections = [
			makeSection({}, [
				{
					node: makeNode({ urn: longUrn }),
					questions: [],
					children: [],
					depth: 0
				}
			])
		];

		const errors = validateDraft(fw, sections);
		expect(errors.length).toBeGreaterThan(0);
		const nodeError = errors.find((e) => e.key === 'node-node-1');
		expect(nodeError).toBeDefined();
		expect(nodeError!.message).toContain('URN is 256 characters');
	});

	it('rejects empty framework name', () => {
		const fw = makeFramework({ name: '' });
		const sections = [makeSection()];

		const errors = validateDraft(fw, sections);
		expect(errors.length).toBeGreaterThan(0);
		const publishError = errors.find((e) => e.key === 'publish');
		expect(publishError).toBeDefined();
		expect(publishError!.message).toBe('Framework name is required.');
	});
});
