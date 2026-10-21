<script lang="ts">
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { getToastStore } from '$lib/components/Toast/stores';
	import { getModalStore, type ModalStore } from '$lib/components/Modals/stores';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const modalStore: ModalStore = getModalStore();
	const toastStore = getToastStore();
	const isAdmin = Boolean(page.data.user?.is_admin);

	let busy = $state(false);

	async function extractErrorMessage(res: Response): Promise<string> {
		try {
			const body = await res.json();
			const raw = body?.error ?? body?.message?.error ?? body?.detail;
			const key = Array.isArray(raw) ? raw[0] : raw;
			if (typeof key === 'string' && key) return safeTranslate(key);
		} catch {
			/* fall through to the generic message */
		}
		return m.anErrorOccurred();
	}

	function modalConfirmDelete(): void {
		modalStore.trigger({
			type: 'confirm',
			title: m.deleteModalTitle(),
			body: `${m.deleteModalMessage({ name: data.data.name })}`,
			response: async (confirmed: boolean) => {
				if (!confirmed) return;
				busy = true;
				try {
					const res = await fetch(`/identity-providers/${data.data.id}`, { method: 'DELETE' });
					if (res.ok) {
						await goto('/identity-providers', { invalidateAll: true });
					} else {
						toastStore.trigger({ message: await extractErrorMessage(res), preset: 'error' });
					}
				} catch {
					toastStore.trigger({ message: m.anErrorOccurred(), preset: 'error' });
				}
				busy = false;
			}
		});
	}
</script>

<DetailView {data}>
	{#snippet actions()}
		{#if isAdmin}
			<Anchor
				breadcrumbAction="push"
				href={`${page.url.pathname}/edit?next=${page.url.pathname}`}
				label={m.edit()}
				class="btn preset-filled-primary-500 h-fit"
				><i class="fa-solid fa-pen-to-square mr-2" data-testid="edit-button"></i>{m.edit()}</Anchor
			>
			<button
				class="btn preset-filled-error-500 h-fit"
				data-testid="delete-button"
				disabled={busy}
				onclick={modalConfirmDelete}><i class="fa-solid fa-trash mr-2"></i>{m.delete()}</button
			>
		{/if}
	{/snippet}
</DetailView>
