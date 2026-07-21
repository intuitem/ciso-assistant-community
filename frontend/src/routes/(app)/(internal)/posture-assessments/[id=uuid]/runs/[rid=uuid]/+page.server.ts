import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';
import { error, fail, type Actions, type NumericRange } from '@sveltejs/kit';

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
					results: [{ ref_id: formData.get('ref_id'), result: formData.get('result') }]
				})
			}
		);
		if (!res.ok) return fail(res.status, await res.json());
		return await res.json();
	}
};
