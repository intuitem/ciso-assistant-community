import { describe, it, expect, beforeEach } from 'vitest';

import {
	hrefPathname,
	isSiblingPath,
	syncBreadcrumbsToCurrentUrl,
	loadFromSession,
	type Breadcrumb
} from './breadcrumbs';

const home: Breadcrumb = { label: 'Home', href: '/' };
const crumb = (label: string, href: string): Breadcrumb => ({ label, href });

describe('hrefPathname', () => {
	it('returns undefined for undefined', () => {
		expect(hrefPathname(undefined)).toBeUndefined();
	});

	it('returns full string when no query', () => {
		expect(hrefPathname('/foo/bar')).toBe('/foo/bar');
	});

	it('strips query string', () => {
		expect(hrefPathname('/foo?bar=1&baz=2')).toBe('/foo');
	});

	it('handles root', () => {
		expect(hrefPathname('/')).toBe('/');
	});
});

describe('isSiblingPath', () => {
	it('returns false when first arg is undefined', () => {
		expect(isSiblingPath(undefined, '/foo')).toBe(false);
	});

	it('returns false on different depth', () => {
		expect(isSiblingPath('/foo', '/foo/bar')).toBe(false);
		expect(isSiblingPath('/foo/bar', '/foo')).toBe(false);
	});

	it('returns false on different first segment', () => {
		expect(isSiblingPath('/foo/123', '/bar/123')).toBe(false);
	});

	it('returns true on same depth + same first segment', () => {
		expect(isSiblingPath('/requirement-assessments/abc', '/requirement-assessments/def')).toBe(
			true
		);
		expect(isSiblingPath('/folders/a', '/folders/b')).toBe(true);
	});

	it('returns false when either path is empty', () => {
		expect(isSiblingPath('/', '/foo')).toBe(false);
		expect(isSiblingPath('', '/foo')).toBe(false);
	});
});

describe('syncBreadcrumbsToCurrentUrl', () => {
	it('trims trail and updates query when current path matches an intermediate crumb', () => {
		const trail = [home, crumb('Folders', '/folders'), crumb('Folder A', '/folders/a')];
		const next = syncBreadcrumbsToCurrentUrl(trail, '/folders', '/folders?q=x', 'fallback', false);
		expect(next).toEqual([home, { label: 'Folders', href: '/folders?q=x' }]);
	});

	it('updates query on the last crumb when current path equals it', () => {
		const trail = [home, crumb('Folders', '/folders')];
		const next = syncBreadcrumbsToCurrentUrl(trail, '/folders', '/folders?q=y', 'fallback', false);
		expect(next).toEqual([home, { label: 'Folders', href: '/folders?q=y' }]);
	});

	it('resets trail to [home, current] on fresh load with no match', () => {
		const trail = [home, crumb('Stale', '/old')];
		const next = syncBreadcrumbsToCurrentUrl(trail, '/new', '/new?x=1', 'New', true);
		expect(next).toEqual([home, { label: 'New', href: '/new?x=1' }]);
	});

	it('replaces last crumb on sibling navigation (same depth + first segment)', () => {
		const trail = [home, crumb('Folder list', '/folders'), crumb('A', '/folders/a')];
		const next = syncBreadcrumbsToCurrentUrl(trail, '/folders/b', '/folders/b', 'B', false);
		expect(next).toEqual([
			home,
			crumb('Folder list', '/folders'),
			{ label: 'B', href: '/folders/b' }
		]);
	});

	it('appends on non-sibling navigation when not a fresh load', () => {
		const trail = [home, crumb('Folders', '/folders')];
		const next = syncBreadcrumbsToCurrentUrl(
			trail,
			'/risk-scenarios',
			'/risk-scenarios',
			'RS',
			false
		);
		expect(next).toEqual([
			home,
			crumb('Folders', '/folders'),
			{ label: 'RS', href: '/risk-scenarios' }
		]);
	});

	it('does not replace when last crumb has no href (no false sibling match)', () => {
		const trail = [home, { label: 'Detached' } as Breadcrumb];
		const next = syncBreadcrumbsToCurrentUrl(trail, '/foo', '/foo', 'Foo', false);
		expect(next).toEqual([home, { label: 'Detached' }, { label: 'Foo', href: '/foo' }]);
	});

	it('match wins over sibling: trims even when last crumb is a sibling of current', () => {
		// trail ends with a deeper crumb that happens to share first segment with current
		const trail = [home, crumb('Folders', '/folders'), crumb('A', '/folders/a')];
		// current path matches the intermediate crumb -> trim, do not sibling-replace
		const next = syncBreadcrumbsToCurrentUrl(trail, '/folders', '/folders?q=1', 'fallback', false);
		expect(next).toEqual([home, { label: 'Folders', href: '/folders?q=1' }]);
	});
});

describe('loadFromSession', () => {
	beforeEach(() => {
		sessionStorage.clear();
	});

	it('returns initial value when storage is empty', () => {
		const init = [home];
		expect(loadFromSession(init)).toBe(init);
	});

	it('returns initial value when storage contains invalid JSON', () => {
		sessionStorage.setItem('ciso:breadcrumbs', '{not json');
		const init = [home];
		expect(loadFromSession(init)).toBe(init);
	});

	it('returns initial value when stored value is not an array', () => {
		sessionStorage.setItem('ciso:breadcrumbs', JSON.stringify({ label: 'oops' }));
		const init = [home];
		expect(loadFromSession(init)).toBe(init);
	});

	it('hydrates valid crumbs and prepends live home', () => {
		sessionStorage.setItem(
			'ciso:breadcrumbs',
			JSON.stringify([
				{ label: 'StaleHome', href: '/' },
				{ label: 'Folders', href: '/folders' },
				{ label: 'A', href: '/folders/a' }
			])
		);
		const result = loadFromSession([home]);
		expect(result).toHaveLength(3);
		expect(result[0].label).toBe('Home'); // live home replaces stale
		expect(result[1]).toEqual({ label: 'Folders', href: '/folders' });
		expect(result[2]).toEqual({ label: 'A', href: '/folders/a' });
	});

	it('drops entries that fail shape validation', () => {
		sessionStorage.setItem(
			'ciso:breadcrumbs',
			JSON.stringify([
				{ label: 'home', href: '/' },
				{ label: 'Valid', href: '/foo' },
				{ href: '/missing-label' }, // missing label
				{ label: 42, href: '/wrong-type' }, // non-string label
				{ label: 'BadHref', href: 123 }, // non-string href
				null, // null entry
				{ label: 'Good', href: '/good' }
			])
		);
		const result = loadFromSession([home]);
		expect(result).toHaveLength(3);
		expect(result[0].label).toBe('Home');
		expect(result[1]).toEqual({ label: 'Valid', href: '/foo' });
		expect(result[2]).toEqual({ label: 'Good', href: '/good' });
	});

	it('caps hydrated tail to BREADCRUMBS_MAX_DEPTH (5)', () => {
		const long = [{ label: 'home', href: '/' }];
		for (let i = 0; i < 10; i++) long.push({ label: `c${i}`, href: `/c/${i}` });
		sessionStorage.setItem('ciso:breadcrumbs', JSON.stringify(long));
		const result = loadFromSession([home]);
		expect(result).toHaveLength(6); // home + 5 tail
	});
});
