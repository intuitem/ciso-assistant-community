<script lang="ts">
	// Props
	/** Exposes parent props to this component. */
	export let parent: any;

	// Stores
	import type { ModalStore } from '@skeletonlabs/skeleton';
	import { getModalStore } from '@skeletonlabs/skeleton';

	import { copy } from '@svelte-put/copy';

	import NumberField from '$lib/components/Forms/NumberField.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import { AuthTokenCreateSchema } from '$lib/utils/schemas';
	import { zod } from 'sveltekit-superforms/adapters';
	import { m } from '$paraglide/messages';

	const modalStore: ModalStore = getModalStore();

	export let form;
	export let formAction: string = '?/createPAT';

	let tokenDisplayed = false;

	const _form = superForm(form, {
		dataType: 'json',
		enctype: 'application/x-www-form-urlencoded',
		invalidateAll: true,
		applyAction: $$props.applyAction ?? true,
		resetForm: $$props.resetForm ?? false,
		validators: zod(AuthTokenCreateSchema),
		validationMethod: 'auto',
		onUpdated: async ({ form }) => {
			if (form.message?.data?.token) {
				tokenDisplayed = true;
			}
		}
	});

	import SuperForm from '$lib/components/Forms/Form.svelte';
	import { page } from '$app/stores';
	import { superForm } from 'sveltekit-superforms';

	// Base Classes
	const cBase = 'card p-4 w-fit shadow-xl space-y-4 max-w-[80ch]';
	const cHeader = 'text-2xl font-bold';
	const cForm = 'p-4 space-y-4 rounded-container-token';

	$: console.log('toto', $page.form?.form?.message?.data?.token);
</script>

{#if $modalStore[0]}
	<div class="modal-example-form {cBase}">
		<header class={cHeader}>{$modalStore[0].title ?? '(title missing)'}</header>
		<article class="flex flex-row space-x-8">
			<div class="flex flex-col space-y-4 items-center">
				<div class="flex flex-col space-y-4 items-center self-center">
					<p class="text-surface-900">{m.personalAccessTokenCreateDescription()}</p>
					<SuperForm
						dataType="json"
						action={formAction}
						{_form}
						validators={zod(AuthTokenCreateSchema)}
						let:form
						class="modal-form {cForm}"
						validationMethod="onsubmit"
					>
						{#if !tokenDisplayed}
							<TextField {form} field="name" label={m.name()} classesContainer="w-full" />
							<NumberField
								{form}
								field="expiry"
								label={m.expiry()}
								helpText={m.personalAccessTokenExpiryHelpText()}
							/>
							<footer class="modal-footer {parent.regionFooter}">
								<button
									class="btn variant-filled-primary w-full"
									data-testid="activate-totp-confirm-button"
									type="submit">{m.generateNewPersonalAccessToken()}</button
								>
							</footer>
						{:else}
							<div class="card p-4 variant-ghost-secondary flex flex-row items-center">
								<i
									class="fa-solid fa-bell mr-2 text-secondary-800"
								/>{m.personalAccessTokenOnlyDisplayedOnce()}
							</div>
							<span class="flex flex-row gap-2 variant-ghost-surface items-center card pl-2">
								<pre>{$page?.form?.form?.message?.data?.token}</pre>
								<button
									type="button"
									class="btn px-2 py-1 {parent.buttonNeutral} rounded-l-none"
									use:copy={{ text: $page?.form?.form?.message?.data?.token }}
									><i class="fa-solid fa-copy mr-2"></i>{m.copy()}</button
								></span
							>
							<footer class="modal-footer {parent.regionFooter}">
								<button
									class="btn variant-filled-primary w-full"
									data-testid="activate-totp-confirm-button"
									type="button"
									on:click={parent.onConfirm}>{m.done()}</button
								>
							</footer>
						{/if}
					</SuperForm>
				</div>
			</div>
		</article>
	</div>
{/if}
