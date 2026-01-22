import { base } from '$app/paths';
import type { PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';
import { getModelInfo } from '$lib/utils/crud';
import { safeTranslate } from '$lib/utils/i18n';

const MODEL = 'consent-records';

export const load: PageServerLoad = async ({ url, fetch, depends }) => {
	depends('app:consent-records');

	const model = getModelInfo(MODEL);

	if (!model) {
		throw error(404, 'Model not found');
	}

	const queryParams = url.searchParams;

	try {
		const response = await fetch(`${base}/api/privacy/consent-records/?${queryParams.toString()}`);
		if (!response.ok) {
			throw error(response.status, 'Failed to load consent records');
		}

		const data = await response.json();

		return {
			title: safeTranslate(model.verbose_name_plural || model.verbose_name),
			consentRecords: data.results || [],
			count: data.count || 0,
			next: data.next,
			previous: data.previous,
			model,
			queryParams: Object.fromEntries(queryParams.entries())
		};
	} catch (err) {
		console.error('Error loading consent records:', err);
		throw error(500, 'Failed to load consent records');
	}
};
