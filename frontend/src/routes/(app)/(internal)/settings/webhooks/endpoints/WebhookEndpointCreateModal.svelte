<script lang="ts">
	import type { ModelInfo } from '$lib/utils/types';
	import type { SuperForm } from 'sveltekit-superforms';
	import { onMount, tick } from 'svelte';
	import { getModalStore, type ModalStore } from '$lib/components/Modals/stores';
	import { page } from '$app/state';
	import { zod } from 'sveltekit-superforms/adapters';
	import TextField from '$lib/components/Forms/TextField.svelte';
	const modalStore: ModalStore = getModalStore();
	import Form from '$lib/components/Forms/Form.svelte';
	import { m } from '$paraglide/messages';
	import MarkdownField from '$lib/components/Forms/MarkdownField.svelte';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import { webhookEndpointSchema } from '$lib/utils/schemas';

	// Base Classes
	const cBase = 'card bg-surface-50 p-4 w-fit max-w-4xl shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';

	interface Props {
		/** Exposes parent props to this component. */
		parent: any;
		form: SuperForm<any>;
		formAction?: string;
		debug?: boolean;
		[key: string]: any;
	}

	let { parent, form, formAction = '?/createWebhookEndpoint', debug = false }: Props = $props();

	// Focus the first field when modal opens
	onMount(async () => {
		await tick(); // Wait for DOM to render
		const firstField = document.querySelector('input[data-focusindex="0"]');
		if (firstField instanceof HTMLElement) {
			firstField.focus();
		}
	});
</script>

{#if $modalStore[0]}
	<div class="modal-example-form {cBase}">
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
			data={form}
			dataType="form"
			validators={zod(webhookEndpointSchema)}
			action={formAction}
		>
			{#snippet children({ form })}
				<TextField {form} field="name" label={m.name()} data-focusindex="0" />
				<MarkdownField {form} field="description" label={m.description()} data-focusindex="1" />
				<TextField {form} field="url" label={m.url()} data-focusindex="2" />
				<TextField
					{form}
					type="password"
					field="secret"
					label={m.secret()}
					helpText={m.webhookSecretHelpText()}
				/>
				<AutocompleteSelect
					{form}
					field="event_types"
					label={m.events()}
					optionsEndpoint="settings/webhooks/event-types"
					optionsLabelField="label"
					optionsValueField="value"
					multiple
				/>
				<p class="">
					<button
						class="btn preset-filled-primary-500 font-semibold w-full"
						data-testid="login-btn"
						type="submit">{m.save()}</button
					>
				</p>
			{/snippet}
		</Form>
	</div>
{/if}
