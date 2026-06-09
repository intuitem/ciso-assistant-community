import { describe, it, expect } from 'vitest';

// table.ts and AutocompleteSelect.svelte can't be imported in this unit-test
// environment because they transitively pull in $app/stores.
// The function is replicated here to document and pin the contract.
type Option = { label: string; value: string | number; translatedLabel?: string };

function prependNullOption(opts: Option[], nullable: boolean): Option[] {
	if (!nullable || opts.some((o) => o.value === '--')) return opts;
	return [{ label: '--', value: '--', translatedLabel: '--' }, ...opts];
}

const baseOpts: Option[] = [
	{ label: 'A', value: 'a', translatedLabel: 'A' },
	{ label: 'B', value: 'b', translatedLabel: 'B' }
];

describe('prependNullOption', () => {
	it('does nothing when nullable is false', () => {
		expect(prependNullOption(baseOpts, false)).toEqual(baseOpts);
	});

	it('prepends a -- option when nullable is true', () => {
		const result = prependNullOption(baseOpts, true);
		expect(result[0]).toEqual({ label: '--', value: '--', translatedLabel: '--' });
		expect(result.slice(1)).toEqual(baseOpts);
	});

	it('does not double-prepend if -- is already present', () => {
		const withNull: Option[] = [{ label: '--', value: '--', translatedLabel: '--' }, ...baseOpts];
		const result = prependNullOption(withNull, true);
		expect(result.filter((o) => o.value === '--')).toHaveLength(1);
		expect(result).toHaveLength(withNull.length);
	});

	it('works on an empty option list', () => {
		const result = prependNullOption([], true);
		expect(result).toHaveLength(1);
		expect(result[0]).toEqual({ label: '--', value: '--', translatedLabel: '--' });
	});

	it('preserves the rest of the list unchanged', () => {
		const result = prependNullOption(baseOpts, true);
		expect(result).toHaveLength(baseOpts.length + 1);
		expect(result.slice(1)).toStrictEqual(baseOpts);
	});
});
