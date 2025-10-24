<script lang="ts">
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import { superForm } from 'sveltekit-superforms';
	import { zod } from 'sveltekit-superforms/adapters';
	import type { ActionData, PageData } from './$types';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import { z } from 'zod';
	import { m } from '$paraglide/messages';

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
		credentials: z.object({
			server_url: z.string().url(),
			email: z.string().email(),
			api_token: z.string().optional()
		}),
		settings: z.object({
			project_key: z.string(),
			issue_type: z.string().default('Task')
		})
	});

	const _form = superForm(data.form, {
		dataType: 'json',
		invalidateAll,
		applyAction: true,
		resetForm: true,
		validators: zod(schema),
		taintedMessage: true,
		validationMethod: 'auto'
	});

	const formStore = _form.form;

	let showApiTokenField = $state(!data?.config?.has_api_token);
	let showWebhookSecretField = $state(!data?.config?.has_webhook_secret);
</script>

{#key form}
	<div class="flex flex-col">
		<SuperForm
			class="flex flex-col space-y-3"
			action={formAction}
			dataType={'json'}
			enctype={'application/x-www-form-urlencoded'}
			data={data.form}
			{_form}
			{invalidateAll}
			validators={zod(schema)}
		>
			{#snippet children({ form, data, initialData })}
				<Checkbox {form} field="is_active" label={m.active()} />
				<TextField
					{form}
					field="server_url"
					valuePath="credentials.server_url"
					label={m.serverUrl()}
					helpText={m.jiraServerUrlHelpText()}
				/>
				<TextField
					{form}
					field="email"
					valuePath="credentials.email"
					autocomplete="new-password"
					label={m.email()}
					helpText={m.jiraEmailHelpText()}
				/>
				{#if showApiTokenField}
					<TextField
						{form}
						field="api_token"
						type="password"
						valuePath="credentials.api_token"
						autocomplete="new-password"
						label={m.apiToken()}
					/>
				{:else}
					<div class="w-full p-4 flex flex-row justify-evenly items-center preset-tonal-secondary">
						<p>{m.apiTokenAlreadySetHelpText()}</p>
						<button
							class="btn preset-filled"
							onclick={() => {
								showApiTokenField = true;
								$formStore.api_token = '';
							}}>{m.resetApiToken()}</button
						>
					</div>
				{/if}
				<TextField
					{form}
					field="project_key"
					valuePath="settings.project_key"
					label={m.projectKey()}
					helpText={m.jiraProjectKeyHelpText()}
				/>
				<TextField
					{form}
					field="issue_type"
					valuePath="settings.issue_type"
					label={m.issueType()}
				/>
				{#if showWebhookSecretField}
					<TextField {form} field="webhook_secret" type="password" label={m.webhookSecret()} />
				{:else}
					<div
						class="text-center w-full p-4 flex flex-row justify-evenly items-center preset-tonal-secondary"
					>
						<p>{m.webhookSecretAlreadySetHelpText()}</p>
						<button
							class="btn preset-filled"
							onclick={() => {
								showWebhookSecretField = true;
								$formStore.webhook_secret = '';
							}}>{m.resetWebhookSecret()}</button
						>
					</div>
				{/if}
				<button
					class="text-center btn preset-filled-primary-500 font-semibold w-full"
					data-testid="save-button">{m.save()}</button
				>
			{/snippet}
		</SuperForm>
	</div>
{/key}
