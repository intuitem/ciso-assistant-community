import { fetchAllByIds } from './pagination';

const isPlainObject = (value: unknown): value is Record<string, unknown> =>
	typeof value === 'object' && value !== null && !Array.isArray(value);

export const isMaskedPlaceholder = (value: unknown): boolean => {
	if (!isPlainObject(value)) return false;
	const keys = Object.keys(value);
	if (keys.length === 0) return true;
	return keys.every((key) => {
		const inner = value[key];
		if (inner === null || inner === undefined) return true;
		if (Array.isArray(inner)) return inner.every((item) => isMaskedPlaceholder(item));
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

/**
 * The ids among `ids` that the user cannot see, looked up on `endpoint` without
 * its query string: a picker's filters must not pass an object it merely leaves
 * out for a hidden one. When the lookup fails, all of them are reported: a link
 * nobody could check is kept, not dropped on the next save.
 */
export async function findHiddenIds(
	fetchFn: typeof fetch,
	endpoint: string,
	ids: string[]
): Promise<string[]> {
	if (ids.length === 0) return [];
	try {
		const visible = await fetchAllByIds(fetchFn, `/${endpoint.split('?')[0]}`, ids);
		const seen = new Set(visible.map((row) => String(row.id)));
		return ids.filter((id) => !seen.has(id));
	} catch {
		return ids;
	}
}
