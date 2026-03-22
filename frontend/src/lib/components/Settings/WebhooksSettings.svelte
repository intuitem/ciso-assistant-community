<script lang="ts">
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import WebhookEndpointCreateModal from '../../../routes/(app)/(internal)/settings/webhooks/endpoints/WebhookEndpointCreateModal.svelte';
	import { m } from '$paraglide/messages';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';
	import { page } from '$app/state';
	import DeleteConfirmModal from '$lib/components/Modals/DeleteConfirmModal.svelte';
	import { defaults } from 'sveltekit-superforms';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { modelEventsMap } from '$lib/utils/webhooks';
	import { safeTranslate } from '$lib/utils/i18n';
	import { z } from 'zod';

	const modalStore: ModalStore = getModalStore();

	interface Props {
		data: any;
		allowMultiple?: boolean;
	}

	let { data, allowMultiple = false }: Props = $props();

	function modalWebhookEndpointCreateForm(): void {
		const modalComponent: ModalComponent = {
			ref: WebhookEndpointCreateModal,
			props: {
				form: data.webhookEndpointCreateForm,
				formAction: '?/createWebhookEndpoint',
				invalidateAll: true
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: m.createWebhookEndpoint()
		};
		modalStore.trigger(modal);
	}

	function modalConfirmDelete(
		id: string,
		row: { [key: string]: string | number | boolean | null }
	): void {
		const modalComponent: ModalComponent = {
			ref: DeleteConfirmModal,
			props: {
				_form: defaults({ id }, zod(z.object({ id: z.string() }))),
				id: id,
				debug: false,
				URLModel: 'webhook-endpoints',
				formAction: '?/deleteWebhookEndpoint'
			}
		};
		const name = row.name;
		const body = m.deleteModalMessage({ name: name });
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: m.deleteModalTitle(),
			body: body
		};
		modalStore.trigger(modal);
	}

	let displayedEndpoint = $state(
		data?.webhookEndpoints?.length > 0 ? data.webhookEndpoints[0] : undefined
	);

	$effect(() => {
		const endpoints = data?.webhookEndpoints ?? [];

		if (!endpoints.length) {
			displayedEndpoint = undefined;
			return;
		}

		const exists = displayedEndpoint
			? endpoints.some((e: Record<string, any>) => e.id === displayedEndpoint.id)
			: false;

		if (!exists) {
			displayedEndpoint = endpoints[0];
		}
	});
</script>

{#if page.data?.featureflags?.outgoing_webhooks}
	<div class="flex flex-col gap-6">
		<span class="text-gray-500">{m.configureOutgoingWebhooks()}</span>

		<div class="flex items-center justify-between">
			<h3 class="text-base font-semibold flex items-center gap-2">
				<i class="fa-solid fa-globe text-sm text-primary-500"></i>
				{allowMultiple ? m.webhookEndpoints() : m.webhookEndpoint()}
			</h3>
			{#if data?.webhookEndpoints?.length == 0 || allowMultiple}
				<button
					class="btn btn-sm preset-filled-primary-500"
					onclick={modalWebhookEndpointCreateForm}
				>
					<i class="fa-solid fa-plus mr-1"></i>
					{m.createWebhookEndpoint()}
				</button>
			{/if}
		</div>

		{#if displayedEndpoint}
			<div class="grid grid-cols-1 gap-4 lg:grid-cols-3 lg:gap-6">
				{#if allowMultiple}
					<div class="card bg-white shadow-lg overflow-hidden">
						{#each data.webhookEndpoints as endpoint, i}
							{#if i > 0}
								<hr class="border-surface-200" />
							{/if}
							<button
								onclick={() => {
									displayedEndpoint = endpoint;
								}}
								class="flex items-center gap-3 w-full px-4 py-3 text-left hover:bg-surface-50 transition-colors {JSON.stringify(
									displayedEndpoint
								) === JSON.stringify(endpoint)
									? 'bg-surface-50 border-l-2 border-primary-500'
									: ''}"
							>
								<i class="fa-solid fa-globe text-xs text-gray-400"></i>
								<span
									class="flex-1 truncate {JSON.stringify(displayedEndpoint) ===
									JSON.stringify(endpoint)
										? 'font-semibold'
										: ''}"
								>
									{endpoint.name}
								</span>
								{#if endpoint.is_active}
									<span class="badge preset-tonal-success text-xs">{m.active()}</span>
								{/if}
							</button>
						{/each}
					</div>
				{/if}
				<div class="card bg-white shadow-lg lg:col-span-2">
					<header class="flex items-center justify-between p-4 border-b border-surface-200">
						<div class="flex items-center gap-2">
							<h4 class="h4 font-semibold">
								{displayedEndpoint.name}
							</h4>
							{#if displayedEndpoint.is_active}
								<span class="badge preset-tonal-success text-xs">{m.active()}</span>
							{/if}
						</div>
					</header>
					<div class="p-4 flex flex-col gap-4">
						<div class="flex items-center gap-2 text-sm">
							<i class="fa-solid fa-link text-xs text-gray-400"></i>
							<a class="anchor truncate" href={displayedEndpoint.url}>
								{displayedEndpoint.url}
							</a>
						</div>
						<div>
							<p class="font-medium text-sm mb-2">{m.events()}</p>
							<div class="flex flex-col gap-2">
								{#each Object.values(modelEventsMap(displayedEndpoint.event_types)).filter((e: Record) => e?.events?.length > 0) as model}
									<div class="flex items-center gap-2 text-sm">
										<span class="font-medium">{safeTranslate(model.i18nName)}</span>
										<div class="flex flex-wrap gap-1">
											{#each model.events as event}
												{@const action = event.split('.')[1]}
												<span class="badge preset-outlined-surface-500 text-xs"
													>{safeTranslate(action)}</span
												>
											{/each}
										</div>
									</div>
								{/each}
							</div>
						</div>
					</div>
					<footer class="flex items-center gap-2 p-4 border-t border-surface-200">
						<Anchor
							class="btn btn-sm preset-filled-primary-500"
							href="/settings/webhooks/endpoints/{displayedEndpoint.id}?next={page.url.pathname}"
						>
							<i class="fa-solid fa-pen-to-square mr-1 text-xs"></i>
							{m.edit()}
						</Anchor>
						<button
							aria-label={m.delete()}
							onclick={(e) => {
								modalConfirmDelete(displayedEndpoint.id, displayedEndpoint);
								e.stopPropagation();
							}}
							class="btn btn-sm preset-filled-error-500 cursor-pointer"
							data-testid="tablerow-delete-button"
						>
							<i class="fa-solid fa-trash mr-1 text-xs"></i>
							{m.delete()}
						</button>
					</footer>
				</div>
			</div>
		{/if}
	</div>
{/if}
