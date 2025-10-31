import type { ParamMatcher } from '@sveltejs/kit';

export const match = ((param) => {
	const fields = ['configs', 'remote_objects'];

	return fields.includes(param.toLowerCase().replace(/-/g, '_'));
}) satisfies ParamMatcher;
