import { BASE_API_URL } from '$lib/utils/constants';
import { m } from '$paraglide/messages';
import { getModelInfo } from '$lib/utils/crud';
import { safeTranslate } from '$lib/utils/i18n';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, params }) => {
	const endpoint = `${BASE_API_URL}/log-entries/${params.id}/`;
	try {
		const res = await fetch(endpoint);
		if (!res.ok) {
			throw new Error(`Failed to fetch log entry: ${res.status}`);
		}
		const log = await res.json();
		const { foreignKeyFields } = getModelInfo('audit-logs');

		return {
			log,
			foreignKeyFields,
			title: m.logEntryRepr({
				actor: log.actor.str,
				action: safeTranslate(log.action),
				timestamp: log.timestamp,
				object: log.object_repr
			})
		};
	} catch (error) {
		console.error('Error loading audit log entry:', error);
		throw error;
	}
}) satisfies PageServerLoad;
