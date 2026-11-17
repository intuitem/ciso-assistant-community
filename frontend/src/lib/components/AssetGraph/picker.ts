import { get } from 'svelte/store';
import { defaults, superForm, type SuperForm } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import { z } from 'zod';

export function createPickerForm(field: string, initial: string | null = null) {
	const schema = z.object({ [field]: z.string().nullable().optional() });
	const form = superForm(defaults({ [field]: initial }, zod(schema)), {
		dataType: 'json',
		taintedMessage: false,
		SPA: true,
		validators: zod(schema)
	}) as unknown as SuperForm<Record<string, unknown>>;
	const clear = () => form.form.set({ ...get(form.form), [field]: null });
	return { form, clear };
}
