import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { modelSchema } from '$lib/utils/schemas';
import { defaultWriteFormAction, defaultDeleteFormAction } from '$lib/utils/actions';
import { superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import { z } from 'zod';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, url }) => {
	const selectedFolderId = url.searchParams.get('folder') ?? '';

	// Defensive parsing: if the API returns a non-2xx (401/403/500/etc.), the body
	// is an error object, not a list. Guard against that so {#each data.folders}
	// doesn't iterate over object keys or throw.
	const toList = (data: any): any[] =>
		Array.isArray(data) ? data : Array.isArray(data?.results) ? data.results : [];

	const foldersRes = await fetch(`${BASE_API_URL}/folders/?content_type=DO&content_type=GL`);
	const folders = foldersRes.ok ? toList(await foldersRes.json()) : [];

	let assets: any[] = [];
	if (selectedFolderId) {
		const assetsRes = await fetch(
			`${BASE_API_URL}/assets/?folder=${encodeURIComponent(selectedFolderId)}`
		);
		assets = assetsRes.ok ? toList(await assetsRes.json()) : [];
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
