<script lang="ts">
	import Form from '$lib/components/Forms/Form.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import { getModalStore, type ModalStore } from '$lib/components/Modals/stores';
	import { IdPGroupSchema } from '$lib/utils/schemas';
	import { m } from '$paraglide/messages';
	import { onMount, tick } from 'svelte';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { superForm } from 'sveltekit-superforms/client';

	const cBase = 'card bg-surface-50 p-4 shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';

	interface Props {
		parent: any;
		form: any;
		formAction?: string;
	}

	const modalStore: ModalStore = getModalStore();
	let { parent, form, formAction = '?/createIdpGroup' }: Props = $props();

	onMount(async () => {
		await tick();
		const firstField = document.querySelector('input[data-focusindex="0"]');
		if (firstField instanceof HTMLElement) firstField.focus();
	});

	const _form = superForm(form, {
		dataType: 'json',
		validators: zod(IdPGroupSchema),
		validationMethod: 'onsubmit',
		onUpdated: async ({ form }) => {
			if (form.valid && parent && typeof parent.onConfirm === 'function') {
				parent.onConfirm();
			}
		}
	});
</script>

{#if $modalStore[0]}
	<div class="w-xl {cBase}">
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
			validators={zod(IdPGroupSchema)}
			action={formAction}
		>
			{#snippet children({ form })}
				<TextField
					{form}
					field="external_group_id"
					label={m.externalGroupId()}
					data-focusindex="0"
					helpText="The group name, UUID or DN exactly as sent by your IdP"
				/>
				<div class="flex flex-row justify-between space-x-4">
					<button
						class="btn bg-gray-400 text-white font-semibold w-full"
						type="button"
						onclick={(e) => parent.onClose(e)}>{m.cancel()}</button
					>
					<button class="btn preset-filled-primary-500 font-semibold w-full" type="submit"
						>{m.save()}</button
					>
				</div>
			{/snippet}
		</Form>
	</div>
{/if}
