import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { BASE_API_URL, UUID_REGEX } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';

export const GET: RequestHandler = async ({ fetch, url }) => {
	const urlModel = url.searchParams.get('model') ?? '';
	const field = url.searchParams.get('field');
	const detail = url.searchParams.get('detail');

	// URL_MODEL_MAP, not URL_MODEL: models without a generic route still have
	// select fields.
	const model = getModelInfo(urlModel);
	const selectField = model.selectFields?.find((f) => f.field === field);
	if (!selectField) error(404, `Unknown select field '${field}' on '${urlModel}'`);
	// Interpolated into a backend path, and `../` normalises away the API prefix.
	if (detail && !new RegExp(`^${UUID_REGEX}$`).test(detail)) error(400, 'Invalid detail id');

	const endpoint =
		selectField.formNestedField && selectField.detail === true && detail
			? `${BASE_API_URL}/${selectField.endpointUrl}/${detail}/${selectField.field}/`
			: `${BASE_API_URL}/${model.endpointUrl ?? urlModel}/${selectField.field}/`;

	const res = await fetch(endpoint);
	if (!res.ok) error(res.status as NumericRange<400, 599>, await res.text());
	return new Response(JSON.stringify(await res.json()), {
		headers: { 'Content-Type': 'application/json' }
	});
};
