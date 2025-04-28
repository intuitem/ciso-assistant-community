<script lang="ts">
	// Props
	/** Exposes parent props to this component. */
	export let parent: any;

	// Stores
	import type { ModalStore } from '@skeletonlabs/skeleton';
	import { getModalStore } from '@skeletonlabs/skeleton';

	import { m } from '$paraglide/messages';

	const modalStore: ModalStore = getModalStore();

	export let _form;
	export let formAction: string = '?/createPAT';

	import SuperForm from '$lib/components/Forms/Form.svelte';

	// Base Classes
	const cBase = 'card p-4 w-fit shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';
	const cForm = 'p-4 space-y-4 rounded-container-token';

	import NumberField from '$lib/components/Forms/NumberField.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import { AuthTokenCreateSchema } from '$lib/utils/schemas';
	import { zod } from 'sveltekit-superforms/adapters';
</script>

{#if $modalStore[0]}
	<div class="modal-example-form {cBase}">
		<header class={cHeader}>{$modalStore[0].title ?? '(title missing)'}</header>
		<article class="flex flex-row space-x-8">
			<div class="flex flex-col space-y-4 items-center">
				<div class="flex flex-col space-y-4 items-center self-center">
					<p class="text-surface-900">{m.enterCodeGeneratedByApp()}</p>
					<!-- Enable for debugging: -->
					<SuperForm
						dataType="json"
						action={formAction}
						data={_form}
						validators={zod(AuthTokenCreateSchema)}
						let:form
						class="modal-form {cForm}"
						validationMethod="onsubmit"
					>
						<TextField {form} field="name" label={m.name()} classesContainer="w-full" />
						<NumberField {form} field="expiry" label={m.expiryDate()} helpText={m.etaHelpText()} />
						<footer class="modal-footer {parent.regionFooter}">
							<button
								class="btn variant-filled-primary w-full"
								data-testid="activate-totp-confirm-button"
								type="submit">{m.generateNewPersonalAccessToken()}</button
							>
						</footer>
					</SuperForm>
				</div>
			</div>
		</article>
	</div>
{/if}
