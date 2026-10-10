import { readdirSync, readFileSync } from 'node:fs';
import { join, relative, resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import {
	canOpenObjectPage,
	canOpenPage,
	THIRD_PARTY_PAGES,
	thirdPartyMayOpen,
	withoutGroups
} from './route-access';

const SRC = resolve(process.cwd(), 'src');
const ROUTES = join(SRC, 'routes');

function pageRouteIds(): string[] {
	const ids: string[] = [];
	const walk = (dir: string) => {
		const entries = readdirSync(dir, { withFileTypes: true });
		if (entries.some((e) => /^\+page(\.server)?\.(svelte|ts)$/.test(e.name))) {
			ids.push('/' + relative(ROUTES, dir));
		}
		for (const e of entries) if (e.isDirectory()) walk(join(dir, e.name));
	};
	walk(ROUTES);
	return ids.map((id) => (id === '/' ? id : id.replace(/\/$/, '')));
}

function sourceFiles(dir: string): string[] {
	return readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
		const path = join(dir, e.name);
		if (e.isDirectory()) return e.name === 'paraglide' ? [] : sourceFiles(path);
		return /\.(svelte|ts)$/.test(e.name) && !e.name.includes('.test.') ? [path] : [];
	});
}

const pages = pageRouteIds();
const appPages = pages.filter((id) => id === '/(app)' || id.startsWith('/(app)/'));

describe('third-party page access', () => {
	it('finds the pages to check', () => {
		expect(appPages.length).toBeGreaterThan(100);
	});

	it('lets third parties open the listed pages and no other app page', () => {
		const opened = appPages.filter(thirdPartyMayOpen).map(withoutGroups).sort();
		expect(opened).toEqual([...THIRD_PARTY_PAGES].sort());
	});

	it('does not restrict pages outside the app', () => {
		const outside = pages.filter((id) => !appPages.includes(id));
		expect(outside.length).toBeGreaterThan(0);
		expect(outside.filter((id) => !thirdPartyMayOpen(id))).toEqual([]);
	});
});

describe('links follow the same policy', () => {
	const thirdParty = { is_third_party: true };
	const internal = { is_third_party: false };

	it('lets internal users open every page', () => {
		expect(appPages.filter((id) => !canOpenPage(internal, id))).toEqual([]);
	});

	it('opens an object page only when its own detail route is listed', () => {
		expect(canOpenObjectPage(thirdParty, 'evidences')).toBe(true);
		expect(canOpenObjectPage(thirdParty, 'applied-controls')).toBe(false);
		expect(canOpenObjectPage(thirdParty, 'threats')).toBe(false);
		expect(canOpenObjectPage(internal, 'threats')).toBe(true);
	});

	// A mistyped or renamed route id would quietly hide the link from third parties. Reads
	// every source file, which can outlast the default timeout when the whole suite runs.
	it('names only existing pages in canOpenPage calls', { timeout: 30_000 }, () => {
		const ids = sourceFiles(SRC).flatMap((file) =>
			[...readFileSync(file, 'utf8').matchAll(/canOpenPage\(\s*[^,()]+,\s*'([^']+)'/g)].map(
				(match) => match[1]
			)
		);
		expect(ids.length).toBeGreaterThan(0);
		expect(ids.filter((id) => !pages.includes(id))).toEqual([]);
	});
});
