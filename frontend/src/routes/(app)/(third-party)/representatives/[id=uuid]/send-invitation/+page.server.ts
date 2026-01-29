import { BASE_API_URL } from '$lib/utils/constants';
import { setFlash } from 'sveltekit-flash-message/server';
import type { Actions } from './$types';
import { message, superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import { z } from 'zod';
import { m } from '$paraglide/messages';

const schema = z.object({
	id: z.string({ required_error: 'idRequired' }).uuid('idRequired')
});

function getId(formData: FormData): string | undefined {
	const raw = formData.get('__superform_json');
	if (typeof raw !== 'string') {
		return undefined;
	}

	let parsed = JSON.parse(raw);

	if (Array.isArray(parsed)) {
		const mapping = parsed[0];
		if (mapping && typeof mapping === 'object' && typeof (mapping as any).id === 'number') {
			const idIndex = (mapping as any).id;
			return typeof parsed[idIndex] === 'string' ? (parsed[idIndex] as string) : undefined;
		}
		const found = parsed.find((v) => typeof v === 'string' && v.includes('@'));
		return typeof found === 'string' ? found : undefined;
	}

	if (parsed && typeof parsed === 'object') {
		const record = parsed as Record<string, unknown>;
		const id = record.id ?? record['__id'];
		return typeof id === 'string' ? id : undefined;
	}

	return undefined;
}

export const actions: Actions = {
	default: async (event) => {
		const formData = await event.request.formData();
		const id = getId(formData);
		const form = await superValidate({ id }, zod(schema));

		const res = await event.fetch(`${BASE_API_URL}/iam/send-invitation/`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ id: id })
		});

		if (!res.ok) {
			setFlash({ type: 'error', message: m.anErrorOccurred() }, event);
			return message(form, { error: 'Unable to send email' });
		}

		setFlash({ type: 'success', message: m.invitationSent() }, event);
		return message(form, { success: true });
	}
};
