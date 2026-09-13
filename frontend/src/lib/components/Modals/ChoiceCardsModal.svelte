<script lang="ts">
	import { getModalStore, type ModalStore } from './stores';
	import { m } from '$paraglide/messages';

	export interface Choice {
		icon: string;
		iconClass?: string;
		label: string;
		description: string;
		testId?: string;
		action: () => void;
	}

	interface Props {
		parent: any;
		title: string;
		choices: Choice[];
	}

	let { parent, title, choices }: Props = $props();

	const modalStore: ModalStore = getModalStore();

	const cBase = 'card bg-surface-100-900 border border-surface-500 p-4 w-modal shadow-xl space-y-4';

	function choose(action: () => void) {
		modalStore.close();
		action();
	}
</script>

{#if $modalStore[0]}
	<div class="modal-choice-cards {cBase}">
		<div class="flex items-center justify-between">
			<header class="text-2xl font-bold">{title}</header>
			<button
				type="button"
				aria-label={m.close()}
				class="flex items-center hover:text-primary-500 cursor-pointer"
				onclick={parent.onClose}
			>
				<i class="fa-solid fa-xmark"></i>
			</button>
		</div>
		<div
			class="grid gap-4"
			style="grid-template-columns: repeat({choices.length}, minmax(0, 1fr));"
		>
			{#each choices as choice (choice.label)}
				<button
					class="flex flex-col items-start gap-2 p-4 rounded-xl border border-surface-200-800 bg-surface-50-950 text-left hover:bg-surface-100-900 hover:border-primary-400 transition-colors shadow-sm cursor-pointer"
					onclick={() => choose(choice.action)}
					data-testid={choice.testId}
				>
					<i class="fa-solid {choice.icon} {choice.iconClass ?? 'text-primary-500'} text-2xl"></i>
					<span class="text-sm font-semibold">{choice.label}</span>
					<span class="text-xs text-surface-600-400">{choice.description}</span>
				</button>
			{/each}
		</div>
	</div>
{/if}
