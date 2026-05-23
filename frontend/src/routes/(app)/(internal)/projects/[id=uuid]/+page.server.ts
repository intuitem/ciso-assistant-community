import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';
import type { Actions } from '@sveltejs/kit';
import { nestedDeleteFormAction } from '$lib/utils/actions';

export const load: PageServerLoad = async (event) => {
	const detail = await loadDetail({
		event,
		model: getModelInfo('projects'),
		id: event.params.id
	});

	const [priorityRes, kindRes, currenciesRes] = await Promise.all([
		event.fetch(`${BASE_API_URL}/pmbok/projects/priority/`),
		event.fetch(`${BASE_API_URL}/pmbok/projects/kind/`),
		event.fetch(`${BASE_API_URL}/pmbok/projects/currencies/`)
	]);

	const priorityOptions = priorityRes.ok ? await priorityRes.json() : [];
	const kindOptions = kindRes.ok ? await kindRes.json() : [];
	const currencyOptions = currenciesRes.ok ? await currenciesRes.json() : [];

	const snapshotsRes = await event.fetch(
		`${BASE_API_URL}/metrology/builtin-metric-samples/for_object/?model=project&object_id=${event.params.id}`
	);
	const rawSnapshots = snapshotsRes.ok ? await snapshotsRes.json() : [];
	const snapshots = Array.isArray(rawSnapshots) ? [...rawSnapshots].reverse() : [];

	return {
		...detail,
		priorityOptions,
		kindOptions,
		currencyOptions,
		snapshots
	};
};

export const actions: Actions = {
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	}
};
