<script lang="ts">
	import { m } from '$paraglide/messages';
	import { onDestroy } from 'svelte';
	import FilterNameModal from './FilterNameModal.svelte';
	import FolderTreeSelect from '$lib/components/Forms/FolderTreeSelect.svelte';
	import { hasPermissionAnywhere } from '$lib/utils/access-control';
	import type { User } from '$lib/utils/types';
	import { defaults, superForm } from 'sveltekit-superforms';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { z } from 'zod';

	interface Props {
		parent: any;
		user?: User;
		initialName: string;
		// fields to share a personal filter to a domain
		filterId?: string;
		model?: string;
		properties?: Record<string, { value: string }[]>;
		// Present when editing an existing shared filter -- shows a persistent
		// domain field (instead of the opt-in "share" toggle) letting it be
		// moved to a different domain.
		currentDomainId?: string;
		onRenamed: (name: string, domain?: string) => void | Promise<void>;
		// Sharing supersedes the personal filter -- it is deleted once its
		// shared counterpart is created, not linked to it.
		onShared?: (result: { shared: any; deletedPersonalId: string }) => void;
	}

	let {
		parent,
		user,
		initialName,
		filterId,
		model,
		properties,
		currentDomainId,
		onRenamed,
		onShared
	}: Props = $props();

	const canShare = !!(
		filterId &&
		model &&
		onShared &&
		user &&
		hasPermissionAnywhere(user, 'add_savedfilter')
	);
	const showDomainField = !!currentDomainId;

	// Activate the sharing saved filter. When enabled, the user can choose a domain that the filter will be saved to when the modifications are saved.
	let shareEnabled = $state(false);
	let selectedDomain = $state('');

	// Standalone SPA form backing the hierarchical domain picker (FolderTreeSelect
	// requires a SuperForm); we mirror its value into selectedDomain.
	const domainSchema = z.object({ domain: z.string() });
	const domainForm = superForm(defaults({ domain: currentDomainId ?? '' }, zod(domainSchema)), {
		dataType: 'json',
		taintedMessage: false,
		validators: zod(domainSchema),
		SPA: true
	});
	const unsubscribeDomain = domainForm.form.subscribe((v) => {
		selectedDomain = v.domain ?? '';
	});
	onDestroy(unsubscribeDomain);

	const canSubmit = $derived(
		showDomainField ? !!selectedDomain : !shareEnabled || !!selectedDomain
	);

	function enableShare() {
		shareEnabled = true;
	}

	function disableShare() {
		shareEnabled = false;
		domainForm.form.update(() => ({ domain: '' }));
	}

	async function handleSubmit(name: string) {
		if (showDomainField) {
			// Editing an existing shared filter -- rename and/or move it to a
			// different domain in a single PATCH, no separate create+delete step.
			await onRenamed(name, selectedDomain);
			return;
		}

		if (!shareEnabled || !selectedDomain) {
			await onRenamed(name);
			return;
		}

		// Sharing supersedes the personal filter, so the rename is skipped --
		// the personal entry is about to be deleted, the new name only applies
		// to the shared filter being created.
		const sharedRes = await fetch('/fe-api/saved-filters/', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ name, model, properties, folder: selectedDomain })
		});
		const shared = await sharedRes.json();
		if (!sharedRes.ok) {
			throw new Error(typeof shared === 'string' ? shared : JSON.stringify(shared));
		}

		const deleteRes = await fetch(`/fe-api/saved-filters/personal/${filterId}/`, {
			method: 'DELETE'
		});
		if (!deleteRes.ok && deleteRes.status !== 204) {
			throw new Error('Failed to remove the personal filter after sharing');
		}

		onShared?.({ shared, deletedPersonalId: filterId! });
	}
</script>

<FilterNameModal {parent} {initialName} {canSubmit} onSubmit={handleSubmit}>
	{#snippet extraFields()}
		{#if showDomainField}
			<FolderTreeSelect
				form={domainForm}
				field="domain"
				label={m.domain()}
				writePermission="add_savedfilter"
			/>
		{:else if canShare}
			<div class="space-y-2 pt-2 border-t border-surface-200-800">
				{#if !shareEnabled}
					<button type="button" class="btn btn-sm preset-tonal-surface" onclick={enableShare}>
						<i class="fa-solid fa-share-nodes mr-2"></i>{m.shareToDomain()}
					</button>
				{:else}
					<div class="flex items-center justify-between">
						<span class="block text-sm font-semibold">{m.shareToDomain()}</span>
						<button
							type="button"
							class="text-surface-500 hover:text-surface-700-300 text-sm"
							onclick={disableShare}
						>
							<i class="fa-solid fa-xmark"></i>
						</button>
					</div>
					<FolderTreeSelect form={domainForm} field="domain" writePermission="add_savedfilter" />
				{/if}
			</div>
		{/if}
	{/snippet}
</FilterNameModal>
