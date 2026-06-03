import { BASE_API_URL } from '$lib/utils/constants';
import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch }) => {
	const res = await fetch(`${BASE_API_URL}/analytics/export/xlsx/`);
	if (!res.ok) {
		const status = (res.status >= 400 && res.status <= 599 ? res.status : 502) as NumericRange<
			400,
			599
		>;
		error(status, 'Error generating the analytics XLSX export');
	}

	const fileName = `ciso-assistant-analytics-${new Date().toISOString().split('T')[0]}.xlsx`;

	return new Response(await res.blob(), {
		headers: {
			'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
			'Content-Disposition': `attachment; filename="${fileName}"`
		}
	});
};
