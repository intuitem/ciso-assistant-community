interface SearchableOption {
	label: string;
	translatedLabel?: string;
	detail?: string;
	groupLabels?: string[];
}

/**
 * Return the options whose displayed label (the translation, or the raw label
 * when there is none), detail (such as a permission's technical name) or group
 * heading (such as the permission's module or model) contains `query`, ignoring
 * case and surrounding spaces. A blank query returns every option.
 */
export function filterOptions<T extends SearchableOption>(options: T[], query: string): T[] {
	const needle = query.trim().toLocaleLowerCase();
	if (!needle) return options;
	return options.filter((option) =>
		[option.translatedLabel ?? option.label, option.detail, ...(option.groupLabels ?? [])].some(
			(text) => text?.toLocaleLowerCase().includes(needle)
		)
	);
}
