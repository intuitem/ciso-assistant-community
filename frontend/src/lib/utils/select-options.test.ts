import { describe, it, expect, vi } from 'vitest';
import { URL_MODEL_MAP } from '$lib/utils/crud';
import { BASE_API_URL } from '$lib/utils/constants';
import { ensureSelectOptions } from '$lib/utils/select-options';
import { GET } from '../../routes/(app)/(internal)/select-options/+server';

const PARENT = '3af191d3-347d-48c9-949b-126280aa33d0';

const declared = Object.entries(URL_MODEL_MAP)
	.filter(([, entry]: [string, any]) => entry.selectFields?.length)
	.flatMap(([urlModel, entry]: [string, any]) =>
		entry.selectFields.map((f: any) => ({ urlModel, field: f.field, nested: !!f.formNestedField }))
	);

async function clientUrl(urlModel: string, field: string, nested: boolean) {
	let asked = '';
	vi.stubGlobal('fetch', async (url: string) => {
		asked = String(url);
		return { ok: true, json: async () => ({}) };
	});
	await ensureSelectOptions(
		{ urlModel, selectFields: [{ field, ...(nested ? { formNestedField: 'parent' } : {}) }] },
		nested ? { parent: PARENT } : {}
	);
	vi.unstubAllGlobals();
	return asked;
}

describe('every declared select field is reachable', () => {
	it(`covers ${declared.length} fields across ${new Set(declared.map((d) => d.urlModel)).size} models`, async () => {
		const unreachable: string[] = [];

		for (const { urlModel, field, nested } of declared) {
			const asked = await clientUrl(urlModel, field, nested);
			const backend = vi.fn(async () => ({ ok: true, json: async () => ({}) }));
			try {
				// The client's own URL, handed to the route that must serve it.
				await GET({ fetch: backend, url: new URL(`http://x${asked}`) } as any);
			} catch (e: any) {
				unreachable.push(`${urlModel}.${field} -> ${e?.status ?? e}`);
				continue;
			}
			const called = String(backend.mock.calls[0]?.[0] ?? '');
			if (!called.startsWith(BASE_API_URL) || !called.endsWith(`/${field}/`)) {
				unreachable.push(`${urlModel}.${field} -> built '${called}'`);
			}
		}

		expect(unreachable).toEqual([]);
	});
});
