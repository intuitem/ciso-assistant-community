import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { fetchAllPages } from '$lib/utils/pagination';
import { modelSchema } from '$lib/utils/schemas';
import { defaultWriteFormAction, defaultDeleteFormAction } from '$lib/utils/actions';
import { superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import { z } from 'zod';
import type { Actions, PageServerLoad } from './$types';

const BATCH = 40;

const idOf = (ref: any): string => (typeof ref === 'object' && ref !== null ? ref.id : ref);

function chunks<T>(items: T[], size: number): T[][] {
	const out: T[][] = [];
	for (let i = 0; i < items.length; i += size) out.push(items.slice(i, i + size));
	return out;
}

async function loadExternalNeighbours(fetch: typeof globalThis.fetch, assets: any[]) {
	const localIds = new Set(assets.map((a) => a.id));
	const externalParentIds = new Set<string>();
	for (const a of assets) {
		for (const p of a.parent_assets ?? []) {
			const pid = idOf(p);
			if (!localIds.has(pid)) externalParentIds.add(pid);
		}
	}

	const byId = new Map<string, any>();

	for (const batch of chunks([...externalParentIds], BATCH)) {
		const rows = await fetchAllPages(fetch, `${BASE_API_URL}/assets/?id=${batch.join(',')}`).catch(
			() => []
		);
		for (const r of rows) byId.set(r.id, r);
	}

	for (const batch of chunks([...localIds], BATCH)) {
		const qs = batch.map((id) => `parent_assets=${id}`).join('&');
		const rows = await fetchAllPages(fetch, `${BASE_API_URL}/assets/?${qs}`).catch(() => []);
		for (const r of rows) if (!localIds.has(r.id)) byId.set(r.id, r);
	}

	return {
		externalAssets: [...byId.values()],
		hiddenAssetIds: [...externalParentIds].filter((id) => !byId.has(id))
	};
}

export const load: PageServerLoad = async ({ fetch, url }) => {
	const selectedFolderId = url.searchParams.get('folder') ?? '';

	// Defensive: if the API returns a non-2xx (401/403/500/etc.), degrade to an
	// empty list so {#each data.folders} doesn't iterate over object keys or throw.
	const folders = await fetchAllPages(
		fetch,
		`${BASE_API_URL}/folders/?content_type=DO&content_type=GL`
	).catch(() => []);

	let assets: any[] = [];
	let externalAssets: any[] = [];
	let hiddenAssetIds: string[] = [];
	if (selectedFolderId) {
		assets = await fetchAllPages(
			fetch,
			`${BASE_API_URL}/assets/?folder=${encodeURIComponent(selectedFolderId)}`
		).catch(() => []);
		({ externalAssets, hiddenAssetIds } = await loadExternalNeighbours(fetch, assets));
	}

	const assetModelInfo = getModelInfo('assets');
	const assetSchema = modelSchema('assets');
	const assetInitialData: Record<string, any> = {};
	if (selectedFolderId) {
		assetInitialData.folder = selectedFolderId;
	}
	const assetCreateForm = await superValidate(assetInitialData, zod(assetSchema), {
		errors: false
	});

	// Delete form for the DeleteConfirmModal (validates `id` UUID).
	const assetDeleteForm = await superValidate(zod(z.object({ id: z.string().uuid() })));

	const typeRes = await fetch(`${BASE_API_URL}/assets/type/`);
	const typeData = typeRes.ok ? await typeRes.json() : {};
	const typeOptions = Object.entries(typeData).map(([key, value]) => ({
		label: value as string,
		value: key
	}));

	return {
		folders,
		assets,
		externalAssets,
		hiddenAssetIds,
		selectedFolderId,
		assetDeleteForm,
		assetModel: {
			...assetModelInfo,
			urlModel: 'assets',
			createForm: assetCreateForm,
			selectOptions: { type: typeOptions }
		}
	};
};

export const actions: Actions = {
	create: async (event) => {
		return defaultWriteFormAction({
			event,
			urlModel: 'assets',
			action: 'create',
			redirectToWrittenObject: false
		});
	},
	delete: async (event) => {
		return defaultDeleteFormAction({ event, urlModel: 'assets' });
	}
};
