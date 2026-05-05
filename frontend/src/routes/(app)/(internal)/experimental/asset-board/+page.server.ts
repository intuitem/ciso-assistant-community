import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { modelSchema } from '$lib/utils/schemas';
import { defaultWriteFormAction } from '$lib/utils/actions';
import { superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, url }) => {
	const selectedFolderId = url.searchParams.get('folder') ?? '';

	const foldersRes = await fetch(`${BASE_API_URL}/folders/?content_type=DO&content_type=GL`);
	const foldersData = await foldersRes.json();
	const folders = foldersData.results || foldersData;

	let assets: any[] = [];
	if (selectedFolderId) {
		const assetsRes = await fetch(
			`${BASE_API_URL}/assets/?folder=${encodeURIComponent(selectedFolderId)}`
		);
		const assetsData = await assetsRes.json();
		assets = assetsData.results || assetsData;
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
	}
};
