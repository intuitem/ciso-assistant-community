<script lang="ts">
	// Props
	/** Exposes parent props to this component. */
	export let parent: any;

	// Stores
	import { getModalStore } from '@skeletonlabs/skeleton';
	import type { ModalStore } from '@skeletonlabs/skeleton';

	import * as m from '$paraglide/messages';

	const modalStore: ModalStore = getModalStore();

	export let totp;
	export let _form;
	export let formAction: string;

	import { superForm } from 'sveltekit-superforms';

	import SuperForm from '$lib/components/Forms/Form.svelte';

	// Base Classes
	const cBase = 'card p-4 w-modal shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';
	const cForm = 'p-4 space-y-4 rounded-container-token';

	import TextField from '$lib/components/Forms/TextField.svelte';
	import { zod } from 'sveltekit-superforms/adapters';
	import { mfaAuthenticateSchema } from '../utils/schemas';
</script>

{#if $modalStore[0]}
	<div class="modal-example-form {cBase}">
		<header class={cHeader}>{$modalStore[0].title ?? '(title missing)'}</header>
		<article>{$modalStore[0].body ?? '(body missing)'}</article>
		<article class="flex flex-col space-y-4 items-center">
			<!-- Enable for debugging: -->
			<SuperForm
				dataType="json"
				action={formAction}
				data={_form}
				validators={zod(mfaAuthenticateSchema)}
				let:form
				class="modal-form {cForm}"
			>
				<!-- prettier-ignore -->
				<TextField {form} field="code" label="_code" />
				<footer class="modal-footer {parent.regionFooter}">
					<button
						type="button"
						class="btn {parent.buttonNeutral}"
						data-testid="delete-cancel-button"
						on:click={parent.onClose}>{m.cancel()}</button
					>
					<button
						class="btn variant-filled-primary"
						data-testid="mfa-authenticate-confirm-button"
						type="submit">{m.submit()}</button
					>
				</footer>
			</SuperForm>
		</article>
	</div>
{/if}
