import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import { fail, superValidate } from 'sveltekit-superforms';
import type { Actions, PageServerLoad } from './$types';
import { z } from 'zod';
import { zod } from 'sveltekit-superforms/adapters';
import * as m from '$paraglide/messages';
import { setFlash } from 'sveltekit-flash-message/server';

export const load: PageServerLoad = async (event) => {
	return loadDetail({ event, model: getModelInfo('entity-assessments'), id: event.params.id });
};

export const actions: Actions = {
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
			setFlash({ type: 'error', message: m.mailFailedToSend() }, cookies);
			return fail(400, { form: ComplianceAssessmentForm });
		}
		setFlash({ type: 'success', message: m.mailSuccessfullySent() }, cookies);
		return { ComplianceAssessmentForm };
	}
};
