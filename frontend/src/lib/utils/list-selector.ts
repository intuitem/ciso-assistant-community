interface SearchableOption {
	label: string;
	translatedLabel?: string;
	detail?: string;
}

/**
 * Return the options whose displayed label (the translation, or the raw label
 * when there is none) or detail (such as a permission's technical name) contains
 * `query`, ignoring case and surrounding spaces. A blank query returns every option.
 */
export function filterOptions<T extends SearchableOption>(options: T[], query: string): T[] {
	const needle = query.trim().toLowerCase();
	if (!needle) return options;
	return options.filter((option) =>
		[option.translatedLabel ?? option.label, option.detail].some((text) =>
			text?.toLowerCase().includes(needle)
		)
	);
}
