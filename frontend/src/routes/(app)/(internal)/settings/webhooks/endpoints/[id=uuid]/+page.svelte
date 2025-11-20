<script lang="ts">
	import type { PageData } from './$types';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import { m } from '$paraglide/messages';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import MarkdownField from '$lib/components/Forms/MarkdownField.svelte';
	import { zod } from 'sveltekit-superforms/adapters';
	import { webhookEndpointSchema } from '$lib/utils/schemas';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import EventTypesSelect from '../EventTypesSelect.svelte';
	import { onMount } from 'svelte';
	import { getSecureRedirect } from '$lib/utils/helpers';
	import { goto } from '$lib/utils/breadcrumbs';
	import { page } from '$app/state';
	import WebhookSecretGenerator from '$lib/components/Forms/WebhookSecretGenerator.svelte';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import { SHOW_TARGET_DOMAINS } from '../constants';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const formStore = data.form?.form;

	let showSecretField = $state(!data.webhookEndpoint?.has_secret);

	let eventTypeOptions = $state([]);

	function cancel(): void {
		const nextValue = getSecureRedirect(page.url.searchParams.get('next'));
		if (nextValue) goto(nextValue);
	}

	onMount(async () => {
		eventTypeOptions = await fetch('/settings/webhooks/event-types').then((res) => res.json());
	});
</script>

<SuperForm
	class="flex flex-col space-y-3"
	data={data?.form}
	dataType="form"
	validators={zod(webhookEndpointSchema)}
>
	{#snippet children({ form })}
		<Checkbox {form} field="is_active" label={m.isActive()} />
		<TextField {form} field="name" label={m.name()} data-focusindex="0" />
		<MarkdownField {form} field="description" label={m.description()} data-focusindex="1" />
		<TextField {form} field="url" label={m.url()} data-focusindex="2" />
		{#if showSecretField}
			<WebhookSecretGenerator {form} field="secret" />
		{:else}
			<div class="w-full p-4 flex flex-row justify-evenly items-center preset-tonal-secondary">
				<p>{m.secretAlreadySetHelpText()}</p>
				<button
					class="btn preset-filled"
					onclick={() => {
						showSecretField = true;
						$formStore.secret = '';
					}}>{m.resetSecret()}</button
				>
			</div>
		{/if}
		{#if SHOW_TARGET_DOMAINS}
			<AutocompleteSelect
				{form}
				field="target_folders"
				label={m.targetDomains()}
				helpText={m.webhookEndpointTargetDomainsHelpText()}
				optionsEndpoint="folders?content_type=DO&content_type=GL"
				multiple
			/>
		{/if}

		<EventTypesSelect {form} field="event_types" label={m.events()} options={eventTypeOptions} />
		<div class="flex flex-row justify-between space-x-4">
			<button class="btn bg-gray-400 text-white font-semibold w-full" type="button" onclick={cancel}
				>{m.cancel()}</button
			>
			<button
				class="btn preset-filled-primary-500 font-semibold w-full"
				data-testid="login-btn"
				type="submit">{m.save()}</button
			>
		</div>
	{/snippet}
</SuperForm>
