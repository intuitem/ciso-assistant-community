<script lang="ts">
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import ServiceAccountSecretModal from '$lib/components/Modals/ServiceAccountSecretModal.svelte';
	import { m } from '$paraglide/messages';
	import { page } from '$app/state';
	import { goto, invalidateAll } from '$app/navigation';
	import { getToastStore } from '$lib/components/Toast/stores';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const modalStore: ModalStore = getModalStore();
	const toastStore = getToastStore();
	const isAdmin = Boolean(page.data.user?.is_admin);

	let busy = $state(false);

	function modalSecret(payload: { client_id: string; client_secret: string }): void {
		const modalComponent: ModalComponent = {
			ref: ServiceAccountSecretModal,
			props: {
				clientId: payload.client_id,
				clientSecret: payload.client_secret
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.clientSecret()
		};
		modalStore.trigger(modal);
	}

	function modalRotateSecret(): void {
		modalStore.trigger({
			type: 'confirm',
			title: m.rotateSecret(),
			body: m.rotateSecretConfirm(),
			response: async (confirmed: boolean) => {
				if (!confirmed) return;
				busy = true;
				try {
					const res = await fetch(`/service-accounts/${data.data.id}/rotate-secret`, {
						method: 'POST'
					});
					if (res.ok) {
						const result = await res.json();
						setTimeout(() => modalSecret(result), 0);
					} else {
						toastStore.trigger({ message: m.anErrorOccurred(), preset: 'error' });
					}
				} catch {
					toastStore.trigger({ message: m.anErrorOccurred(), preset: 'error' });
				}
				busy = false;
			}
		});
	}

	async function setActive(isActive: boolean): Promise<void> {
		busy = true;
		try {
			const res = await fetch(`/service-accounts/${data.data.id}`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ is_active: isActive })
			});
			if (res.ok) {
				await invalidateAll();
			} else {
				toastStore.trigger({ message: m.anErrorOccurred(), preset: 'error' });
			}
		} catch {
			toastStore.trigger({ message: m.anErrorOccurred(), preset: 'error' });
		}
		busy = false;
	}

	function toggleActive(): void {
		if (data.data.is_active) {
			modalStore.trigger({
				type: 'confirm',
				title: m.deactivate(),
				body: m.deactivateServiceAccountConfirm(),
				response: async (confirmed: boolean) => {
					if (!confirmed) return;
					await setActive(false);
				}
			});
		} else {
			setActive(true);
		}
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
					const res = await fetch(`/service-accounts/${data.data.id}`, { method: 'DELETE' });
					if (res.ok) {
						await goto('/service-accounts', { invalidateAll: true });
					} else {
						toastStore.trigger({ message: m.anErrorOccurred(), preset: 'error' });
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
				class="btn preset-filled-secondary-500 h-fit"
				data-testid="toggle-active-button"
				disabled={busy}
				onclick={toggleActive}
			>
				{#if data.data.is_active}
					<i class="fa-solid fa-ban mr-2"></i>{m.deactivate()}
				{:else}
					<i class="fa-solid fa-check mr-2"></i>{m.activate()}
				{/if}
			</button>
			<button
				class="btn preset-filled-tertiary-500 h-fit"
				data-testid="rotate-secret-button"
				disabled={busy}
				onclick={modalRotateSecret}
				><i class="fa-solid fa-arrows-rotate mr-2"></i>{m.rotateSecret()}</button
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

{#if data.data.permissions?.length}
	<div class="card px-6 py-4 bg-surface-50-950 shadow-lg mt-4 space-y-2">
		<h4 class="h4 font-semibold">{m.permissions()}</h4>
		<div class="flex flex-wrap gap-2">
			{#each data.data.permissions as permission}
				<span class="badge preset-tonal-primary">{permission.app_label}: {permission.codename}</span
				>
			{/each}
		</div>
	</div>
{/if}
