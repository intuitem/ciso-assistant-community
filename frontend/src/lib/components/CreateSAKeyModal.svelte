<script lang="ts">
	import { copy } from '@svelte-put/copy';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import NumberField from '$lib/components/Forms/NumberField.svelte';
	import { ServiceAccountKeyCreateSchema } from '$lib/utils/schemas';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { superForm } from 'sveltekit-superforms';
	import { getModalStore, type ModalStore } from '$lib/components/Modals/stores';
	import { m } from '$paraglide/messages';

	const modalStore: ModalStore = getModalStore();

	interface Props {
		parent: any;
		form: any;
		formAction?: string;
		[key: string]: any;
	}

	let { parent, form, formAction = '?/create', ...rest }: Props = $props();

	let token = $state<string | null>(null);
	let copied = $state(false);
	let tokenInputElement: HTMLInputElement | undefined = $state();

	const _form = superForm(form, {
		dataType: 'json',
		invalidateAll: true,
		applyAction: rest.applyAction ?? true,
		resetForm: rest.resetForm ?? false,
		validators: zod(ServiceAccountKeyCreateSchema),
		validationMethod: 'auto',
		onUpdated: async ({ form }) => {
			if (form.message?.object?.token) {
				token = form.message.object.token;
				setTimeout(() => tokenInputElement?.select(), 0);
			}
		}
	});

	const cBase = 'card bg-surface-50 p-4 w-fit shadow-xl space-y-4 max-w-[60ch] overflow-auto';
	const cHeader = 'text-2xl font-bold';
	const cForm = 'p-4 space-y-4 rounded-container-token';

	function handleCopy() {
		copied = true;
		setTimeout(() => (copied = false), 2000);
	}
</script>

{#if $modalStore[0]}
	<div class={cBase}>
		<header class={cHeader}>{$modalStore[0].title ?? m.serviceAccountKey()}</header>
		<SuperForm
			dataType="json"
			action={formAction}
			{_form}
			validators={zod(ServiceAccountKeyCreateSchema)}
			class="modal-form {cForm}"
			validationMethod="onsubmit"
		>
			{#snippet children({ form })}
				{#if !token}
					<TextField
						{form}
						field="name"
						label={m.keyName()}
						helpText={m.keyNameHelpText()}
						classesContainer="w-full"
					/>
					<NumberField
						{form}
						field="expiry_days"
						label={m.expiry()}
						helpText={m.personalAccessTokenExpiryHelpText()}
					/>
					<footer class="modal-footer {parent?.regionFooter ?? ''} flex gap-2">
						<button
							type="button"
							class="btn preset-outlined-surface-500 flex-1"
							onclick={parent?.onClose}
						>
							{m.cancel()}
						</button>
						<button type="submit" class="btn preset-filled-primary-500 flex-1">
							<i class="fa-solid fa-key mr-2"></i>{m.generate()}
						</button>
					</footer>
				{:else}
					<div class="card p-3 preset-tonal-warning flex items-start gap-2">
						<i class="fa-solid fa-triangle-exclamation text-warning-700 mt-0.5"></i>
						<p class="text-sm font-medium text-warning-900">
							{m.tokenWarning()}
						</p>
					</div>
					<div class="flex gap-2 items-stretch">
						<input
							bind:this={tokenInputElement}
							type="text"
							readonly
							value={token}
							class="input font-mono text-sm px-3 py-2 flex-1 select-all"
							onfocus={(e) => e.currentTarget.select()}
						/>
						<button
							type="button"
							class="btn preset-filled-primary-500 px-4"
							use:copy={{ text: token }}
							onclick={handleCopy}
						>
							{#if copied}
								<i class="fa-solid fa-check mr-2"></i>{m.copied()}
							{:else}
								<i class="fa-solid fa-copy mr-2"></i>{m.copy()}
							{/if}
						</button>
					</div>
					<footer class="modal-footer {parent?.regionFooter ?? ''}">
						<button
							type="button"
							class="btn preset-filled-primary-500 w-full"
							onclick={parent?.onConfirm}
						>
							{m.done()}
						</button>
					</footer>
				{/if}
			{/snippet}
		</SuperForm>
	</div>
{/if}
