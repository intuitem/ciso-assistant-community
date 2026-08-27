<script lang="ts">
	import { m } from '$paraglide/messages';
	import { onDestroy } from 'svelte';
	import FilterNameModal from './FilterNameModal.svelte';
	import FolderTreeSelect from '$lib/components/Forms/FolderTreeSelect.svelte';
	import { defaults, superForm } from 'sveltekit-superforms';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { z } from 'zod';

	interface Props {
		parent: any;
		model: string;
		properties: Record<string, { value: string }[]>;
		onSaved: (entry: any, scope: 'personal' | 'shared') => void;
	}

	let { parent, model, properties, onSaved }: Props = $props();

	let scope = $state<'personal' | 'shared'>('personal');
	let selectedDomain = $state('');

	// Standalone SPA form backing the hierarchical domain picker (FolderTreeSelect
	// requires a SuperForm); we mirror its value into selectedDomain.
	const domainSchema = z.object({ domain: z.string() });
	const domainForm = superForm(defaults({ domain: '' }, zod(domainSchema)), {
		dataType: 'json',
		taintedMessage: false,
		validators: zod(domainSchema),
		SPA: true
	});
	const unsubscribeDomain = domainForm.form.subscribe((v) => {
		selectedDomain = v.domain ?? '';
	});
	onDestroy(unsubscribeDomain);

	const canSubmit = $derived(scope !== 'shared' || !!selectedDomain);

	async function handleSubmit(name: string) {
		const endpoint =
			scope === 'personal' ? '/fe-api/saved-filters/personal/' : '/fe-api/saved-filters/';
		const body =
			scope === 'personal'
				? { name, model, properties }
				: { name, model, properties, folder: selectedDomain };
		const res = await fetch(endpoint, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(body)
		});
		const data = await res.json();
		if (!res.ok) {
			throw new Error(typeof data === 'string' ? data : JSON.stringify(data));
		}
		onSaved(data, scope);
	}
</script>

<FilterNameModal {parent} {canSubmit} onSubmit={handleSubmit}>
	{#snippet extraFields()}
		<div class="space-y-1">
			<span class="block text-sm font-semibold">{m.scope()}</span>
			<div class="flex gap-4">
				<label class="flex items-center gap-2">
					<input type="radio" name="save-filter-scope" value="personal" bind:group={scope} />
					{m.personalFilters()}
				</label>
				<label class="flex items-center gap-2">
					<input type="radio" name="save-filter-scope" value="shared" bind:group={scope} />
					{m.sharedFilters()}
				</label>
			</div>
		</div>

		{#if scope === 'shared'}
			<FolderTreeSelect
				form={domainForm}
				field="domain"
				label={m.domain()}
				writePermission="add_savedfilter"
			/>
		{/if}
	{/snippet}
</FilterNameModal>
