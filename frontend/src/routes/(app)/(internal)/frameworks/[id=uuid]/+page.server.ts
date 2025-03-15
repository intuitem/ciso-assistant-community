import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, params }) => {
	const URLModel = 'frameworks';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/object/`;

	const [framework, tree] = await Promise.all([
		fetch(endpoint).then((res) => res.json()),
		fetch(`${BASE_API_URL}/${URLModel}/${params.id}/tree`).then((res) => res.json())
	]);
	return { URLModel, framework, tree, title: framework.name };
}) satisfies PageServerLoad;
