import { BASE_API_URL } from '$lib/utils/constants';
import { m } from '$paraglide/messages';

import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

type WordExportFailure = {
	error?:
		| 'invalidCustomWordTemplate'
		| 'customWordTemplateTimedOut'
		| 'customWordTemplateCrashed'
		| 'customWordTemplateFailed';
	detail?: string;
};

function failureMessage(failure: WordExportFailure): string {
	if (failure.error === 'customWordTemplateTimedOut') return m.customWordTemplateTimedOut();
	if (failure.error === 'customWordTemplateCrashed') return m.customWordTemplateCrashed();
	if (failure.error === 'customWordTemplateFailed') return m.customWordTemplateFailed();
	if (failure.error === 'invalidCustomWordTemplate' && failure.detail)
		return m.invalidCustomWordTemplate({ detail: failure.detail });
	return 'Error fetching the Word file';
}

export const GET: RequestHandler = async ({ fetch, params }) => {
	const URLModel = 'compliance-assessments';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/word_report/`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		const failure: WordExportFailure = await res.json().catch(() => ({}));
		error(res.status, failureMessage(failure));
	}

	const fileName = `audit-exec-summary-${new Date().toISOString()}.docx`;

	return new Response(res.body, {
		headers: {
			'Content-Type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
			'Content-Disposition': `attachment; filename="${fileName}"`,
			'Transfer-Encoding': 'chunked'
		}
	});
};
