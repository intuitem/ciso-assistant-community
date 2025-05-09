import { BASE_API_URL } from '$lib/utils/constants';
import { m } from '$paraglide/messages';
import { safeTranslate } from '$lib/utils/i18n'
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, params }) => {
	const endpoint = `${BASE_API_URL}/log-entries/${params.id}/`;

	const res = await fetch(endpoint);
	const log = await res.json();

	return { log, title: m.logEntryRepr({actor: log.actor.str, action: safeTranslate(log.action), timestamp: log.timestamp, object: log.object_repr}) };
}) satisfies PageServerLoad;
