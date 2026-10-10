import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { match as isInternalModel } from '../../params/internal_urlmodels';
import { match as isThirdPartyModel } from '../../params/thirdparty_urlmodels';
import { URL_MODEL_MAP } from './crud';
import { URL_MODEL } from './types';

const ROUTES = resolve(process.cwd(), 'src/routes/(app)');

// When two generic routes match the same URL, SvelteKit picks between them by comparing
// route ids, so moving or renaming a folder would silently swap the page served.
describe('each URL model has exactly one generic list, detail and edit page', () => {
	it.each(URL_MODEL)('%s', (urlModel) => {
		expect([isInternalModel(urlModel), isThirdPartyModel(urlModel)].filter(Boolean)).toHaveLength(
			1
		);
	});
});

const addExistingModels = Object.entries(URL_MODEL_MAP)
	.filter(([, entry]) => entry.reverseForeignKeyFields?.some((f) => f.addExisting))
	.map(([urlModel]) => urlModel);

describe('addExisting models expose PATCH at /<urlModel>/<id>', () => {
	it('finds the models to check', () => {
		expect(addExistingModels.length).toBeGreaterThan(0);
	});

	it.each(addExistingModels)('%s', (urlModel) => {
		const dir = `${ROUTES}/${urlModel}/[id=uuid]`;
		if (!existsSync(dir)) return;
		const server = `${dir}/+server.ts`;
		expect(existsSync(server), `${urlModel} shadows the generic route`).toBe(true);
		expect(readFileSync(server, 'utf8')).toMatch(/export const PATCH/);
	});
});
