import { handleErrorResponse, normalizeServiceAccountAuthorization } from '#lib/utils/actions.js';
import { BASE_API_URL } from '#lib/utils/constants.js';
import { getModelInfo } from '#lib/utils/crud.js';
import { getSecureRedirect } from '#lib/utils/helpers.js';
import { safeTranslate } from '#lib/utils/i18n.js';
import { modelSchema } from '#lib/utils/schemas.js';
import { m } from '#paraglide/messages.js';
import { fail, redirect, type Actions } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { message, superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import type { PageServerLoad } from './$types';
import { errorFromBody } from '#lib/utils/errors.js';

const URLModel = 'service-accounts';

export const load: PageServerLoad = async (event) => {
	const model = getModelInfo(URLModel);
	const schema = modelSchema(URLModel);

	const endpoint = `${BASE_API_URL}/${model.endpointUrl}/${event.params.id}/`;
	const res = await event.fetch(endpoint);
	if (!res.ok) {
		errorFromBody(res.status, await res.json());
	}
	const serviceAccount = await res.json();
	const object = {
		name: serviceAccount.name,
		description: serviceAccount.description,
		identity_source: serviceAccount.identity_source,
		social_app: serviceAccount.social_app?.id,
		federated_subject: serviceAccount.federated_subject,
		permissions: serviceAccount.permissions?.map((permission: { id: number }) => permission.id),
		folders: serviceAccount.folders?.map((folder: { id: string }) => folder.id),
		is_recursive: serviceAccount.is_recursive,
		expiry_date: serviceAccount.expiry_date,
		is_role_linked: serviceAccount.is_role_linked,
		is_global_admin: serviceAccount.is_global_admin,
		role_name: serviceAccount.role_name,
		role: serviceAccount.role,
		authorization_mode: serviceAccount.is_global_admin
			? 'global_admin'
			: serviceAccount.is_role_linked
				? 'role'
				: 'custom'
	};

	const form = await superValidate(object, zod(schema), { errors: false });

	return { form, model, object, URLModel, title: m.edit() };
};

export const actions: Actions = {
	default: async (event) => {
		const formData = await event.request.formData();
		if (!formData) {
			return fail(400, { form: null });
		}

		const schema = modelSchema(URLModel);
		const form = await superValidate(formData, zod(schema));

		if (!form.valid) {
			console.error(form.errors);
			return message(form, { status: 400 });
		}

		normalizeServiceAccountAuthorization(form.data);

		const model = getModelInfo(URLModel);
		const endpoint = `${BASE_API_URL}/${model.endpointUrl}/${event.params.id}/`;

		// The backend only implements partial_update for service accounts: PATCH.
		const res = await event.fetch(endpoint, {
			method: 'PATCH',
			body: JSON.stringify(form.data)
		});

		if (!res.ok) return await handleErrorResponse({ event, response: res, form });

		const writtenObject = await res.json();

		setFlash(
			{
				type: 'success',
				message: m.successfullyUpdatedObject({
					object: safeTranslate(model.verboseName).toLowerCase()
				})
			},
			event
		);

		const next = getSecureRedirect(event.url.searchParams.get('next'));
		if (next) redirect(302, next);

		return message(form, { object: writtenObject });
	}
};
