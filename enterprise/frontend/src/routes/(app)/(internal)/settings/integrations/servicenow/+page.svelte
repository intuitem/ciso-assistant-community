<script lang="ts">
	import { copy } from '@svelte-put/copy';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import { superForm } from 'sveltekit-superforms';
	import { zod } from 'sveltekit-superforms/adapters';
	import type { ActionData, PageData } from './$types';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import FieldMapper from '$lib/components/Forms/FieldMapper.svelte';
	import { z } from 'zod';
	import { m } from '$paraglide/messages';
	import { page } from '$app/state';
	import LoadingSpinner from '$lib/components/utils/LoadingSpinner.svelte';

	interface Props {
		data: PageData;
		form: ActionData;
		[key: string]: any;
	}

	let { data, form }: Props = $props();

	const invalidateAll = true;
	const formAction = '?/save';

	const schema = z.object({
		id: z.string(),
		provider_id: z.string(),
		folder_id: z.string(),
		is_active: z.boolean().default(true),
		webhook_secret: z.string().optional(),
		credentials: z.object({
			instance_url: z.string().url(),
			username: z.string(),
			password: z.string().optional()
		}),
		settings: z.object({
			enable_outgoing_sync: z.boolean().default(false),
			enable_incoming_sync: z.boolean().default(false),
			table_name: z.string(),
      field_map: z.record(z.string(), z.any())
                  .default({})
                  .optional(),
      value_map: z.record(z.string(), z.any())
                  .default({})
                  .optional()
    })
	});

	const _form = superForm(data.form, {
		dataType: 'json',
		invalidateAll,
		applyAction: true,
		resetForm: false,
		validators: zod(schema),
		taintedMessage: true,
		validationMethod: 'auto'
	});

	const formStore = _form.form;

	let showApiTokenField = $state(!data?.config?.has_password);
	let showWebhookSecretField = $state(!data?.config?.has_webhook_secret);
	let testConnectionState: { loading: boolean; success?: boolean } = $state({
		loading: false,
		success: undefined
	});
</script>

