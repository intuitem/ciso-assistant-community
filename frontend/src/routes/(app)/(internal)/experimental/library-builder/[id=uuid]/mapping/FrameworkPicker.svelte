<script lang="ts">
	import { onDestroy } from 'svelte';
	import AutocompleteSelect from '#lib/components/Forms/AutocompleteSelect.svelte';
	import { defaults, superForm } from 'sveltekit-superforms';
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
		label: string;
		options: Option[];
		value: string;
	}

	let { label, options, value = $bindable() }: Props = $props();

	// AutocompleteSelect needs a SuperForm: one-field, client-only.
	const schema = z.object({ framework: z.string().nullable().optional() });
	const form = superForm(defaults({ framework: value || null }, zod(schema)), {
		dataType: 'json',
		taintedMessage: false,
		SPA: true,
		validators: zod(schema)
	});
	const unsubscribe = form.form.subscribe((v) => {
		const next = v?.framework ?? '';
		if (next !== value) value = next;
	});
	onDestroy(unsubscribe);

	// Outside changes (swap, default source) flow back into the picker.
	$effect(() => {
		const next = value || null;
		form.form.update((v) => (v.framework === next ? v : { ...v, framework: next }), {
			taint: false
		});
	});

	const selectOptions = $derived(
		options.map((o) => ({
			value: o.urn,
			label: o.kind === 'draft' ? `${o.name} · ${m.lbMappingThisLibrary()}` : o.name
		}))
	);
</script>

{#if selectOptions.length}
	<AutocompleteSelect {form} field="framework" {label} options={selectOptions} nullable />
{/if}
