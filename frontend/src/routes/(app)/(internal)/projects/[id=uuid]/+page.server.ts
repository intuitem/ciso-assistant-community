import { getModelInfo } from '#lib/utils/crud.js';
import { loadDetail } from '#lib/utils/load.js';
import { BASE_API_URL } from '#lib/utils/constants.js';
import { fetchAllPages } from '#lib/utils/pagination.js';
import type { PageServerLoad } from './$types';
import { error, type Actions } from '@sveltejs/kit';
import { nestedDeleteFormAction } from '#lib/utils/actions.js';

export const load: PageServerLoad = async (event) => {
	const detail = await loadDetail({
		event,
		model: getModelInfo('projects'),
		id: event.params.id
	});

	const [priorityRes, kindRes, currenciesRes, statusTerms, healthTerms] = await Promise.all([
		event.fetch(`${BASE_API_URL}/pmbok/projects/priority/`),
		event.fetch(`${BASE_API_URL}/pmbok/projects/kind/`),
		event.fetch(`${BASE_API_URL}/pmbok/projects/currencies/`),
		fetchAllPages(event.fetch, `${BASE_API_URL}/terminologies/?field_path=project.status`).catch(
			() => []
		),
		fetchAllPages(event.fetch, `${BASE_API_URL}/terminologies/?field_path=project.health`).catch(
			() => []
		)
	]);

	const priorityOptions = priorityRes.ok ? await priorityRes.json() : [];
	const kindOptions = kindRes.ok ? await kindRes.json() : [];
	const currencyOptions = currenciesRes.ok ? await currenciesRes.json() : [];

	function toEnumOptions(items: any[]): { value: string; label: string }[] {
		return items
			.filter((t: any) => t.is_visible)
			.map((t: any) => ({ value: t.id, label: t.translated_name ?? t.name }));
	}
	const statusOptions = toEnumOptions(statusTerms);
	const healthOptions = toEnumOptions(healthTerms);
	// Snapshots store the value's name: colours are looked up by it.
	const toColors = (items: { name: string; hexcolor?: string }[]): Record<string, string> =>
		Object.fromEntries(items.map((t) => [t.name, t.hexcolor ?? '']));
	const statusColors = toColors(statusTerms);
	const healthColors = toColors(healthTerms);

	const [snapshotsRes, objectRes] = await Promise.all([
		event.fetch(
			`${BASE_API_URL}/metrology/builtin-metric-samples/for_object/?model=project&object_id=${event.params.id}`
		),
		event.fetch(`${BASE_API_URL}/pmbok/projects/${event.params.id}/object/`)
	]);
	const rawSnapshots = snapshotsRes.ok ? await snapshotsRes.json() : [];
	const snapshots = Array.isArray(rawSnapshots) ? [...rawSnapshots].reverse() : [];

	// The ids the project links to, from the raw object: the read data masks the
	// objects the user cannot see, and a section save must send those links back
	// untouched. Without them the page does not load.
	if (!objectRes.ok) {
		error(objectRes.status, objectRes.statusText || 'Failed to load the linked objects');
	}
	const rawObject = await objectRes.json();
	const linkedIds = Object.fromEntries(
		[
			'parent_project',
			'status',
			'health',
			'linked_collection',
			'responsibility_matrices',
			'filtering_labels',
			'owner',
			'sponsor'
		].map((field) => [field, rawObject[field]])
	);

	return {
		...detail,
		linkedIds,
		priorityOptions,
		kindOptions,
		currencyOptions,
		statusOptions,
		healthOptions,
		statusColors,
		healthColors,
		snapshots
	};
};

export const actions: Actions = {
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	}
};
