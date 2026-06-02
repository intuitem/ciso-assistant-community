import { BASE_API_URL } from '$lib/utils/constants';
import { InfraConfigSchema } from '$lib/utils/infra-config';
import { safeTranslate } from '$lib/utils/i18n';
import { m } from '$paraglide/messages';
import { fail, type Actions } from '@sveltejs/kit';
import { message, superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch }) => {
	let infraConfig: { allowed_ips: string[] } = { allowed_ips: [] };
	try {
		const response = await fetch(`${BASE_API_URL}/settings/infra-config/`);
		if (response.ok) {
			infraConfig = await response.json();
		}
	} catch (e) {
		// Backend unreachable / timed out — fall back to an empty config rather
		// than 500-ing the settings page.
		console.error('Failed to load infra-config settings', e);
	}

	const form = await superValidate(infraConfig, zod(InfraConfigSchema), { errors: false });

	return { infraConfig, form, title: m.infraConfig() };
};

export const actions: Actions = {
	saveInfraConfig: async (event) => {
		const formData = await event.request.formData();

		if (!formData) {
			return fail(400, { form: null });
		}

		const form = await superValidate(formData, zod(InfraConfigSchema));

		if (!form.valid) {
			return fail(400, { form });
		}

		const endpoint = `${BASE_API_URL}/settings/infra-config/`;
		const response = await event.fetch(endpoint, {
			method: 'PUT',
			body: JSON.stringify(form.data)
		});

		if (!response.ok) {
			const res: Record<string, any> = await response.json().catch(() => ({}));
			// Collect human-readable messages: allowed_ips field errors first, then generic.
			const raw: string[] = Array.isArray(res.allowed_ips)
				? res.allowed_ips
				: res.detail
					? [res.detail]
					: res.error
						? Array.isArray(res.error)
							? res.error
							: [res.error]
						: [];
			const text = raw.map((msg) => safeTranslate(msg)).join(' ') || m.anErrorOccurred();
			// Surfaced inline via $message in the page (no flash: with applyAction/
			// invalidateAll disabled the flash cookie would otherwise show stale on
			// the next navigation).
			return message(form, { type: 'error', text }, { status: response.status });
		}

		return message(form, { type: 'success', text: m.infraConfigSettingsUpdated() });
	}
};
