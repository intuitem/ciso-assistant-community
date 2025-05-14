<script lang="ts">
	// Props
	

	// Stores
	import type { CssClasses, ModalStore } from '@skeletonlabs/skeleton-svelte';

	interface Action {
		label: string;
		action: () => boolean | Promise<boolean>;
		async: boolean;
		classes?: CssClasses;
		btnIcon?: string;
	}

	interface Props {
		/** Exposes parent props to this component. */
		parent: any;
		actions: Action[];
	}

	let { parent, actions }: Props = $props();

	const modalStore: ModalStore = getModalStore();

	// Base Classes
	const cBase = 'card p-4 w-modal shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';
</script>

{#if $modalStore[0]}
	<div class="modal-example-form {cBase}">
		<header class={cHeader} data-testid="modal-title">
			{$modalStore[0].title ?? '(title missing)'}
		</header>
		<article>{$modalStore[0].body ?? '(body missing)'}</article>
		<article>
			<span class="flex flex-row justify-between">
				{#each actions as action}
					<button
						onclick={async (event) => {
							const result = await action.action();
							return result ? parent.onConfirm(event) : null;
						}}
						class="btn {action.classes ?? 'preset-filled-surface-500'}"
					>
						{#if action.btnIcon}
							<i class="fa-solid mr-2 {action.btnIcon}"></i>
						{/if}
						{action.label}
					</button>
				{/each}
			</span>
		</article>
	</div>
{/if}
