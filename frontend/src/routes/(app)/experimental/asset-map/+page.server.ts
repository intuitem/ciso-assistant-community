import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { modelSchema } from '$lib/utils/schemas';
import { defaultWriteFormAction } from '$lib/utils/actions';
import { superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, url }) => {
	const focus = url.searchParams.get('focus') ?? '';
	const mode = url.searchParams.get('mode') === 'connected' ? 'connected' : 'chain';
	const maxHops = url.searchParams.get('max_hops') ?? '';
	const expand = url.searchParams.getAll('expand');
	const reveal = url.searchParams.getAll('reveal');

	let graph = null;
	let graphError: string | null = null;
	if (focus) {
		const params = new URLSearchParams({ mode });
		if (maxHops) params.set('max_hops', maxHops);
		for (const id of expand) params.append('expand', id);
		for (const id of reveal) params.append('reveal', id);
		const res = await fetch(
			`${BASE_API_URL}/assets/${encodeURIComponent(focus)}/dependency-graph/?${params}`
		);
		if (res.ok) graph = await res.json();
		else graphError = res.status === 404 ? 'notFound' : 'failed';
	}

	const typeRes = await fetch(`${BASE_API_URL}/assets/type/`);
	const typeData = typeRes.ok ? await typeRes.json() : {};

	return {
		title: 'Asset dependency map',
		focus,
		mode,
		maxHops,
		expand,
		graph,
		graphError,
		assetModel: {
			...getModelInfo('assets'),
			urlModel: 'assets',
			createForm: await superValidate({}, zod(modelSchema('assets')), { errors: false }),
			selectOptions: {
				type: Object.entries(typeData).map(([value, label]) => ({ label: label as string, value }))
			}
		}
	};
};

export const actions: Actions = {
	create: async (event) =>
		defaultWriteFormAction({
			event,
			urlModel: 'assets',
			action: 'create',
			redirectToWrittenObject: false
		})
};
