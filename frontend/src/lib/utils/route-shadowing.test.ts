import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { URL_MODEL_MAP } from './crud';

const ROUTES = resolve(process.cwd(), 'src/routes/(app)');

const addExistingModels = Object.entries(URL_MODEL_MAP)
	.filter(([, entry]) => entry.reverseForeignKeyFields?.some((f) => f.addExisting))
	.map(([urlModel]) => urlModel);

describe('addExisting models expose PATCH at /<urlModel>/<id>', () => {
	it('finds the models to check', () => {
		expect(addExistingModels.length).toBeGreaterThan(0);
	});

	it.each(addExistingModels)('%s', (urlModel) => {
		for (const group of ['(internal)', '(third-party)']) {
			const dir = `${ROUTES}/${group}/${urlModel}/[id=uuid]`;
			if (!existsSync(dir)) continue;
			const server = `${dir}/+server.ts`;
			expect(existsSync(server), `${group}/${urlModel} shadows the generic route`).toBe(true);
			expect(readFileSync(server, 'utf8')).toMatch(/export const PATCH/);
		}
	});
});
