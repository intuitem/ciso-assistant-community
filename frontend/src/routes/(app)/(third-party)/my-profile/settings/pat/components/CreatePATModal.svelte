<script lang="ts">
	import { copy } from '@svelte-put/copy';

	import NumberField from '$lib/components/Forms/NumberField.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import { AuthTokenCreateSchema } from '$lib/utils/schemas';
	import { zod } from 'sveltekit-superforms/adapters';
	import { m } from '$paraglide/messages';

	import SuperForm from '$lib/components/Forms/Form.svelte';
	import { page } from '$app/state';
	import { superForm } from 'sveltekit-superforms';
	import { getModalStore, type ModalStore } from '$lib/components/Modals/stores';

	const modalStore: ModalStore = getModalStore();

	interface Props {
		/** Exposes parent props to this component. */
		parent: any;
		form: any;
		formAction?: string;
		[key: string]: any;
	}

	let { parent, form, formAction = '?/createPAT', ...rest }: Props = $props();

	let tokenDisplayed = $state(false);
	let copied = $state(false);
	let tokenInputElement: HTMLInputElement | undefined = $state();

	const _form = superForm(form, {
		dataType: 'json',
		enctype: 'application/x-www-form-urlencoded',
		invalidateAll: true,
		applyAction: rest.applyAction ?? true,
		resetForm: rest.resetForm ?? false,
		validators: zod(AuthTokenCreateSchema),
		validationMethod: 'auto',
		onUpdated: async ({ form }) => {
			if (form.message?.data?.token) {
				tokenDisplayed = true;
				// Auto-select token on next tick
				setTimeout(() => {
					tokenInputElement?.select();
				}, 0);
			}
		}
	});

	// Base Classes
	const cBase = 'card bg-surface-50 p-4 w-fit shadow-xl space-y-4 max-w-[80ch] overflow-auto';
	const cHeader = 'text-2xl font-bold';
	const cForm = 'p-4 space-y-4 rounded-container-token';

	function handleCopy() {
		copied = true;
		setTimeout(() => {
			copied = false;
		}, 2000);
	}
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
						class="modal-form {cForm}"
						validationMethod="onsubmit"
					>
						{#snippet children({ form })}
							{#if !tokenDisplayed}
								<TextField {form} field="name" label={m.name()} classesContainer="w-full" />
								<NumberField
									{form}
									field="expiry"
									label={m.expiry()}
									helpText={m.personalAccessTokenExpiryHelpText()}
								/>
								<footer class="modal-footer {parent?.regionFooter ?? ''}">
									<button
										class="btn preset-filled-primary-500 w-full"
										data-testid="activate-totp-confirm-button"
										type="submit">{m.generateNewPersonalAccessToken()}</button
									>
								</footer>
							{:else}
								<div class="card p-4 preset-tonal-secondary flex flex-row items-center">
									<i class="fa-solid fa-bell mr-2 text-secondary-800"
									></i>{m.personalAccessTokenOnlyDisplayedOnce()}
								</div>
								<div class="space-y-2">
									<label class="label font-semibold">{m.token()}</label>
									<div class="flex flex-row gap-2 items-stretch">
										<input
											bind:this={tokenInputElement}
											type="text"
											readonly
											value={page?.form?.form?.message?.data?.token}
											class="input font-mono text-sm px-3 py-2 flex-1 select-all"
											onfocus={(e) => e.currentTarget.select()}
										/>
										<button
											type="button"
											class="btn preset-filled-primary-500 px-4"
											use:copy={{ text: page?.form?.form?.message?.data?.token }}
											onclick={handleCopy}
										>
											{#if copied}
												<i class="fa-solid fa-check mr-2"></i>{m.copied()}
											{:else}
												<i class="fa-solid fa-copy mr-2"></i>{m.copy()}
											{/if}
										</button>
									</div>
								</div>
								<footer class="modal-footer {parent?.regionFooter ?? ''}">
									<button
										class="btn preset-filled-primary-500 w-full"
										data-testid="activate-totp-confirm-button"
										type="button"
										onclick={parent?.onConfirm}>{m.done()}</button
									>
								</footer>
							{/if}
						{/snippet}
					</SuperForm>
				</div>
			</div>
		</article>
	</div>
{/if}
