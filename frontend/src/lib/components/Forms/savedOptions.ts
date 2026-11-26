export interface SelectOption {
	value: string | number;
	label: string;
}

/**
 * Return `options` plus an option for each saved value missing from them.
 *
 * A picker clears a value that matches none of its options, so a saved table
 * or mapping the remote metadata no longer lists (a legacy name, incomplete
 * metadata, a failed lookup) would be wiped on load and lost on save. Listing
 * it as an extra option keeps it selected.
 */
export function withSavedOptions<T extends SelectOption>(
	options: T[],
	savedValues: unknown[],
	label: (value: string) => string
): (T | SelectOption)[] {
	const known = new Set(options.map((option) => String(option.value)));
	const missing = new Set(
		savedValues
			.filter((value) => value !== undefined && value !== null && value !== '')
			.map(String)
			.filter((value) => !known.has(value))
	);
	return [...options, ...[...missing].map((value) => ({ value, label: label(value) }))];
}
