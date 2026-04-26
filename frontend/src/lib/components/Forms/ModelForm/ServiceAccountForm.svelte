<script lang="ts">
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import { getModalStore, type ModalStore } from '$lib/components/Modals/stores';
	import { ServiceAccountCreateSchema } from '$lib/utils/schemas';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { superForm } from 'sveltekit-superforms';
	import { m } from '$paraglide/messages';

	const modalStore: ModalStore = getModalStore();

	interface Props {
		parent: any;
		form: any;
		formAction?: string;
	}

	let { parent, form, formAction = '?/createSA' }: Props = $props();

	const _form = superForm(form, {
		dataType: 'json',
		invalidateAll: true,
		validators: zod(ServiceAccountCreateSchema),
		validationMethod: 'auto',
		onUpdated: async ({ form }) => {
			if (form.valid) {
				modalStore.close();
			}
		}
	});

	const cBase = 'card bg-surface-50 p-4 w-fit shadow-xl space-y-4 max-w-[60ch] overflow-auto';
	const cHeader = 'text-2xl font-bold';
	const cForm = 'p-4 space-y-4 rounded-container-token';
</script>

{#if $modalStore[0]}
	<div class={cBase}>
		<header class={cHeader}>{$modalStore[0].title ?? m.createServiceAccount()}</header>
		<p class="text-sm text-surface-600 px-4">
			{m.serviceAccountIdentifiedAs()}
			<code class="font-mono text-xs bg-surface-100 px-1 rounded">
				&lt;name&gt;@serviceaccount.ciso-assistant.com
			</code>
		</p>
		<SuperForm
			dataType="json"
			action={formAction}
			{_form}
			validators={zod(ServiceAccountCreateSchema)}
			class="modal-form {cForm}"
			validationMethod="onsubmit"
		>
			{#snippet children({ form })}
				<TextField
					{form}
					field="slug"
					label={m.name()}
					helpText={m.serviceAccountSlugHelpText()}
					classesContainer="w-full"
				/>
				<TextArea
					{form}
					field="description"
					label={m.description()}
					helpText={m.serviceAccountDescriptionHelpText()}
				/>
				<TextField
					{form}
					type="date"
					field="expiry_date"
					label={m.expiryDate()}
					helpText={m.noExpiry()}
					classesContainer="w-full"
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
						{m.add()}
					</button>
				</footer>
			{/snippet}
		</SuperForm>
	</div>
{/if}
