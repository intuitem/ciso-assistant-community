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

	const isVisible = (key: string) => visible.includes(key);
	const visibleCount = $derived(columns.filter((c) => isVisible(c.key)).length);

	function toggle(key: string) {
		if (isVisible(key)) {
			if (visibleCount <= 1) return; // always keep at least one column
			onChange(visible.filter((k) => k !== key));
		} else {
			// preserve natural column order when re-adding
			onChange(columns.filter((c) => isVisible(c.key) || c.key === key).map((c) => c.key));
		}
	}

	function showAll() {
		onChange(columns.map((c) => c.key));
	}

	function hideAll() {
		// keep the first column so the table never collapses to nothing
		onChange(columns.slice(0, 1).map((c) => c.key));
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
		{#if visibleCount < columns.length}
			<span class="text-xs ml-2">{visibleCount}/{columns.length}</span>
		{/if}
	</Popover.Trigger>
	<Popover.Positioner class="z-50!">
		<Popover.Content class="card p-2 bg-white w-64 shadow-lg space-y-2 border border-surface-200">
			<div class="flex items-center justify-between gap-2 px-1">
				<button type="button" class="text-xs anchor" onclick={showAll}>{m.showAll()}</button>
				<button type="button" class="text-xs anchor" onclick={hideAll}>{m.hideAll()}</button>
			</div>
			<hr class="border-surface-200" />
			<ul class="max-h-64 overflow-y-auto space-y-1">
				{#each columns as column (column.key)}
					{@const visibleColumn = isVisible(column.key)}
					{@const isLastVisible = visibleColumn && visibleCount <= 1}
					<li>
						<label
							class="flex items-center gap-2 px-1 py-1 rounded hover:bg-surface-50 cursor-pointer text-sm {isLastVisible
								? 'opacity-50 cursor-not-allowed'
								: ''}"
							title={isLastVisible ? m.atLeastOneColumnRequired() : undefined}
						>
							<input
								type="checkbox"
								class="checkbox"
								checked={visibleColumn}
								disabled={isLastVisible}
								onchange={() => toggle(column.key)}
							/>
							<span class="truncate">{safeTranslate(column.label)}</span>
						</label>
					</li>
				{/each}
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
		</Popover.Content>
	</Popover.Positioner>
</Popover>
