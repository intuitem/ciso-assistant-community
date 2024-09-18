import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, params }) => {
	const URLModel = 'frameworks';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/object/`;

	const res = await fetch(endpoint);
	const framework = await res.json();
	const tree = await fetch(`${BASE_API_URL}/${URLModel}/${params.id}/tree`).then((res) =>
		res.json()
	);
	return { URLModel, framework, tree };
}) satisfies PageServerLoad;
