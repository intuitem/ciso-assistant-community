import { BASE_API_URL } from '$lib/utils/constants';
import { fail, type Actions } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { m } from '$paraglide/messages';

import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, params, url }) => {
	const graphEndpoint = `${BASE_API_URL}/ebios-rm/operating-modes/${params.id}/build_graph/`;
	const eaEndpoint = `${BASE_API_URL}/ebios-rm/elementary-actions/?operating_modes=${params.id}`;
	const killChainEndpoint = `${BASE_API_URL}/ebios-rm/kill-chains/?operating_mode=${params.id}`;

	const [graphRes, eaRes, kcRes] = await Promise.all([
		fetch(graphEndpoint),
		fetch(eaEndpoint),
		fetch(killChainEndpoint)
	]);

	const graphData = await graphRes.json();
	const eaData = await eaRes.json();
	const kcData = await kcRes.json();

	const animated = url.searchParams.get('animated') === 'true';
	return {
		data: graphData,
		animated,
		elementaryActions: eaData.results ?? eaData,
		killChainSteps: kcData.results ?? kcData,
		operatingModeId: params.id
	};
}) satisfies PageServerLoad;

export const actions: Actions = {
	saveGraph: async (event) => {
		const formData = await event.request.formData();
		const killChainStepsJson = formData.get('kill_chain_steps');

		if (!killChainStepsJson || typeof killChainStepsJson !== 'string') {
			return fail(400, { error: 'Missing kill_chain_steps data' });
		}

		let killChainSteps;
		try {
			killChainSteps = JSON.parse(killChainStepsJson);
		} catch {
			return fail(400, { error: 'Invalid JSON in kill_chain_steps' });
		}

		const endpoint = `${BASE_API_URL}/ebios-rm/operating-modes/${event.params.id}/save_graph/`;

		const response = await event.fetch(endpoint, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({ kill_chain_steps: killChainSteps })
		});

		if (response.ok) {
			const graphData = await response.json();
			setFlash(
				{
					type: 'success',
					message: m.successfullyUpdatedObject({ object: m.operatingMode().toLowerCase() })
				},
				event
			);
			return { success: true, graphData };
		} else {
			const errData = await response.json();
			setFlash(
				{
					type: 'error',
					message: errData.errors?.join(', ') ?? m.errorOccurred()
				},
				event
			);
			return fail(response.status, { error: errData.errors });
		}
	}
};
