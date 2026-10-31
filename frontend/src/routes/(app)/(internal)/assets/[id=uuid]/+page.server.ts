import { BASE_API_URL } from '#lib/utils/constants.js';
import type { PageServerLoad } from './$types';

// The homologation tab reads where the asset stands in its framing journey,
// and shows from the start when a framing form can describe it.
export const load: PageServerLoad = async ({ fetch, params }) => {
	const query = new URLSearchParams({ target: 'asset.risk_assessment', subject: params.id });
	const [journey, options] = await Promise.all([
		fetch(`${BASE_API_URL}/assets/${params.id}/assessment-journey/`).then((res) =>
			res.ok ? res.json() : null
		),
		fetch(`${BASE_API_URL}/quick-forms/assess-options/?${query}`).then((res) =>
			res.ok ? res.json() : []
		)
	]);
	return { journey, canFrame: Array.isArray(options) && options.length > 0 };
};
