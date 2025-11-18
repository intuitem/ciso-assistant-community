<script lang="ts">
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import Form from '$lib/components/Forms/Form.svelte';
	import MarkdownField from '$lib/components/Forms/MarkdownField.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import WebhookSecretGenerator from '$lib/components/Forms/WebhookSecretGenerator.svelte';
	import { getModalStore, type ModalStore } from '$lib/components/Modals/stores';
	import { webhookEndpointSchema } from '$lib/utils/schemas';
	import { m } from '$paraglide/messages';
	import { onMount, tick } from 'svelte';
	import type { SuperForm } from 'sveltekit-superforms';
	import { zod } from 'sveltekit-superforms/adapters';
	import { superForm } from 'sveltekit-superforms/client';
	import EventTypesSelect from './EventTypesSelect.svelte';

	// Base Classes
	const cBase = 'card bg-surface-50 p-4 shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';

	interface Props {
		/** Exposes parent props to this component. */
		parent: any;
		form: SuperForm<any>;
		formAction?: string;
		debug?: boolean;
		[key: string]: any;
	}

	const modalStore: ModalStore = getModalStore();

	let { parent, form, formAction = '?/createWebhookEndpoint' }: Props = $props();

	let eventTypeOptions = $state([]);

	// Focus the first field when modal opens
	onMount(async () => {
		await tick(); // Wait for DOM to render
		const firstField = document.querySelector('input[data-focusindex="0"]');
		if (firstField instanceof HTMLElement) {
			firstField.focus();
		}
		eventTypeOptions = await fetch('/settings/webhooks/event-types').then((res) => res.json());
	});

	const _form = superForm(form, {
		dataType: 'json',
		validators: zod(webhookEndpointSchema),
		validationMethod: 'onsubmit',
		onUpdated: async ({ form }) => {
			if (form.valid && parent && typeof parent.onConfirm === 'function') {
				parent.onConfirm();
			}
		}
	});
</script>

{#if $modalStore[0]}
	<div class="w-2xl {cBase}">
		<div class="flex items-center justify-between">
			<header class={cHeader} data-testid="modal-title">
				{$modalStore[0].title ?? '(title missing)'}
			</header>
			<div
				role="button"
				tabindex="0"
				class="flex items-center hover:text-primary-500 cursor-pointer"
				onclick={parent.onClose}
				onkeydown={parent.onClose}
			>
				<i class="fa-solid fa-xmark"></i>
			</div>
		</div>
		<Form
			class="flex flex-col space-y-3"
			{_form}
			data={form}
			dataType="json"
			validators={zod(webhookEndpointSchema)}
			action={formAction}
		>
			{#snippet children({ form })}
				<Checkbox {form} field="is_active" label={m.isActive()} checked />
				<TextField {form} field="name" label={m.name()} data-focusindex="0" />
				<MarkdownField {form} field="description" label={m.description()} data-focusindex="1" />
				<TextField {form} field="url" label={m.url()} data-focusindex="2" autocomplete="off" />
				<WebhookSecretGenerator {form} field="secret" />
				<EventTypesSelect
					{form}
					field="event_types"
					label={m.events()}
					options={eventTypeOptions}
				/>
				<div class="flex flex-row justify-between space-x-4">
					<button
						class="btn bg-gray-400 text-white font-semibold w-full"
						data-testid="cancel-button"
						type="button"
						onclick={(event) => {
							parent.onClose(event);
						}}>{m.cancel()}</button
					>
					<button
						class="btn preset-filled-primary-500 font-semibold w-full"
						data-testid="login-btn"
						type="submit">{m.save()}</button
					>
				</div>
			{/snippet}
		</Form>
	</div>
{/if}
