import { listViewFields } from '$lib/utils/table';
import { type TableSource } from '@skeletonlabs/skeleton-svelte';
import { urlParamModelVerboseName, urlParamModelDescriptionKey } from '$lib/utils/crud';
import { redirect } from '@sveltejs/kit';
import type { LayoutServerLoad } from './$types';

const URLModel = 'service-accounts';

export const load: LayoutServerLoad = async ({ locals }) => {
	if (!locals?.featureflags?.service_accounts) {
		redirect(302, '/analytics');
	}
	const base = listViewFields[URLModel];
	const headData: Record<string, string> = base.body.reduce((obj, key, index) => {
		obj[key] = base.head[index];
		return obj;
	}, {});

	const table: TableSource = {
		head: headData,
		body: [],
		meta: []
	};

	return {
		table,
		modelVerboseName: urlParamModelVerboseName(URLModel),
		modelDescriptionKey: urlParamModelDescriptionKey(URLModel)
	};
};
