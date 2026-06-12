<script lang="ts">
	import { Popover } from '@skeletonlabs/skeleton-svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';

	interface Column {
		key: string;
		label: string;
	}

	interface Props {
		columns: Column[];
		visible: string[];
		onChange: (visible: string[]) => void;
		onReset: () => void;
	}

	let { columns, visible, onChange, onReset }: Props = $props();

	let open = $state(false);
	let draggedKey: string | null = $state(null);
	let dragOverKey: string | null = $state(null);

	const byKey = $derived(new Map(columns.map((c) => [c.key, c])));
	// Visible columns in their current (persisted) order, then the hidden ones.
	const visibleEntries = $derived(visible.map((k) => byKey.get(k)).filter(Boolean) as Column[]);
	const hiddenEntries = $derived(columns.filter((c) => !visible.includes(c.key)));

	function hide(key: string) {
		if (visible.length <= 1) return; // always keep at least one column
		onChange(visible.filter((k) => k !== key));
	}

	function show(key: string) {
		onChange([...visible, key]);
	}

	function showAll() {
		onChange([...visible, ...hiddenEntries.map((c) => c.key)]);
	}

	function hideAll() {
		onChange(visible.slice(0, 1)); // keep the first so the table never collapses
	}

	function onDrop(targetKey: string) {
		if (!draggedKey || draggedKey === targetKey) return;
		const next = [...visible];
		const from = next.indexOf(draggedKey);
		const to = next.indexOf(targetKey);
		if (from === -1 || to === -1) return;
		next.splice(from, 1);
		next.splice(to, 0, draggedKey);
		onChange(next);
		draggedKey = null;
		dragOverKey = null;
	}
</script>

<Popover
	{open}
	onOpenChange={(e) => (open = e.open)}
	positioning={{ placement: 'bottom-end' }}
	autoFocus={false}
	onPointerDownOutside={() => (open = false)}
	closeOnInteractOutside={true}
>
	<Popover.Trigger
		class="btn preset-tonal-surface border border-surface-300 h-9 inline-flex items-center"
		title={m.columns()}
		aria-label={m.columns()}
	>
		<i class="fa-solid fa-table-columns"></i>
		{#if visible.length < columns.length}
			<span class="text-xs ml-2">{visible.length}/{columns.length}</span>
		{/if}
	</Popover.Trigger>
	<Popover.Positioner class="z-50!">
		<Popover.Content class="card p-2 bg-surface-50-950 w-72 shadow-lg space-y-2 border border-surface-200">
			<!-- Render content only when open so column labels don't duplicate page text (breaks exact-text locators). -->
			{#if open}
				<div class="flex items-center justify-between gap-2 px-1">
					<button type="button" class="text-xs anchor" onclick={showAll}>{m.showAll()}</button>
					<button type="button" class="text-xs anchor" onclick={hideAll}>{m.hideAll()}</button>
				</div>
				<hr class="border-surface-200" />
				<ul class="max-h-72 overflow-y-auto space-y-1">
					{#each visibleEntries as column (column.key)}
						{@const isLastVisible = visible.length <= 1}
						<li
							class="flex items-center gap-1 rounded text-sm transition-colors {dragOverKey ===
							column.key
								? 'bg-primary-50'
								: 'hover:bg-surface-50'}"
							role="listitem"
							ondragover={(e) => {
								e.preventDefault();
								dragOverKey = column.key;
							}}
							ondragleave={() => (dragOverKey === column.key ? (dragOverKey = null) : null)}
							ondrop={(e) => {
								e.preventDefault();
								onDrop(column.key);
							}}
						>
							<span
								class="cursor-grab px-1 text-surface-400 active:cursor-grabbing"
								draggable={true}
								role="button"
								tabindex="-1"
								aria-label={m.dragToReorder()}
								title={m.dragToReorder()}
								ondragstart={() => (draggedKey = column.key)}
								ondragend={() => {
									draggedKey = null;
									dragOverKey = null;
								}}
							>
								<i class="fa-solid fa-grip-vertical text-xs"></i>
							</span>
							<label
								class="flex flex-1 items-center gap-2 py-1 pr-1 cursor-pointer {isLastVisible
									? 'opacity-50 cursor-not-allowed'
									: ''}"
								title={isLastVisible ? m.atLeastOneColumnRequired() : undefined}
							>
								<input
									type="checkbox"
									class="checkbox"
									checked={true}
									disabled={isLastVisible}
									onchange={() => hide(column.key)}
								/>
								<span class="truncate">{safeTranslate(column.label)}</span>
							</label>
						</li>
					{/each}
					{#if hiddenEntries.length > 0}
						<li class="px-1 pt-1 text-[0.65rem] uppercase tracking-wide text-surface-400">
							{m.hidden()}
						</li>
						{#each hiddenEntries as column (column.key)}
							<li>
								<label
									class="flex items-center gap-2 rounded py-1 pl-7 pr-1 cursor-pointer text-sm hover:bg-surface-50"
								>
									<input
										type="checkbox"
										class="checkbox"
										checked={false}
										onchange={() => show(column.key)}
									/>
									<span class="truncate">{safeTranslate(column.label)}</span>
								</label>
							</li>
						{/each}
					{/if}
				</ul>
				<hr class="border-surface-200" />
				<div class="flex justify-end px-1">
					<button
						type="button"
						class="btn preset-tonal-surface text-xs"
						onclick={() => {
							onReset();
							open = false;
						}}
					>
						<i class="fa-solid fa-rotate-left mr-2"></i>
						{m.resetToDefault()}
					</button>
				</div>
			{/if}
		</Popover.Content>
	</Popover.Positioner>
</Popover>
