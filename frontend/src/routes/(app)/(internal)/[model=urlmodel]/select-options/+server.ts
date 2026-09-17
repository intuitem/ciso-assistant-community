import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';

export const GET: RequestHandler = async ({ fetch, params, url }) => {
	const field = url.searchParams.get('field');
	const detail = url.searchParams.get('detail');
	const model = getModelInfo(params.model);
	const selectField = model.selectFields?.find((f) => f.field === field);
	if (!selectField) error(404, `Unknown select field '${field}' on '${params.model}'`);

	const endpoint =
		selectField.formNestedField && selectField.detail === true && detail
			? `${BASE_API_URL}/${selectField.endpointUrl}/${detail}/${selectField.field}/`
			: `${BASE_API_URL}/${model.endpointUrl ?? params.model}/${selectField.field}/`;

	const res = await fetch(endpoint);
	if (!res.ok) error(res.status as NumericRange<400, 599>, await res.text());
	return new Response(JSON.stringify(await res.json()), {
		headers: { 'Content-Type': 'application/json' }
	});
};
