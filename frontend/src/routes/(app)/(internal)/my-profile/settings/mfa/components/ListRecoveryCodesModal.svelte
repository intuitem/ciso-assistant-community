<script lang="ts">
	// Props
	

	// Stores
	import type { ModalStore } from '@skeletonlabs/skeleton';
	import { getModalStore } from '@skeletonlabs/skeleton';
	import { recoveryCodes } from '../utils/stores';

	import { m } from '$paraglide/messages';

	import { enhance } from '$app/forms';
	import { copy } from '@svelte-put/copy';
	interface Props {
		/** Exposes parent props to this component. */
		parent: any;
	}

	let { parent }: Props = $props();

	const modalStore: ModalStore = getModalStore();

	// Base Classes
	const cBase = 'card p-4 w-fit shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';
</script>

{#if $modalStore[0]}
	<div class="modal-example-form {cBase}">
		<header class={cHeader}>{$modalStore[0].title ?? '(title missing)'}</header>
		<article class="max-w-[65ch]">{$modalStore[0].body ?? '(body missing)'}</article>
		{#if $recoveryCodes}
			<div class="flex flex-col space-y-4 mx-auto card p-4 max-w-lg">
				<div class="flex flex-wrap justify-evenly">
					{#each $recoveryCodes.unused_codes as code}
						<pre>{code}&nbsp;</pre>
					{/each}
				</div>
				<span class="flex flex-row space-x-2 justify-end">
					<form method="POST" action="?/regenerateRecoveryCodes" use:enhance>
						<input type="hidden" name="regenerate" value="1" />
						<button type="submit" class="btn px-2 py-1 {parent.buttonNeutral}"
							><i class="fa-solid fa-sync mr-2"></i>{m.regenerateRecoveryCodes()}</button
						>
					</form>
					<button
						type="button"
						class="btn px-2 py-1 {parent.buttonNeutral}"
						use:copy={{ text: $recoveryCodes.unused_codes.join(' ') }}
						><i class="fa-solid fa-copy mr-2"></i>{m.copy()}</button
					>
				</span>
			</div>
		{/if}
		<footer class="modal-footer {parent.regionFooter}">
			<button type="button" class="btn {parent.buttonPositive}" onclick={parent.onClose}
				>{m.ok()}</button
			>
		</footer>
	</div>
{/if}
