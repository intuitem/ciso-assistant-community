import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';
import { error, fail, redirect, type Actions, type NumericRange } from '@sveltejs/kit';

export const load: PageServerLoad = async (event) => {
	const res = await event.fetch(
		`${BASE_API_URL}/automation/posture-assessments/${event.params.id}/runs/${event.params.rid}/`
	);
	if (!res.ok) error(res.status as NumericRange<400, 599>, await res.json());
	const body = await res.json();
	const assessmentRes = await event.fetch(
		`${BASE_API_URL}/automation/posture-assessments/${event.params.id}/`
	);
	if (!assessmentRes.ok)
		error(assessmentRes.status as NumericRange<400, 599>, await assessmentRes.json());
	const assessment = await assessmentRes.json();
	return { run: body.run, results: body.results, assessment, title: assessment.name };
};

export const actions: Actions = {
	setResult: async (event) => {
		const formData = await event.request.formData();
		const res = await event.fetch(
			`${BASE_API_URL}/automation/posture-assessments/${event.params.id}/upload-results/`,
			{
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					asset: formData.get('asset'),
					run_id: event.params.rid,
					source: 'manual',
					results: [
						{
							ref_id: formData.get('ref_id'),
							result: formData.get('result'),
							// pass tool-recorded values through so an edit doesn't wipe them
							actual: formData.get('actual') ?? '',
							expected: formData.get('expected') ?? '',
							message: formData.get('message') ?? ''
						}
					]
				})
			}
		);
		if (!res.ok) return fail(res.status, await res.json());
		return await res.json();
	},
	updateRun: async (event) => {
		const formData = await event.request.formData();
		const fd = new FormData();
		if (formData.has('observation')) fd.set('observation', formData.get('observation') as string);
		const attachment = formData.get('attachment');
		if (attachment instanceof File && attachment.size > 0) fd.set('attachment', attachment);
		if (formData.get('remove_attachment')) fd.set('remove_attachment', 'true');
		const res = await event.fetch(
			`${BASE_API_URL}/automation/posture-assessments/${event.params.id}/runs/${event.params.rid}/`,
			{ method: 'PATCH', body: fd }
		);
		if (!res.ok) return fail(res.status, await res.json());
		return { updatedRun: await res.json() };
	},
	deleteRun: async (event) => {
		const res = await event.fetch(
			`${BASE_API_URL}/automation/posture-assessments/${event.params.id}/runs/${event.params.rid}/`,
			{ method: 'DELETE' }
		);
		if (!res.ok) return fail(res.status, await res.json());
		redirect(303, `/posture-assessments/${event.params.id}`);
	}
};
