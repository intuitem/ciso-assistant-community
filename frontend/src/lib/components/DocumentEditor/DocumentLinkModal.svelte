<script lang="ts">
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import { superForm, defaults } from 'sveltekit-superforms';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { z } from 'zod';
	import { m } from '$paraglide/messages';

	interface Props {
		onInsert: (c: { id: string; name: string }) => void;
		onClose: () => void;
	}
	let { onInsert, onClose }: Props = $props();

	const schema = z.object({ document: z.string().optional() });
	const _form = superForm(defaults(zod(schema)), {
		dataType: 'json',
		taintedMessage: false,
		SPA: true,
		validators: zod(schema)
	});
	const { form } = _form;

	let busy = $state(false);

	async function insert() {
		const id = $form.document;
		if (!id) return;
		busy = true;
		try {
			// /document-containers/{id} is served by the static [id]/+server.ts GET.
			const res = await fetch(`/document-containers/${id}`);
			const c = res.ok ? await res.json() : {};
			onInsert({ id, name: c.name || c.str || 'document' });
		} finally {
			busy = false;
		}
	}
</script>

<div
	class="fixed inset-0 z-[60] flex items-start justify-center bg-black/40 p-4 pt-24"
	role="presentation"
	onclick={onClose}
>
	<div
		class="card bg-surface-50-950 w-modal max-w-md space-y-4 p-4 shadow-xl"
		role="presentation"
		onclick={(e) => e.stopPropagation()}
	>
		<div class="flex items-center justify-between">
			<h3 class="text-lg font-bold">{m.linkToDocument()}</h3>
			<button
				type="button"
				aria-label={m.close()}
				class="cursor-pointer hover:text-primary-500"
				onclick={onClose}
			>
				<i class="fa-solid fa-xmark"></i>
			</button>
		</div>
		<AutocompleteSelect
			form={_form}
			lazy
			optionsEndpoint="document-containers"
			optionsExtraFields={[['folder', 'str']]}
			optionsLabelField="name"
			field="document"
			label={m.documentContainer()}
		/>
		<div class="flex justify-end gap-2">
			<button type="button" class="btn preset-tonal" onclick={onClose}>{m.cancel()}</button>
			<button
				type="button"
				class="btn preset-filled-primary-500"
				disabled={busy || !$form.document}
				onclick={insert}
			>
				{m.insertLink()}
			</button>
		</div>
	</div>
</div>
