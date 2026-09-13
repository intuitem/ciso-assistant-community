import { BASE_API_URL } from '$lib/utils/constants';
import { fetchAllPages } from '$lib/utils/pagination';
import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import { fail, superValidate } from 'sveltekit-superforms';
import type { Actions, PageServerLoad } from './$types';
import { z } from 'zod';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import { m } from '$paraglide/messages';
import { setFlash } from 'sveltekit-flash-message/server';
import { safeTranslate } from '$lib/utils/i18n';

export const load: PageServerLoad = async (event) => {
	const detail = await loadDetail({
		event,
		model: getModelInfo('entity-assessments'),
		id: event.params.id
	});

	// The respondent view lives behind the linked audit's assignments, so surface a
	// direct way in from here rather than making the analyst walk the audit page.
	const auditId = detail.data?.compliance_assessment?.id;
	let reviewAssignments: Array<{ id: string; status: string }> = [];
	if (auditId) {
		const assignments = await fetchAllPages<{ id: string; status?: string }>(
			event.fetch,
			`${BASE_API_URL}/requirement-assignments/?compliance_assessment=${auditId}`
		).catch(() => []);
		reviewAssignments = assignments.filter(
			(a: { status?: string }) => a.status && a.status !== 'draft'
		) as Array<{ id: string; status: string }>;
	}

	return { ...detail, reviewAssignments };
};

export const actions: Actions = {
	clone: async (event) => {
		const formData = await event.request.formData();
		const res = await event.fetch(`${BASE_API_URL}/entity-assessments/${event.params.id}/clone/`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				name: formData.get('name'),
				version: formData.get('version')
			})
		});
		let body;
		try {
			body = await res.json();
		} catch {
			body = { error: res.statusText };
		}
		return { cloneStatus: res.status, cloneBody: body };
	},
	mailing: async ({ request, fetch, cookies }) => {
		const formData = await request.formData();
		const schema = z.object({ urlmodel: z.string(), id: z.string().uuid() });
		const ComplianceAssessmentForm = await superValidate(formData, zod(schema));

		const urlmodel = ComplianceAssessmentForm.data.urlmodel;
		const id = ComplianceAssessmentForm.data.id;
		const endpoint = `${BASE_API_URL}/${urlmodel}/${id}/mailing/`;

		if (!ComplianceAssessmentForm.valid) {
			return fail(400, { form: ComplianceAssessmentForm });
		}

		const requestInitOptions: RequestInit = {
			method: 'POST'
		};
		const res = await fetch(endpoint, requestInitOptions);
		if (!res.ok) {
			const response = await res.json();
			if (response.warning) {
				for (const warning of response.warning) {
					setFlash({ type: 'warning', message: safeTranslate(warning) }, cookies);
				}
				return fail(400, { form: ComplianceAssessmentForm });
			}
			setFlash({ type: 'error', message: m.mailFailedToSend() }, cookies);
			return fail(400, { form: ComplianceAssessmentForm });
		}
		// The assignments are started even when delivery fails, so this is a success
		// carrying a warning — not a failure.
		const response = await res.json();
		if (response.warning) {
			for (const warning of response.warning) {
				setFlash({ type: 'warning', message: safeTranslate(warning) }, cookies);
			}
			return { ComplianceAssessmentForm };
		}
		setFlash({ type: 'success', message: m.mailSuccessfullySent() }, cookies);
		return { ComplianceAssessmentForm };
	}
};
