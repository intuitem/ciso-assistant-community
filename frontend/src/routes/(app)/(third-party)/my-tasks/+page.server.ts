import { BASE_API_URL } from '#lib/utils/constants.js';
import { fetchTasks } from '#lib/utils/vendorTasks.js';
import { redirect } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';
import { m } from '#paraglide/messages.js';

export const load: PageServerLoad = async ({ fetch, parent, url }) => {
	const mine = url.searchParams.has('mine');
	const { user, featureflags } = await parent();
	if (featureflags?.tasks === false) redirect(302, '/auditee-dashboard');
	const query = mine ? user.all_actor_ids.map((id: string) => `&assigned_to=${id}`).join('') : '';
	const [tasks, assignments, statusOptions] = await Promise.all([
		fetchTasks(fetch, query),
		fetch(`${BASE_API_URL}/requirement-assignments/?limit=1000`).then(async (r) =>
			r.ok ? (await r.json()).results : []
		),
		fetch(`${BASE_API_URL}/task-templates/status/`).then(async (r) => (r.ok ? r.json() : {}))
	]);
	const links: Record<string, { href: string; label: string }> = {};
	for (const a of assignments) {
		const href = `/auditee-assessments/${a.id}`;
		const audit = a.compliance_assessment.str;
		links[a.compliance_assessment.id] ??= { href, label: audit };
		for (const ra of a.requirement_assessments) {
			links[ra.id] = { href: `${href}?ra=${ra.id}`, label: `${audit} › ${ra.str}` };
		}
	}
	return { tasks, links, mine, statusOptions, title: m.myTasks() };
};

export const actions: Actions = {
	updateStatus: async ({ request, fetch }) => {
		const { id, status } = await request.json();
		const res = await fetch(`${BASE_API_URL}/task-templates/${id}/`, {
			method: 'PATCH',
			body: JSON.stringify({ status })
		});
		return { status: res.status };
	}
};
