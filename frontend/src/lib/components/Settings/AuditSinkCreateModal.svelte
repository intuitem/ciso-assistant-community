<script lang="ts">
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import Form from '$lib/components/Forms/Form.svelte';
	import MarkdownField from '$lib/components/Forms/MarkdownField.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import RadioGroup from '$lib/components/Forms/RadioGroup.svelte';
	import Select from '$lib/components/Forms/Select.svelte';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import { getModalStore, type ModalStore } from '$lib/components/Modals/stores';
	import { auditSinkSchema } from '$lib/utils/schemas';
	import { m } from '$paraglide/messages';
	import { onMount, tick } from 'svelte';
	import type { SuperForm } from 'sveltekit-superforms';
	import { formFieldProxy } from 'sveltekit-superforms';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { superForm } from 'sveltekit-superforms/client';

	const cBase = 'card bg-surface-50 p-4 shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';

	interface Props {
		parent: any;
		form: SuperForm<any>;
		formAction?: string;
		initialData?: Record<string, any> | null;
		[key: string]: any;
	}

	const modalStore: ModalStore = getModalStore();

	let { parent, form, formAction = '?/createAuditSink', initialData = null }: Props = $props();

	const _form = superForm(form, {
		dataType: 'json',
		validators: zod(auditSinkSchema),
		validationMethod: 'onsubmit',
		onUpdated: async ({ form }) => {
			if (form.valid && parent && typeof parent.onConfirm === 'function') {
				parent.onConfirm();
			}
		}
	});

	const { value: transport } = formFieldProxy(_form, 'transport');

	if (initialData) {
		const cfg = initialData.kafka_config ?? {};
		const sasl = cfg.config ?? {};
		_form.form.update((d) => ({
			...d,
			id: initialData.id,
			name: initialData.name,
			description: initialData.description,
			transport: initialData.transport,
			body_format: initialData.body_format,
			is_active: initialData.is_active,
			url: initialData.url ?? '',
			headers:
				initialData.headers && Object.keys(initialData.headers).length
					? JSON.stringify(initialData.headers)
					: '',
			target_folders: initialData.target_folders ?? [],
			bootstrap_servers: cfg.bootstrap_servers ?? '',
			topic: cfg.topic ?? '',
			security_protocol: sasl.security_protocol ?? 'PLAINTEXT',
			sasl_mechanism: sasl.sasl_mechanism ?? '',
			sasl_username: sasl.sasl_plain_username ?? '',
			sasl_password: sasl.sasl_plain_password ?? ''
		}));
	}

	onMount(async () => {
		await tick();
		const firstField = document.querySelector('input[data-focusindex="0"]');
		if (firstField instanceof HTMLElement) {
			firstField.focus();
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
				onkeydown={(e) => {
					if (e.key === 'Enter' || e.key === ' ') {
						e.preventDefault();
						parent.onClose(e);
					}
				}}
			>
				<i class="fa-solid fa-xmark"></i>
			</div>
		</div>
		<Form
			class="flex flex-col space-y-3"
			{_form}
			data={form}
			dataType="json"
			validators={zod(auditSinkSchema)}
			action={formAction}
		>
			{#snippet children({ form })}
				<Checkbox {form} field="is_active" label={m.isActive()} checked />
				<TextField {form} field="name" label={m.name()} data-focusindex="0" />
				<MarkdownField {form} field="description" label={m.description()} />
				<RadioGroup
					{form}
					field="transport"
					label={m.transport()}
					possibleOptions={[
						{ label: 'HTTP', value: 'http' },
						{ label: 'Kafka', value: 'kafka' }
					]}
					labelKey="label"
					valueKey="value"
				/>
				<RadioGroup
					{form}
					field="body_format"
					label={m.bodyFormat()}
					possibleOptions={[
						{ label: 'OCSF', value: 'ocsf' },
						{ label: m.raw(), value: 'raw' }
					]}
					labelKey="label"
					valueKey="value"
					helpText={m.bodyFormatHelpText()}
				/>
				{#if $transport === 'kafka'}
					<TextField
						{form}
						field="bootstrap_servers"
						label={m.bootstrapServers()}
						autocomplete="off"
						helpText={m.bootstrapServersHelpText()}
					/>
					<TextField {form} field="topic" label={m.kafkaTopic()} autocomplete="off" />
					<Dropdown
						open={false}
						style="hover:text-primary-700"
						icon="fa-solid fa-lock"
						header={m.securityAndAuthentication()}
					>
						<Select
							{form}
							field="security_protocol"
							label={m.securityProtocol()}
							options={[
								{ label: 'PLAINTEXT', value: 'PLAINTEXT' },
								{ label: 'SSL', value: 'SSL' },
								{ label: 'SASL_PLAINTEXT', value: 'SASL_PLAINTEXT' },
								{ label: 'SASL_SSL', value: 'SASL_SSL' }
							]}
						/>
						<Select
							{form}
							field="sasl_mechanism"
							label={m.saslMechanism()}
							options={[
								{ label: m.none(), value: '' },
								{ label: 'PLAIN', value: 'PLAIN' },
								{ label: 'SCRAM-SHA-256', value: 'SCRAM-SHA-256' },
								{ label: 'SCRAM-SHA-512', value: 'SCRAM-SHA-512' }
							]}
						/>
						<TextField {form} field="sasl_username" label={m.saslUsername()} autocomplete="off" />
						<TextField
							{form}
							field="sasl_password"
							label={m.saslPassword()}
							type="password"
							autocomplete="off"
						/>
					</Dropdown>
				{:else}
					<TextField {form} field="url" label={m.url()} autocomplete="off" />
					<TextField
						{form}
						field="headers"
						label={m.httpHeaders()}
						autocomplete="off"
						helpText={m.httpHeadersHelpText()}
					/>
				{/if}
				<AutocompleteSelect
					{form}
					field="target_folders"
					label={m.targetDomains()}
					helpText={m.auditSinkTargetDomainsHelpText()}
					optionsEndpoint="folders?content_type=DO&content_type=GL"
					multiple
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
					<button class="btn preset-filled-primary-500 font-semibold w-full" type="submit"
						>{m.save()}</button
					>
				</div>
			{/snippet}
		</Form>
	</div>
{/if}