{#key page.data}
	<div class="flex flex-col gap-8">
		<SuperForm
			class="flex flex-col space-y-3"
			action={formAction}
			dataType={'json'}
			enctype={'application/x-www-form-urlencoded'}
			data={data.form}
			{_form}
			{invalidateAll}
			validators={zod(schema)}
      debug
		>
			{#snippet children({ form })}
				<Checkbox {form} field="is_active" label={m.active()} />
				<div class="flex flex-col gap-4 card preset-outlined-surface-200-800 p-2">
					<span class="flex flex-row justify-between items-center">
						<h4 class="h4">{m.outgoingSync()}</h4>
						<Checkbox
							{form}
							field="enable_outgoing_sync"
							valuePath="settings.enable_outgoing_sync"
							label=""
							disabled={!$formStore.is_active}
						/>
					</span>
					<TextField
						{form}
						field="instance_url"
						valuePath="credentials.instance_url"
						label={m.instanceUrl()}
						helpText={m.serviceNowInstanceUrlHelpText()}
						disabled={!$formStore.is_active || !$formStore.settings.enable_outgoing_sync}
					/>
					<TextField
						{form}
						field="username"
						valuePath="credentials.username"
						autocomplete="new-password"
						label={m.username()}
						helpText={m.serviceNowUsernameHelpText()}
						disabled={!$formStore.is_active || !$formStore.settings.enable_outgoing_sync}
					/>
					{#if showApiTokenField}
						<TextField
							{form}
							field="password"
							type="password"
							valuePath="credentials.password"
							autocomplete="new-password"
							label={m.password()}
							disabled={!$formStore.is_active || !$formStore.settings.enable_outgoing_sync}
						/>
					{:else}
						<p class="font-semibold text-sm -mb-4">{m.password()}</p>
						<div
							class="w-full p-4 flex flex-row justify-evenly items-center preset-tonal-secondary"
						>
							<p>{m.passwordAlreadySetHelpText()}</p>
							<button
								disabled={!$formStore.is_active || !$formStore.settings.enable_outgoing_sync}
								class="btn preset-filled"
								onclick={() => {
									showApiTokenField = true;
									$formStore.credentials.password = '';
								}}
								>{m.resetPassword()}
							</button>
						</div>
					{/if}
					<span class="flex flex-row justify-between gap-4">
						<button
							disabled={!$formStore.is_active || !$formStore.settings.enable_outgoing_sync}
							type="button"
							class="btn preset-filled-secondary-500"
							onclick={async () => {
								testConnectionState = { loading: true, success: false };
								const response = await fetch('/settings/integrations/test-connection', {
									method: 'POST',
									headers: {
										'Content-Type': 'application/json'
									},
									body: JSON.stringify({
										credentials: {
											instance_url: $formStore.credentials.instance_url,
											username: $formStore.credentials.username,
											password: $formStore.credentials.password
										},
										provider: page.data.provider,
										configuration_id: page.data?.config?.id
									})
								});
								testConnectionState = { loading: false, success: response.ok };
							}}>{m.testConnection()}</button
						>
						<div class="flex items-center">
							{#if testConnectionState.loading}
								<LoadingSpinner />
							{:else if testConnectionState.success === true}
								<span class="text-success-700 font-semibold">{m.connectionSuccessful()}</span>
							{:else if testConnectionState.success === false}
								<span class="text-error-500 font-semibold">{m.connectionFailed()}</span>
							{/if}
						</div>
					</span>
				</div>
				<div class="flex flex-col gap-4 card preset-outlined-surface-200-800 p-2">
					<span class="flex flex-row justify-between items-center">
						<h4 class="h4">{m.incomingSync()}</h4>
						<Checkbox
							{form}
							field="enable_incoming_sync"
							valuePath="settings.enable_incoming_sync"
							label=""
							disabled={!$formStore.is_active}
						/>
					</span>
					{#if showWebhookSecretField}
						<TextField
							{form}
							field="webhook_secret"
							type="password"
							label={m.webhookSecret()}
							disabled={!$formStore.is_active || !$formStore.settings.enable_incoming_sync}
						/>
					{:else}
						<p class="font-semibold text-sm -mb-4">{m.webhookSecret()}</p>
						<div
							class="text-center w-full p-4 flex flex-row justify-evenly items-center preset-tonal-secondary"
						>
							<p>{m.webhookSecretAlreadySetHelpText()}</p>
							<button
								disabled={!$formStore.is_active || !$formStore.settings.enable_incoming_sync}
								class="btn preset-filled"
								onclick={() => {
									showWebhookSecretField = true;
									$formStore.webhook_secret = '';
								}}>{m.resetWebhookSecret()}</button
							>
						</div>
					{/if}
				</div>
				{#if page.data?.config?.webhook_url_full}
					<p class="font-semibold text-sm -mb-1">{m.webhookEndpointUrl()}</p>
					<span
						class="flex flex-row justify-between gap-2 preset-tonal-secondary items-center card pl-2 text-xs"
					>
						<pre>&lt;API_HOST&gt;{page.data?.config?.webhook_url_full}</pre>
						<button
							type="button"
							class="btn px-2 py-1 preset-tonal-secondary rounded-l-none"
							use:copy={{ text: page.data?.config?.webhook_url_full }}
							><i class="fa-solid fa-copy mr-2"></i>{m.copy()}</button
						>
					</span>
					<p class="text-sm text-surface-500 -mt-3">{m.webhookEndpointUrlHelpText()}</p>
				{/if}
        <FieldMapper {form} integrationId={page.data?.config?.id} />
				<button
					class="text-center btn preset-filled-primary-500 font-semibold w-full"
					data-testid="save-button">{m.save()}</button
				>
			{/snippet}
		</SuperForm>
	</div>
{/key}
