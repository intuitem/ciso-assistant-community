import { base } from '$app/paths';
import type { PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';
import { getModelInfo } from '$lib/utils/crud';
import { safeTranslate } from '$lib/utils/i18n';
import { urlModel } from '$lib/stores';
import { get } from 'svelte/store';

const MODEL = 'data-assets';

export const load: PageServerLoad = async ({ url, fetch, depends }) => {
	depends('app:data-assets');

	const urlModelStore = get(urlModel);
	const model = getModelInfo(MODEL);

	if (!model) {
		throw error(404, 'Model not found');
	}

	const queryParams = url.searchParams;

	try {
		const response = await fetch(`${base}/api/privacy/data-assets/?${queryParams.toString()}`);
		if (!response.ok) {
			throw error(response.status, 'Failed to load data assets');
		}

		const data = await response.json();

		return {
			title: safeTranslate(model.verbose_name_plural || model.verbose_name),
			dataAssets: data.results || [],
			count: data.count || 0,
			next: data.next,
			previous: data.previous,
			model,
			queryParams: Object.fromEntries(queryParams.entries())
		};
	} catch (err) {
		console.error('Error loading data assets:', err);
		throw error(500, 'Failed to load data assets');
	}
};
