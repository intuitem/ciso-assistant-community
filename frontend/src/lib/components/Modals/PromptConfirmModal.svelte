<script lang="ts">
	import type { urlModel } from '$lib/utils/types';

	// Props
	/** Exposes parent props to this component. */
	export let parent: any;

	// Stores
	import { getModalStore } from '@skeletonlabs/skeleton';
	import type { ModalStore } from '@skeletonlabs/skeleton';

	import { m } from '$paraglide/messages';

	const modalStore: ModalStore = getModalStore();

	export let _form = {};
	export let URLModel: urlModel | '' = '';
	export let id: string = '';
	export let formAction: string = '';
	export let bodyComponent: ComponentType | undefined;
	export let bodyProps: Record<string, unknown> = {};

	import { superForm } from 'sveltekit-superforms';

	const { form } = _form
		? superForm(_form, {
				dataType: 'json',
				id: `confirm-modal-form-${crypto.randomUUID()}`
			})
		: null;

	// Base Classes
	const cBase = 'card p-4 w-modal shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';
	const cForm = 'p-4 space-y-4 rounded-container-token';

	import SuperDebug from 'sveltekit-superforms';
	import type { ComponentType } from 'svelte';
	import { enhance } from '$app/forms';
	export let debug = false;

	let userInput = '';
</script>

{#if $modalStore[0]}
	<div class="modal-example-form {cBase}">
		<header class={cHeader}>{$modalStore[0].title ?? '(title missing)'}</header>
		<article>{$modalStore[0].body ?? '(body missing)'}</article>

		<p class="text-red-500 font-bold">{m.confirmYes()}</p>
		<input
			type="text"
			data-testid="delete-prompt-confirm-textfield"
			bind:value={userInput}
			placeholder={m.confirmYesPlaceHolder()}
			class="w-full mt-2 p-2 border border-gray-300 rounded"
		/>

		{#if bodyComponent}
			<div class="max-h-96 overflow-y-scroll scroll card">
				<svelte:component this={bodyComponent} {...bodyProps} />
			</div>
		{/if}
		{#if _form && Object.keys(_form).length > 0}
			<form method="POST" action={formAction} use:enhance class="modal-form {cForm}">
				<footer class="modal-footer {parent.regionFooter}">
					<button type="button" class="btn {parent.buttonNeutral}" on:click={parent.onClose}
						>{m.cancel()}</button
					>
					<input type="hidden" name="urlmodel" value={URLModel} />
					<input type="hidden" name="id" value={id} />
					<button
						class="btn variant-filled-error"
						type="submit"
						data-testid="delete-prompt-confirm-button"
						on:click={parent.onConfirm}
						disabled={!userInput || userInput.trim().toLowerCase() !== m.yes().toLowerCase()}
					>
						{m.submit()}
					</button>
				</footer>
			</form>

			{#if debug === true}
				<SuperDebug data={$form} />
			{/if}
		{:else}
			<footer class="modal-footer {parent.regionFooter}">
				<button type="button" class="btn {parent.buttonNeutral}" on:click={parent.onClose}
					>{m.cancel()}</button
				>
				<button
					class="btn variant-filled-error"
					type="button"
					on:click={parent.onConfirm}
					disabled={!userInput || userInput.trim().toLowerCase() !== m.yes().toLowerCase()}
				>
					{m.submit()}
				</button>
			</footer>
		{/if}
	</div>
{/if}
