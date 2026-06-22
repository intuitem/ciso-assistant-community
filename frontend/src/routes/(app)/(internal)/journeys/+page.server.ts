import { BASE_API_URL } from '$lib/utils/constants';
import { listViewFields } from '$lib/utils/table';
import { type TableSource } from '@skeletonlabs/skeleton-svelte';
import { superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import { z } from 'zod';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch }) => {
	// Build the (empty) table skeleton from the journeys list-view config; ModelTable
	// fetches the rows client-side from /journeys.
	const base = listViewFields['journeys'];
	const head = base ? [...base.head] : [];
	const body = base ? [...base.body] : [];
	const headData: Record<string, string> = body.reduce(
		(obj, key, index) => {
			obj[key] = head[index];
			return obj;
		},
		{} as Record<string, string>
	);
	const table: TableSource = { head: headData, body: [], meta: [] };

	const deleteForm = await superValidate(zod(z.object({ id: z.string().uuid() })));

	// Presets feed the "Start a journey" picker; domains feed the folder selector.
	const presetsPromise = fetch(`${BASE_API_URL}/presets/`)
		.then((res) => res.json())
		.then((data) => data.results ?? data)
		.catch(() => []);

	const domainsPromise = fetch(`${BASE_API_URL}/folders?content_type=DO&content_type=GL`)
		.then((res) => res.json())
		.then((data) => data.results ?? data)
		.catch(() => []);

	const [presets, domains] = await Promise.all([presetsPromise, domainsPromise]);

	return { table, deleteForm, presets, domains, URLModel: 'journeys' };
};
