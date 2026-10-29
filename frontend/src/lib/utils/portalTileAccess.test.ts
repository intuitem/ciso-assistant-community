import { describe, expect, it } from 'vitest';
import { canUseTile, type TileAccess } from './portalTileAccess';

const access = (codenames: string[], docs: string[] = []): TileAccess => ({
	has: (c) => codenames.includes(c),
	modelName: (m) => ({ incidents: 'incident', 'risk-assessments': 'riskassessment' })[m],
	readableDocuments: new Set(docs)
});

describe('canUseTile', () => {
	it('needs the add permission for create tiles', () => {
		const tile = { kind: 'create', target: { model: 'incidents' } };
		expect(canUseTile(tile, access(['view_incident']))).toBe(false);
		expect(canUseTile(tile, access(['add_incident']))).toBe(true);
	});

	it('needs the view permission for navigate tiles to a model', () => {
		const tile = { kind: 'navigate', target: { model: 'risk-assessments' } };
		expect(canUseTile(tile, access([]))).toBe(false);
		expect(canUseTile(tile, access(['view_riskassessment']))).toBe(true);
	});

	it('keeps plain pages and click-time-checked kinds', () => {
		expect(canUseTile({ kind: 'navigate', target: { model: 'my-assignments' } }, access([]))).toBe(
			true
		);
		expect(canUseTile({ kind: 'quickForm', target: {} }, access([]))).toBe(true);
	});

	it('accepts either document permission for the library', () => {
		const tile = { kind: 'navigate', target: { model: 'documents' } };
		expect(canUseTile(tile, access([]))).toBe(false);
		expect(canUseTile(tile, access(['view_published_documentcontainer']))).toBe(true);
	});

	it('shows a specific document only when the viewer can read it', () => {
		const tile = { kind: 'navigate', target: { model: 'documents', document: 'd1' } };
		expect(canUseTile(tile, access(['view_documentcontainer'], ['d2']))).toBe(false);
		expect(canUseTile(tile, access([], ['d1']))).toBe(true);
	});
});
