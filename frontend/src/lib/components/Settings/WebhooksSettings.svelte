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
	import { zod } from 'sveltekit-superforms/adapters';
	import { modelEventsMap } from '$lib/utils/webhooks';
	import { safeTranslate } from '$lib/utils/i18n';
	import z from 'zod';

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
	<div class="flex flex-col gap-3">
		<span class="text-gray-500">{m.configureOutgoingWebhooks()}</span>
		<span class="flex flex-row justify-between">
			<h3 class="h3">{allowMultiple ? m.webhookEndpoints() : m.webhookEndpoint()}</h3>
			{#if data?.webhookEndpoints?.length == 0 || allowMultiple}
				<button class="btn preset-filled-primary-500 w-fit" onclick={modalWebhookEndpointCreateForm}
					><i class="fa-solid fa-plus mr-2"></i>{m.createWebhookEndpoint()}</button
				>
			{/if}
		</span>
		{#if displayedEndpoint}
			<div class="grid grid-cols-1 gap-4 lg:grid-cols-3 lg:gap-8">
				{#if allowMultiple}
					<div class="card p-2 bg-surface-50-950">
						{#each data.webhookEndpoints as endpoint}
							<span class="flex flex-row gap-4 items-center">
								<button
									onclick={() => {
										displayedEndpoint = endpoint;
									}}
									class="text-secondary-600 hover:underline {JSON.stringify(displayedEndpoint) ===
									JSON.stringify(endpoint)
										? 'font-semibold'
										: ''}"
								>
									{endpoint.name}</button
								>
								{#if endpoint.is_active}
									<span class="badge preset-tonal-success">{m.active()}</span>
								{/if}
							</span>
						{/each}
					</div>
				{/if}
				<div class="card p-2 lg:col-span-2">
					<div class="flex flex-col gap-4">
						<span class="flex flex-row gap-2 items-center">
							<h4 class="h4">
								{displayedEndpoint.name}
							</h4>
							{#if displayedEndpoint.is_active}
								<span class="badge preset-tonal-success">{m.active()}</span>
							{/if}
						</span>
						<a class="anchor" href={displayedEndpoint.url}>
							{displayedEndpoint.url}
						</a>
						<div>
							<p class="font-medium">{m.events()}</p>
							{#each Object.values(modelEventsMap(displayedEndpoint.event_types)).filter((e: Record) => e?.events?.length > 0) as model}
								<div class="flex flex-col gap-3">
									<span class="flex flex-row gap-3">
										<p class="font-medium">{safeTranslate(model.i18nName)}</p>
										<span class="flex flex-row gap-2">
											{#each model.events as event}
												{@const action = event.split('.')[1]}
												<p>{safeTranslate(action)}</p>
											{/each}
										</span>
									</span>
								</div>
							{/each}
						</div>
						<span class="flex flex-row gap-2">
							<Anchor
								class="btn preset-filled-primary-500 h-fit"
								href="/settings/webhooks/endpoints/{displayedEndpoint.id}?next={page.url.pathname}"
								><i class="fa-solid fa-pen-to-square mr-2"></i>{m.edit()}</Anchor
							>
							<button
								aria-label={m.delete()}
								onclick={(e) => {
									modalConfirmDelete(displayedEndpoint.id, displayedEndpoint);
									e.stopPropagation();
								}}
								class="btn preset-filled-error-500 h-fit cursor-pointer"
								data-testid="tablerow-delete-button"
								><i class="fa-solid fa-trash mr-2"></i>{m.delete()}</button
							>
						</span>
					</div>
				</div>
			</div>
		{/if}
	</div>
{/if}
