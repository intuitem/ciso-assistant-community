import type { Actions, PageServerLoad } from './$types';

import { BASE_API_URL } from '$lib/utils/constants';
import { type TableSource } from '@skeletonlabs/skeleton-svelte';
import { listViewFields } from '$lib/utils/table';
import { fail, superValidate } from 'sveltekit-superforms';
import { z } from 'zod';
import { zod } from 'sveltekit-superforms/adapters';
import { setFlash } from 'sveltekit-flash-message/server';
import { m } from '$paraglide/messages';

export const load = (async ({ fetch, params }) => {
	const URLModel = 'risk-scenarios';
	const baseEndpoint = `${BASE_API_URL}/${URLModel}/${params.id}/`;
	const objectEndpoint = `${BASE_API_URL}/${URLModel}/${params.id}/object/`;
	const object = await fetch(objectEndpoint).then((res) => res.json());
	const scenario = await fetch(baseEndpoint).then((res) => res.json());

	const tables: Record<string, any> = {};

	await Promise.all(
		['assets', 'threats', 'vulnerabilities', 'security-exceptions'].map(async (key) => {
			const keyEndpoint = `${BASE_API_URL}/${key}/?risk_scenarios=${params.id}`;
			const response = await fetch(keyEndpoint);
			if (response.ok) {
				const table: TableSource = {
					head: listViewFields[key].head,
					body: [],
					meta: []
				};
				tables[key] = table;
			} else {
				console.error(`Failed to fetch data for ${key}: ${response.statusText}`);
			}
		})
	);
	//todo the naming here is not great because of inverted logic inhereted from the filters
	await Promise.all(
		['risk_scenarios', 'risk_scenarios_e'].map(async (key) => {
			const table: TableSource = {
				head: ['name', 'owner', 'eta'],
				body: [],
				meta: []
			};
			tables[key] = table;
		})
	);

	const riskMatrix = await fetch(`${BASE_API_URL}/risk-matrices/${object.risk_matrix}/`)
		.then((res) => res.json())
		.then((res) => JSON.parse(res.json_definition));

	return { scenario, tables, riskMatrix, title: scenario.name };
}) satisfies PageServerLoad;

export const actions: Actions = {
	syncToActions: async (event) => {
		const formData = await event.request.formData();

		if (!formData) {
			return fail(400, { form: null });
		}

		const schema = z.object({ reset_residual: z.boolean().optional() });
		const form = await superValidate(formData, zod(schema));

		const response = await event.fetch(
			`${BASE_API_URL}/risk-scenarios/${event.params.id}/sync-to-actions/?dry_run=false`,
			{
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(form.data)
			}
		);
		if (response.ok) {
			setFlash(
				{
					type: 'success',
					message: m.syncToAppliedControlsSuccess()
				},
				event
			);
		} else {
			setFlash(
				{
					type: 'error',
					message: m.syncToAppliedControlsError()
				},
				event
			);
		}
		return { form, message: { appliedControls: await response.json() } };
	}
};
