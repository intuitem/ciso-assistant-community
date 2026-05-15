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
			class="absolute left-1/2 -translate-x-1/2 z-20 mt-1 w-64 bg-white border border-gray-200 rounded-lg shadow-lg py-1"
		>
			<button
				type="button"
				role="menuitem"
				class="w-full px-3 py-2 text-left hover:bg-gray-50"
				onclick={() => addWith('blank')}
			>
				<div class="text-sm text-gray-700">{m.builderBlankNode()}</div>
				<div class="text-xs text-gray-400">{m.builderBlankNodeHint()}</div>
			</button>
			<div class="border-t border-gray-100 my-1"></div>
			<button
				type="button"
				role="menuitem"
				class="w-full px-3 py-2 text-left hover:bg-gray-50"
				onclick={() => addWith('group')}
			>
				<div class="text-sm text-gray-700">
					<i class="fa-solid fa-folder text-gray-400 mr-1"></i>{m.builderGroup()}
				</div>
				<div class="text-xs text-gray-400">{m.builderGroupHint()}</div>
			</button>
			<button
				type="button"
				role="menuitem"
				class="w-full px-3 py-2 text-left hover:bg-gray-50"
				onclick={() => addWith('requirement')}
			>
				<div class="text-sm text-gray-700">
					<i class="fa-solid fa-square-check text-green-500 mr-1"></i>{m.requirement()}
				</div>
				<div class="text-xs text-gray-400">{m.builderRequirementHint()}</div>
			</button>
			<button
				type="button"
				role="menuitem"
				class="w-full px-3 py-2 text-left hover:bg-gray-50"
				onclick={() => addWith('splash')}
			>
				<div class="text-sm text-gray-700">
					<i class="fa-solid fa-display text-purple-400 mr-1"></i>{m.builderSplashScreen()}
				</div>
				<div class="text-xs text-gray-400">{m.builderSplashScreenHint()}</div>
			</button>
		</div>
	{/if}
</div>
