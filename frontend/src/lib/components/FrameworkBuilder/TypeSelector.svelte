<script lang="ts">
	import { QUESTION_TYPES } from './builder-utils.svelte';

	interface Props {
		currentVariant: string;
		onselect: (variant: string) => void;
	}

	let { currentVariant, onselect }: Props = $props();
	let open = $state(false);
	let triggerEl: HTMLButtonElement | undefined = $state();
	let menuEl: HTMLDivElement | undefined = $state();
	let menuPos = $state({ top: -9999, left: -9999 });

	const currentTypeInfo = $derived(
		QUESTION_TYPES.find((t) => t.value === currentVariant) ?? QUESTION_TYPES[0]
	);

	// The menu uses `position: fixed` so it escapes the `overflow-hidden` on the
	// surrounding NodeBlock card. That also means nothing keeps it on screen: opened
	// near the bottom it used to render past the fold, and being fixed, scrolling
	// could not bring it back. So measure it and flip above the trigger when there
	// is no room below, clamping to the viewport either way.
	const MARGIN = 8;

	function place() {
		if (!triggerEl || !menuEl) return;
		const trigger = triggerEl.getBoundingClientRect();
		const menu = menuEl.getBoundingClientRect();

		let top = trigger.bottom + 4;
		if (top + menu.height > window.innerHeight - MARGIN) {
			top = trigger.top - menu.height - 4;
		}
		// Taller than the space above and below (a short window): pin it rather than
		// let either edge escape.
		top = Math.max(MARGIN, Math.min(top, window.innerHeight - menu.height - MARGIN));

		const left = Math.max(MARGIN, Math.min(trigger.left, window.innerWidth - menu.width - MARGIN));
		menuPos = { top, left };
	}

	function toggle() {
		open = !open;
		if (!open) menuPos = { top: -9999, left: -9999 };
	}

	// Placed after paint so the menu has a measurable height, and kept anchored while
	// the page moves under it.
	$effect(() => {
		if (!open) return;
		const frame = requestAnimationFrame(place);
		window.addEventListener('scroll', place, true);
		window.addEventListener('resize', place);
		return () => {
			cancelAnimationFrame(frame);
			window.removeEventListener('scroll', place, true);
			window.removeEventListener('resize', place);
		};
	});

	function select(variant: string) {
		onselect(variant);
		open = false;
		menuPos = { top: -9999, left: -9999 };
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
			bind:this={menuEl}
			class="fixed z-30 grid w-56 max-h-[80vh] grid-cols-2 gap-1 overflow-y-auto rounded-lg border border-surface-200-800 bg-surface-50-950 p-2 shadow-lg"
			style="top: {menuPos.top}px; left: {menuPos.left}px"
		>
			{#each QUESTION_TYPES as type (type.value)}
				<button
					type="button"
					class="flex items-center gap-2 px-3 py-2 rounded-md text-sm hover:bg-surface-50-950 transition-colors {currentVariant ===
					type.value
						? 'ring-2 ring-blue-500 ring-offset-1'
						: ''}"
					onclick={() => select(type.value)}
				>
					<span class="w-7 h-7 rounded flex items-center justify-center {type.color}">
						<i class="fa-solid {type.icon} text-xs"></i>
					</span>
					<span class="text-surface-700-300 font-medium">{type.label}</span>
				</button>
			{/each}
		</div>
	{/if}
</div>
