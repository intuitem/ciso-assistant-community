<script lang="ts">
	import { copy } from '@svelte-put/copy';
	import SuperForm from '#lib/components/Forms/Form.svelte';
	import { superForm } from 'sveltekit-superforms';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import type { PageData } from './$types';
	import TextField from '#lib/components/Forms/TextField.svelte';
	import Checkbox from '#lib/components/Forms/Checkbox.svelte';
	import FieldMapper from '#lib/components/Forms/FieldMapper.svelte';
	import { ASSET_LOCAL_FIELDS } from '#lib/components/Forms/integrationModels.js';
	import { schema } from './schema';
	import { m } from '#paraglide/messages.js';
	import { page } from '$app/state';
	import LoadingSpinner from '#lib/components/utils/LoadingSpinner.svelte';
	import { describeTestFailure } from '#lib/utils/integration-test.js';

	let { data }: { data: PageData } = $props();

	const invalidateAll = true;
	const formAction = '?/save';

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

	// Both directions talk to GLPI: incoming sync reads the item back after a
	// webhook, so the connection is needed even with outgoing sync off.
	const connectionInUse = $derived(
		$formStore.is_active &&
			($formStore.settings.enable_outgoing_sync || $formStore.settings.enable_incoming_sync)
	);

	// The OAuth client secret and the user password are stored together, so one
	// flag covers both.
	let showSecretFields = $state(!data?.config?.has_api_token);
	let showWebhookSecretField = $state(!data?.config?.has_webhook_secret);
	let testConnectionState: { loading: boolean; success?: boolean; detail?: string } = $state({
		loading: false,
		success: undefined
	});
	let latestTest = 0;

	async function testConnection() {
		// Only the latest test may report: a slow earlier one must not replace
		// the result of a newer one.
		const test = ++latestTest;
		testConnectionState = { loading: true };
		let result: { success: boolean; detail?: string };
		try {
			const response = await fetch('/settings/integrations/test-connection', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					credentials: {
						instance_url: $formStore.credentials.instance_url,
						client_id: $formStore.credentials.client_id,
						client_secret: $formStore.credentials.client_secret,
						username: $formStore.credentials.username,
						password: $formStore.credentials.password
					},
					provider: page.data.provider,
					configuration_id: page.data?.config?.id
				})
			});
			result = {
				success: response.ok,
				detail: response.ok ? '' : await describeTestFailure(response)
			};
		} catch {
			// The request itself failed: show a failure instead of spinning forever.
			result = { success: false };
		}
		if (test === latestTest) {
			testConnectionState = { loading: false, ...result };
		}
	}
</script>

{#key page.data}
	<div class="flex flex-col gap-8">
		<SuperForm
			class="flex flex-col space-y-3"
			action={formAction}
			dataType="json"
			enctype="application/x-www-form-urlencoded"
			data={data.form}
			{_form}
			{invalidateAll}
			validators={zod(schema)}
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
						helpText={m.glpiInstanceUrlHelpText()}
						disabled={!connectionInUse}
					/>
					<TextField
						{form}
						field="client_id"
						valuePath="credentials.client_id"
						autocomplete="off"
						label={m.clientId()}
						helpText={m.glpiClientIdHelpText()}
						disabled={!connectionInUse}
					/>
					<TextField
						{form}
						field="username"
						valuePath="credentials.username"
						autocomplete="new-password"
						label={m.username()}
						helpText={m.glpiUsernameHelpText()}
						disabled={!connectionInUse}
					/>
					{#if showSecretFields}
						<TextField
							{form}
							field="client_secret"
							type="password"
							valuePath="credentials.client_secret"
							autocomplete="new-password"
							label={m.clientSecret()}
							disabled={!connectionInUse}
						/>
						<TextField
							{form}
							field="password"
							type="password"
							valuePath="credentials.password"
							autocomplete="new-password"
							label={m.password()}
							disabled={!connectionInUse}
						/>
					{:else}
						<p class="font-semibold text-sm -mb-4">{m.clientSecret()} / {m.password()}</p>
						<div
							class="w-full p-4 flex flex-row justify-evenly items-center preset-tonal-secondary"
						>
							<p>{m.glpiSecretsAlreadySetHelpText()}</p>
							<button
								type="button"
								disabled={!connectionInUse}
								class="btn preset-filled"
								onclick={() => {
									showSecretFields = true;
									$formStore.credentials.client_secret = '';
									$formStore.credentials.password = '';
								}}
								>{m.glpiResetSecrets()}
							</button>
						</div>
					{/if}
					<span class="flex flex-row justify-between gap-4">
						<button
							disabled={!connectionInUse}
							type="button"
							class="btn preset-filled-secondary-500"
							onclick={testConnection}>{m.testConnection()}</button
						>
						<div class="flex items-center">
							{#if testConnectionState.loading}
								<LoadingSpinner />
							{:else if testConnectionState.success === true}
								<span class="text-success-700-300 font-semibold">{m.connectionSuccessful()}</span>
							{:else if testConnectionState.success === false}
								<span class="text-error-500 font-semibold"
									>{m.connectionFailed()}{testConnectionState.detail
										? `: ${testConnectionState.detail}`
										: ''}</span
								>
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
							autocomplete="new-password"
							label={m.webhookSecret()}
							helpText={m.glpiWebhookSecretHelpText()}
							disabled={!$formStore.is_active || !$formStore.settings.enable_incoming_sync}
						/>
					{:else}
						<p class="font-semibold text-sm -mb-4">{m.webhookSecret()}</p>
						<div
							class="text-center w-full p-4 flex flex-row justify-evenly items-center preset-tonal-secondary"
						>
							<p>{m.webhookSecretAlreadySetHelpText()}</p>
							<button
								type="button"
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
				{#if page.data?.config?.id || $formStore.id}
					<FieldMapper
						{form}
						integrationId={page.data?.config?.id || $formStore.id}
						initialConfig={page.data?.config?.settings}
						description={m.glpiIntegrationMappingsHelpText()}
						remoteFieldLabel={m.glpiField()}
						tableHelpText={m.glpiTableHelpText()}
					/>
					<FieldMapper
						{form}
						integrationId={page.data?.config?.id || $formStore.id}
						modelKey="asset"
						valuePathPrefix="settings.models.asset"
						localFields={ASSET_LOCAL_FIELDS}
						initialConfig={page.data?.config?.settings?.models?.asset}
						title={m.assets()}
						description={m.glpiAssetMappingsHelpText()}
						remoteFieldLabel={m.glpiField()}
						tableHelpText={m.glpiAssetTableHelpText()}
					/>
				{/if}
				<button
					class="text-center btn preset-filled-primary-500 font-semibold w-full"
					data-testid="save-button">{m.save()}</button
				>
			{/snippet}
		</SuperForm>
	</div>
{/key}
