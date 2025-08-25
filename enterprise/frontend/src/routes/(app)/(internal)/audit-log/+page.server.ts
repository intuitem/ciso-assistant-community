import { m } from '$paraglide/messages';
import type { PageServerLoad } from './$types';
import { listViewFields } from '$lib/utils/table';
import { type TableSource } from '@skeletonlabs/skeleton-svelte';
import type { urlModel } from '$lib/utils/types';

export const load = (async () => {
	const URLModel = 'audit-logs' as urlModel;

	const headData: Record<string, string> = listViewFields[URLModel].body.reduce(
		(obj, key, index) => {
			obj[key] = listViewFields[URLModel].head[index];
			return obj;
		},
		{}
	);

	const table: TableSource = {
		head: headData,
		body: [],
		meta: []
	};
	return { table, title: m.auditLog() };
}) satisfies PageServerLoad;
