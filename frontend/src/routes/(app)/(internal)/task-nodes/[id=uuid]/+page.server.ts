import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo, urlParamModelVerboseName } from '$lib/utils/crud';

import { safeTranslate } from '$lib/utils/i18n';
import { m } from '$paraglide/messages';

import { fail, type Actions } from '@sveltejs/kit';
import { message, setError, superValidate } from 'sveltekit-superforms';
import { setFlash } from 'sveltekit-flash-message/server';
import { zod } from 'sveltekit-superforms/adapters';
import { z } from 'zod';
import {
	nestedDeleteFormAction,
	nestedWriteFormAction,
	handleErrorResponse
} from '$lib/utils/actions';
import { modelSchema } from '$lib/utils/schemas';

import { loadDetail } from '$lib/utils/load';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
	const modelInfo = getModelInfo('task-nodes');

	const data = await loadDetail({
		event,
		model: modelInfo,
		id: event.params.id
	});

	return data;
};

export const actions: Actions = {};
