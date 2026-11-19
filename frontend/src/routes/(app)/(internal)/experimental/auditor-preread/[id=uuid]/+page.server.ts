import { nestedWriteFormAction } from '#lib/utils/actions.js';
import { BASE_API_URL } from '#lib/utils/constants.js';
import { getModelInfo } from '#lib/utils/crud.js';
import { formatSelectFieldData } from '#lib/utils/load.js';
import { modelSchema } from '#lib/utils/schemas.js';
import { error, type Actions } from '@sveltejs/kit';
import { superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import { m } from '#paraglide/messages.js';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, params, url }) => {
	// ?guide=<framework urn> applies a guide the numbering only partly matches.
	const guide = url.searchParams.get('guide');
	const query = guide ? `?guide=${encodeURIComponent(guide)}` : '';
	const [auditRes, prereadRes] = await Promise.all([
		fetch(`${BASE_API_URL}/compliance-assessments/${params.id}/`),
		fetch(`${BASE_API_URL}/compliance-assessments/${params.id}/auditor_preread/${query}`)
	]);
	if (!auditRes.ok || !prereadRes.ok) error(auditRes.ok ? prereadRes.status : auditRes.status);
	const audit = await auditRes.json();

	// The evidence form behind "Upload this document": the page fills in name and requirement.
	const evidenceModel = getModelInfo('evidences');
	const evidenceCreateForm = await superValidate(
		{ folder: audit.folder?.id },
		zod(modelSchema('evidences')),
		{ errors: false }
	);
	const selectOptions: Record<string, any> = {};
	await Promise.all(
		(evidenceModel.selectFields ?? []).map(async (f) => {
			const res = await fetch(`${BASE_API_URL}/evidences/${f.field}/`);
			if (res.ok) selectOptions[f.field] = formatSelectFieldData(await res.json(), f);
		})
	);
	evidenceModel.selectOptions = selectOptions;
	// "Add the file" on a paired evidence that has none: a new revision of it.
	const revisionModel = getModelInfo('evidence-revisions');
	const revisionCreateForm = await superValidate(
		{ folder: audit.folder?.id },
		zod(modelSchema('evidence-revisions')),
		{ errors: false }
	);

	return {
		audit,
		preread: await prereadRes.json(),
		evidenceModel,
		evidenceCreateForm,
		revisionModel,
		revisionCreateForm,
		title: m.prereadPageTitle({ name: audit.name })
	};
};

export const actions: Actions = {
	createRevision: async (event) => nestedWriteFormAction({ event, action: 'create' }),
	/** Create an evidence on the requirement, then pair it with the request it was uploaded for. */
	createEvidence: async (event) => {
		const result = await nestedWriteFormAction({ event, action: 'create' });
		const evidence = (result as any)?.form?.message?.object?.id;
		const q = event.url.searchParams;
		if (evidence && q.get('ra') && q.get('request')) {
			const res = await event.fetch(
				`${BASE_API_URL}/compliance-assessments/${event.params.id}/auditor_preread/pair/`,
				{
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({
						requirement_assessment: q.get('ra'),
						request: q.get('request'),
						evidence,
						guide: q.get('guide')
					})
				}
			);
			// The evidence is on file either way; unpaired, it shows as "to match".
			if (!res.ok) console.warn('auditor pre-read: pairing the new evidence failed', res.status);
		}
		return result;
	}
};
