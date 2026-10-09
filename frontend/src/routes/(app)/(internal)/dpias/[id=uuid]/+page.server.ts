import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import { nestedDeleteFormAction } from '$lib/utils/actions';
import { fail, type Actions } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { m } from '$paraglide/messages';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
	const detailData = await loadDetail({
		event,
		model: getModelInfo('dpias'),
		id: event.params.id
	});

	const [report, riskMatrices] = await Promise.all([
		event
			.fetch(`${BASE_API_URL}/privacy/dpias/${event.params.id}/report/`)
			.then((res) => (res.ok ? res.json() : null)),
		event
			.fetch(`${BASE_API_URL}/risk-matrices/`)
			.then((res) => (res.ok ? res.json() : { results: [] }))
			.then((body) => body.results ?? [])
	]);

	return { ...detailData, report, riskMatrices };
};

export const actions: Actions = {
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	},
	createRiskRegisters: async (event) => {
		const formData = await event.request.formData();
		const res = await event.fetch(
			`${BASE_API_URL}/privacy/dpias/${event.params.id}/risk-registers/`,
			{
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ risk_matrix: formData.get('risk_matrix') })
			}
		);
		if (!res.ok) {
			setFlash({ type: 'error', message: m.dpiaRiskRegistersFailed() }, event);
			return fail(res.status);
		}
		setFlash({ type: 'success', message: m.dpiaRiskRegistersCreated() }, event);
		return { success: true };
	}
};
