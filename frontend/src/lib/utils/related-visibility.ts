const isPlainObject = (value: unknown): value is Record<string, unknown> =>
	typeof value === 'object' && value !== null && !Array.isArray(value);

export const isMaskedPlaceholder = (value: unknown): boolean => {
	if (value === '') return true;
	if (!isPlainObject(value)) return false;
	const keys = Object.keys(value);
	if (keys.length === 0) return true;
	return keys.every((key) => {
		const inner = value[key];
		if (inner === null || inner === undefined || inner === '') return true;
		if (Array.isArray(inner)) return inner.length === 0;
		if (isPlainObject(inner)) return Object.keys(inner).length === 0;
		return false;
	});
};

export const countMasked = (value: unknown): number => {
	if (Array.isArray(value)) {
		return value.reduce((total, item) => total + (isMaskedPlaceholder(item) ? 1 : 0), 0);
	}
	return isMaskedPlaceholder(value) ? 1 : 0;
};
