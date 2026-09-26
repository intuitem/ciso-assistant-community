import { describe, expect, it } from 'vitest';
import { getPreset, scaleLevels, seedLevels, type ScoreLevel } from './score-scales';

const frameworkLevels: ScoreLevel[] = [
	{
		score: 1,
		name: 'Initial',
		description: 'Standard process does not exist.',
		description_doc: 'No process documentation.',
		translations: { fr: { name: 'Initial', description: 'Pas de processus.' } }
	},
	{ score: 2, name: 'Repeatable', description: 'Some process.' }
];

describe('seedLevels', () => {
	it('keeps descriptions when seeding a custom scale from framework levels', () => {
		const seeded = seedLevels(frameworkLevels, undefined, 1, 2, ['en']);
		expect(seeded[0]).toMatchObject({
			score: 1,
			name: 'Initial',
			description: 'Standard process does not exist.',
			description_doc: 'No process documentation.'
		});
		expect(seeded[0].translations?.fr).toEqual({
			name: 'Initial',
			description: 'Pas de processus.'
		});
		expect(seeded[1].description).toBe('Some process.');
	});

	it('does not mutate the source levels', () => {
		const source = structuredClone(frameworkLevels);
		seedLevels(source, undefined, 1, 2, ['en', 'de']);
		expect(source).toEqual(frameworkLevels);
	});

	it('drops preset tags so a custom scale never resolves catalog labels', () => {
		const tagged: ScoreLevel[] = [{ score: 0, preset: '0-5', translations: {} }];
		const [level] = seedLevels(tagged, getPreset('0-5'), 0, 5, ['en']);
		expect(level).not.toHaveProperty('preset');
		expect(level.name).toBeTruthy();
	});

	it('accepts proxied levels, as handed over by Svelte state', () => {
		const proxied = frameworkLevels.map((l) => new Proxy(structuredClone(l), {}));
		const seeded = seedLevels(new Proxy(proxied, {}), undefined, 1, 2, ['en']);
		expect(seeded[0].description).toBe('Standard process does not exist.');
		expect(() => structuredClone(seeded)).not.toThrow();
	});

	it('fills every score of the range', () => {
		expect(seedLevels([], undefined, 1, 4, ['en']).map((l) => l.score)).toEqual([1, 2, 3, 4]);
	});

	it('returns no levels for ranges too wide to label', () => {
		expect(seedLevels(frameworkLevels, undefined, 0, 100, ['en'])).toEqual([]);
	});
});

describe('scaleLevels', () => {
	it('accepts bare lists and the wrapped {scale} form', () => {
		expect(scaleLevels(frameworkLevels)).toBe(frameworkLevels);
		expect(scaleLevels({ scale: frameworkLevels })).toBe(frameworkLevels);
		expect(scaleLevels(null)).toEqual([]);
		expect(scaleLevels({ alternatives: {} })).toEqual([]);
	});
});
