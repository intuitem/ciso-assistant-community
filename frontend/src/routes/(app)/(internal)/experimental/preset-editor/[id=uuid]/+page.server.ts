import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';

export const load: PageServerLoad = async ({ fetch, params }) => {
	const presetRes = await fetch(`${BASE_API_URL}/presets/${params.id}/`);
	if (!presetRes.ok) {
		throw error(presetRes.status, 'Preset not found');
	}
	const preset = await presetRes.json();

	const [frameworks, riskMatrices] = await Promise.all([
		fetch(`${BASE_API_URL}/frameworks/?ordering=name`)
			.then((r) => r.json())
			.then((d) => d.results ?? d)
			.catch(() => []),
		fetch(`${BASE_API_URL}/risk-matrices/?ordering=name`)
			.then((r) => r.json())
			.then((d) => d.results ?? d)
			.catch(() => [])
	]);

	return { preset, frameworks, riskMatrices };
};
