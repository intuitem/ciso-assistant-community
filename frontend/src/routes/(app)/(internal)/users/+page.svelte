<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { Tabs } from '@skeletonlabs/skeleton-svelte';

	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import CreateServiceAccountModal from '$lib/components/Forms/ModelForm/ServiceAccountForm.svelte';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const modalStore: ModalStore = getModalStore();

	// Use page.data to access layout-provided user info
	const user = $derived(page.data.user);

	// ── Tab state (persisted in URL) ─────────────────────────────────────
	let tab = $state(page.url.searchParams.get('tab') ?? 'users');

	function switchTab(value: string) {
		tab = value;
		const url = new URL(page.url);
		if (value === 'users') {
			url.searchParams.delete('tab');
		} else {
			url.searchParams.set('tab', value);
		}
		goto(url.toString(), { replaceState: true, noScroll: true, keepFocus: true });
	}

	// ── User modals ────────────────────────────────────────────────────────
	function modalCreateUser() {
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: { form: data.createForm, model: data.model }
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: safeTranslate('add-' + data.model.localName)
		};
		modalStore.trigger(modal);
	}

	// ── SA modals ──────────────────────────────────────────────────────────
	function openCreateSAModal() {
		const modalComponent: ModalComponent = {
			ref: CreateServiceAccountModal,
			props: { form: data.createSAForm, formAction: '?/createSA' }
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.createServiceAccount()
		};
		modalStore.trigger(modal);
	}
</script>

<Tabs value={tab} onValueChange={(e) => switchTab(e.value)}>
	<Tabs.List>
		<Tabs.Trigger value="users">
			<i class="fa-solid fa-user mr-2"></i>{m.users()}
		</Tabs.Trigger>
		{#if user?.is_admin}
			<Tabs.Trigger value="service-accounts">
				<i class="fa-solid fa-robot mr-2"></i>{m.serviceAccounts()}
			</Tabs.Trigger>
		{/if}
		<Tabs.Indicator />
	</Tabs.List>

	<!-- ── Users tab ─────────────────────────────────────────────── -->
	<Tabs.Content value="users">
		{#if data.table}
			<div class="shadow-lg">
				<ModelTable
					source={data.table}
					deleteForm={data.deleteForm}
					URLModel="users"
					baseEndpoint="/users?is_service_account=false"
				>
					{#snippet addButton()}
						<div class="inline-flex overflow-hidden rounded-md border bg-white shadow-xs">
							<button
								class="inline-block p-3 btn-mini-primary w-12 focus:relative"
								data-testid="add-button"
								title={safeTranslate('add-' + data.model.localName)}
								aria-label={safeTranslate('add-' + data.model.localName)}
								onclick={modalCreateUser}
							>
								<i class="fa-solid fa-file-circle-plus"></i>
							</button>
						</div>
					{/snippet}
				</ModelTable>
			</div>
		{/if}
	</Tabs.Content>

	<!-- ── Service accounts tab ──────────────────────────────────── -->
	{#if user?.is_admin}
		<Tabs.Content value="service-accounts">
			<div class="shadow-lg">
				<ModelTable
					source={data.saTable ?? { head: {}, body: [], meta: [] }}
					URLModel="users"
					deleteForm={data.deleteForm}
					baseEndpoint="/service-accounts"
				>
					{#snippet addButton()}
						<div class="inline-flex overflow-hidden rounded-md border bg-white shadow-xs">
							<button
								class="inline-block p-3 btn-mini-primary w-12 focus:relative"
								data-testid="add-sa-button"
								title={m.createServiceAccount()}
								aria-label={m.createServiceAccount()}
								onclick={openCreateSAModal}
							>
								<i class="fa-solid fa-file-circle-plus"></i>
							</button>
						</div>
					{/snippet}
				</ModelTable>
			</div>
		</Tabs.Content>
	{/if}
</Tabs>
