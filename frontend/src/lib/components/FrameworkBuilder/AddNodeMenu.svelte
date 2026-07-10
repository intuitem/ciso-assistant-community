<script lang="ts">
	import { getBuilderContext, type NodePreset } from './builder-state';
	import { m } from '$paraglide/messages';

	interface Props {
		parent: string | null;
		afterIndex?: number;
		triggerLabel: string;
		triggerClass?: string;
		onBeforeAdd?: () => void;
	}
	let { parent, afterIndex, triggerLabel, triggerClass = '', onBeforeAdd }: Props = $props();

	const builder = getBuilderContext();
	let open = $state(false);
	let rootEl: HTMLDivElement;

	function addWith(preset: NodePreset) {
		onBeforeAdd?.();
		builder.addNode({ parent, afterIndex, preset });
		open = false;
	}

	function onFocusOut(e: FocusEvent) {
		if (!rootEl.contains(e.relatedTarget as Node | null)) open = false;
	}

	function onKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			open = false;
			(rootEl.querySelector('button') as HTMLButtonElement | null)?.focus();
		}
	}
</script>

<div class="relative" bind:this={rootEl} onfocusout={onFocusOut} onkeydown={onKeydown}>
	<button
		type="button"
		class={triggerClass}
		aria-haspopup="menu"
		aria-expanded={open}
		onclick={() => (open = !open)}
	>
		{triggerLabel}
	</button>
	{#if open}
		<div
			role="menu"
			class="absolute left-1/2 -translate-x-1/2 z-20 mt-1 w-64 bg-surface-50-950 border border-surface-200-800 rounded-lg shadow-lg py-1"
		>
			<button
				type="button"
				role="menuitem"
				class="w-full px-3 py-2 text-left hover:bg-surface-50-950"
				onclick={() => addWith('blank')}
			>
				<div class="text-sm text-surface-700-300">{m.builderBlankNode()}</div>
				<div class="text-xs text-surface-500">{m.builderBlankNodeHint()}</div>
			</button>
			<div class="border-t border-surface-100-900 my-1"></div>
			<button
				type="button"
				role="menuitem"
				class="w-full px-3 py-2 text-left hover:bg-surface-50-950"
				onclick={() => addWith('group')}
			>
				<div class="text-sm text-surface-700-300">
					<i class="fa-solid fa-folder text-surface-500 mr-1"></i>{m.builderGroup()}
				</div>
				<div class="text-xs text-surface-500">{m.builderGroupHint()}</div>
			</button>
			<button
				type="button"
				role="menuitem"
				class="w-full px-3 py-2 text-left hover:bg-surface-50-950"
				onclick={() => addWith('requirement')}
			>
				<div class="text-sm text-surface-700-300">
					<i class="fa-solid fa-square-check text-green-500 mr-1"></i>{m.requirement()}
				</div>
				<div class="text-xs text-surface-500">{m.builderRequirementHint()}</div>
			</button>
			<button
				type="button"
				role="menuitem"
				class="w-full px-3 py-2 text-left hover:bg-surface-50-950"
				onclick={() => addWith('splash')}
			>
				<div class="text-sm text-surface-700-300">
					<i class="fa-solid fa-display text-purple-400 mr-1"></i>{m.builderSplashScreen()}
				</div>
				<div class="text-xs text-surface-500">{m.builderSplashScreenHint()}</div>
			</button>
		</div>
	{/if}
</div>
