<script lang="ts">
	import { onDestroy } from 'svelte';
	import AutocompleteSelect from '#lib/components/Forms/AutocompleteSelect.svelte';
	import { defaults, superForm, type SuperForm } from 'sveltekit-superforms';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { z } from 'zod';
	import { m } from '#paraglide/messages.js';

	interface Option {
		urn: string;
		name: string;
		library_urn: string;
		kind: 'draft' | 'library';
	}

	interface Props {
		/** Form field name, also the input id: unique per picker on a page. */
		field: string;
		label: string;
		options: Option[];
		value: string;
	}

	let { field, label, options, value = $bindable() }: Props = $props();

	// AutocompleteSelect needs a SuperForm: one-field, client-only.
	const schema = z.object({ [field]: z.string().nullable().optional() });
	const form = superForm(defaults({ [field]: value || null }, zod(schema)), {
		dataType: 'json',
		taintedMessage: false,
		SPA: true,
		validators: zod(schema)
	});
	const unsubscribe = form.form.subscribe((v) => {
		const next = (v?.[field] as string | null | undefined) ?? '';
		if (next !== value) value = next;
	});
	onDestroy(unsubscribe);

	// Outside changes (swap, default source) flow back into the picker.
	$effect(() => {
		const next = value || null;
		form.form.update((v) => (v[field] === next ? v : { ...v, [field]: next }), {
			taint: false
		});
	});

	// The computed key types as an index signature; AutocompleteSelect wants a record.
	const pickerForm = form as unknown as SuperForm<Record<string, unknown>>;

	const selectOptions = $derived(
		options.map((o) => ({
			value: o.urn,
			label: o.kind === 'draft' ? `${o.name} · ${m.lbMappingThisLibrary()}` : o.name
		}))
	);
</script>

{#if selectOptions.length}
	<AutocompleteSelect form={pickerForm} {field} {label} options={selectOptions} nullable />
{/if}
