<script lang="ts">
	import { QUESTION_TYPES } from './builder-utils.svelte';

	interface Props {
		currentVariant: string;
		onselect: (variant: string) => void;
	}

	let { currentVariant, onselect }: Props = $props();
	let open = $state(false);
	let triggerEl: HTMLButtonElement | undefined = $state();
	let menuPos = $state({ top: 0, left: 0 });

	const currentTypeInfo = $derived(
		QUESTION_TYPES.find((t) => t.value === currentVariant) ?? QUESTION_TYPES[0]
	);

	// The menu uses `position: fixed` so it escapes the `overflow-hidden` on
	// the surrounding NodeBlock card. Anchor it to the trigger's bounding
	// rect each time we open.
	function toggle() {
		if (!open && triggerEl) {
			const r = triggerEl.getBoundingClientRect();
			menuPos = { top: r.bottom + 4, left: r.left };
		}
		open = !open;
	}

	function select(variant: string) {
		onselect(variant);
		open = false;
	}
</script>

<div class="relative">
	<button
		bind:this={triggerEl}
		type="button"
		class="inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium {currentTypeInfo.color} hover:opacity-80 transition-opacity"
		onclick={toggle}
	>
		<i class="fa-solid {currentTypeInfo.icon}"></i>
		{currentTypeInfo.label}
		<i class="fa-solid fa-chevron-down text-[10px] opacity-60"></i>
	</button>

	{#if open}
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="fixed inset-0 z-20"
			onclick={() => (open = false)}
			onkeydown={(e) => e.key === 'Escape' && (open = false)}
		></div>
		<div
			class="fixed z-30 bg-white rounded-lg shadow-lg border border-gray-200 p-2 grid grid-cols-2 gap-1 w-56"
			style="top: {menuPos.top}px; left: {menuPos.left}px"
		>
			{#each QUESTION_TYPES as type (type.value)}
				<button
					type="button"
					class="flex items-center gap-2 px-3 py-2 rounded-md text-sm hover:bg-gray-50 transition-colors {currentVariant ===
					type.value
						? 'ring-2 ring-blue-500 ring-offset-1'
						: ''}"
					onclick={() => select(type.value)}
				>
					<span class="w-7 h-7 rounded flex items-center justify-center {type.color}">
						<i class="fa-solid {type.icon} text-xs"></i>
					</span>
					<span class="text-gray-700 font-medium">{type.label}</span>
				</button>
			{/each}
		</div>
	{/if}
</div>
