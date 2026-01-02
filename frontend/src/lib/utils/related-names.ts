import { browser } from '$app/environment';

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const cache = new Map<string, Record<string, string>>();

const chunk = (items: string[], size: number) => {
	const chunks: string[][] = [];
	for (let i = 0; i < items.length; i += size) {
		chunks.push(items.slice(i, i + size));
	}
	return chunks;
};

export const isUuid = (value: string): boolean => UUID_REGEX.test(value);

export const fetchNames = async (
	urlModel: string,
	ids: string[]
): Promise<Record<string, string>> => {
	if (!browser || !urlModel || ids.length === 0) return {};
	const uniqueIds = Array.from(new Set(ids)).filter(isUuid);
	if (uniqueIds.length === 0) return {};

	const existing = cache.get(urlModel) ?? {};
	const missing = uniqueIds.filter((id) => !existing[id]);
	if (missing.length === 0) return existing;

	let updated = { ...existing };
	for (const batch of chunk(missing, 100)) {
		const params = new URLSearchParams();
		batch.forEach((id) => params.append('id[]', id));
		const response = await fetch(`/${urlModel}/names?${params.toString()}`);
		if (!response.ok) continue;
		const data = await response.json();
		if (data && typeof data === 'object') {
			updated = { ...updated, ...data };
		}
	}

	cache.set(urlModel, updated);
	return updated;
};
