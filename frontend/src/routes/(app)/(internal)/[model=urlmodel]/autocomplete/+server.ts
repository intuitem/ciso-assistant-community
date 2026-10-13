import { BASE_API_URL } from '$lib/utils/constants';
import { error, type NumericRange } from '@sveltejs/kit';
import { getModelInfo } from '$lib/utils/crud';
import type { RequestHandler } from './$types';

/**
 * Generic proxy for the lightweight autocomplete action of any model whose
 * viewset mixes in AutocompleteMixin. Model-specific autocomplete routes (e.g.
 * assets/autocomplete) still take precedence over this param route.
 */
export const GET: RequestHandler = async ({ fetch, params, url }) => {
	const model = getModelInfo(params.model);
	const endpoint = `${BASE_API_URL}/${model.endpointUrl ?? params.model}/autocomplete/${
		url.searchParams.size ? '?' + url.searchParams.toString() : ''
	}`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		const body = await res.text();
		let parsed: unknown;
		try {
			parsed = JSON.parse(body);
		} catch {
			parsed = body;
		}
		error(res.status as NumericRange<400, 599>, parsed as any);
	}
	return new Response(res.body, {
		status: res.status,
		headers: { 'Content-Type': 'application/json' }
	});
};
