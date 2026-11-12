import { afterEach, describe, expect, it, vi } from 'vitest';
import {
	hasSelection,
	readLinkType,
	readSelection,
	recallSelection,
	rememberSelection,
	selectionParams,
	selectionToParams,
	selectionListFilters,
	withParams
} from './scenarioSelection';

const url = (query: string) => new URLSearchParams(query);

describe('scenario selection params', () => {
	it('keeps only the prefixed, non-empty params', () => {
		const params = selectionParams(
			url('scenario__treatment=mitigate&status=active&scenario__owner=&link_type=all')
		);
		expect(params.toString()).toBe('scenario__treatment=mitigate');
		expect(hasSelection(url('status=active'))).toBe(false);
	});

	it('reads and writes repeated values', () => {
		const values = readSelection(url('scenario__current_level=2&scenario__current_level=3'));
		expect(values).toEqual({ current_level: ['2', '3'] });
		expect(selectionToParams(values).toString()).toBe(
			'scenario__current_level=2&scenario__current_level=3'
		);
	});

	it('turns the resolved filters into scenario list params', () => {
		expect(
			selectionListFilters({ within_tolerance: ['NO'], current_level: ['2', '3'] }).toString()
		).toBe('within_tolerance=NO&current_level=2&current_level=3');
		expect(selectionListFilters(undefined).toString()).toBe('');
	});

	it('defaults the action plan to additional measures', () => {
		expect(readLinkType(url(''))).toBe('additional');
		expect(readLinkType(url('link_type=all'))).toBe('all');
		expect(readLinkType(url('link_type=bogus'))).toBe('additional');
	});

	it('appends params only when there are some', () => {
		expect(withParams('/a', url(''))).toBe('/a');
		expect(withParams('/a', url('x=1'))).toBe('/a?x=1');
		expect(withParams('/a?y=2', url('x=1'))).toBe('/a?y=2&x=1');
	});
});

describe('remembered selection', () => {
	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it('round-trips through storage per assessment', () => {
		const store = new Map<string, string>();
		vi.stubGlobal('localStorage', {
			getItem: (k: string) => store.get(k) ?? null,
			setItem: (k: string, v: string) => store.set(k, v),
			removeItem: (k: string) => store.delete(k)
		});
		rememberSelection('ra-1', url('scenario__treatment=accept&status=x'));
		expect(recallSelection('ra-1')?.toString()).toBe('scenario__treatment=accept');
		expect(recallSelection('ra-2')).toBeNull();

		rememberSelection('ra-1', url(''));
		expect(recallSelection('ra-1')).toBeNull();
	});

	it('works without storage', () => {
		vi.stubGlobal('localStorage', {
			getItem: () => {
				throw new Error('blocked');
			},
			setItem: () => {
				throw new Error('blocked');
			},
			removeItem: () => {
				throw new Error('blocked');
			}
		});
		expect(() => rememberSelection('ra-1', url('scenario__treatment=accept'))).not.toThrow();
		expect(recallSelection('ra-1')).toBeNull();
	});
});
