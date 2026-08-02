<script lang="ts">
	import { m } from '$paraglide/messages';

	export interface PaletteTechnique {
		id: string;
		ref_id: string;
		name: string;
		tactics: string[];
		children?: PaletteTechnique[];
	}

	export interface PaletteLane {
		id: string;
		ref_id: string;
		name: string;
	}

	interface Props {
		lanes: PaletteLane[];
		techniques: PaletteTechnique[];
		/** `techniqueId:tacticId` keys — placed in one tactic, still offered in others */
		placedIds: Set<string>;
		onDragStateChange?: (tactics: string[] | null) => void;
	}

	let { lanes, techniques, placedIds, onDragStateChange }: Props = $props();

	let query = $state('');
	// 15+ lanes and ~700 techniques: everything starts collapsed, search is the way in
	let expandedLanes = $state(new Set<string>());
	let expandedParents = $state(new Set<string>());

	const needle = $derived(query.trim().toLowerCase());

	function matches(technique: PaletteTechnique): boolean {
		if (!needle) return true;
		return `${technique.ref_id} ${technique.name}`.toLowerCase().includes(needle);
	}

	// a parent stays visible when only its sub-techniques match
	function visibleIn(lane: PaletteLane): PaletteTechnique[] {
		return techniques
			.filter((technique) => technique.tactics.includes(lane.id))
			.map((technique) => {
				const children = (technique.children ?? []).filter(matches);
				if (matches(technique)) return { ...technique, children: technique.children ?? [] };
				return children.length ? { ...technique, children } : null;
			})
			.filter((technique): technique is PaletteTechnique => technique !== null);
	}

	const byLane = $derived(lanes.map((lane) => ({ lane, items: visibleIn(lane) })));
	const searching = $derived(needle.length > 0);

	function toggle(set: Set<string>, key: string): Set<string> {
		const next = new Set(set);
		next.has(key) ? next.delete(key) : next.add(key);
		return next;
	}

	function handleDragStart(event: DragEvent, technique: PaletteTechnique) {
		if (!event.dataTransfer) return;
		event.dataTransfer.setData(
			'application/json',
			JSON.stringify({
				id: technique.id,
				ref_id: technique.ref_id,
				name: technique.name,
				tactics: technique.tactics
			})
		);
		event.dataTransfer.effectAllowed = 'move';
		onDragStateChange?.(technique.tactics);
	}

	function handleDragEnd() {
		onDragStateChange?.(null);
	}
</script>

<div
	class="w-72 shrink-0 bg-surface-50-950 border-r border-surface-200-800 flex flex-col h-full overflow-hidden"
>
	<div class="p-3 border-b border-surface-200-800">
		<input
			type="search"
			placeholder={m.searchPlaceholder()}
			bind:value={query}
			class="input w-full px-2 py-1 text-sm"
			aria-label={m.search()}
		/>
	</div>

	<div class="flex-1 overflow-y-auto p-2 space-y-1">
		{#each byLane as { lane, items } (lane.id)}
			{@const open = searching || expandedLanes.has(lane.id)}
			<div>
				<button
					class="w-full flex items-center justify-between px-2 py-1.5 text-xs font-semibold text-surface-600-400 hover:bg-surface-100-900 rounded-base"
					onclick={() => (expandedLanes = toggle(expandedLanes, lane.id))}
					aria-expanded={open}
				>
					<span class="text-left text-wrap">{lane.name}</span>
					<span class="flex items-center gap-1 shrink-0">
						<span class="text-surface-500">{items.length}</span>
						<i class="fa-solid fa-chevron-{open ? 'down' : 'right'} text-[10px] text-surface-500"
						></i>
					</span>
				</button>

				{#if open}
					<div class="space-y-0.5 mt-1">
						{#each items as technique (technique.id)}
							{@const placed = placedIds.has(`${technique.id}:${lane.id}`)}
							{@const children = technique.children ?? []}
							{@const childrenOpen = searching || expandedParents.has(`${lane.id}:${technique.id}`)}
							<div
								class="rounded-base border px-2 py-1 text-xs {placed
									? 'border-surface-200-800 bg-surface-100-900 text-surface-500 opacity-60'
									: 'border-surface-300-700 bg-surface-50-950 cursor-grab hover:border-primary-500'}"
								draggable={!placed}
								ondragstart={(event) => !placed && handleDragStart(event, technique)}
								ondragend={handleDragEnd}
								role="listitem"
							>
								<div class="flex items-start gap-1">
									<span class="grow leading-snug text-wrap">
										<span class="font-mono text-[10px] text-surface-500">{technique.ref_id}</span>
										{technique.name}
									</span>
									{#if placed}
										<i class="fa-solid fa-check text-[10px] text-success-500 mt-0.5"></i>
									{/if}
									{#if children.length}
										<button
											type="button"
											class="shrink-0 text-surface-600-400 hover:text-primary-500"
											aria-expanded={childrenOpen}
											aria-label={technique.name}
											onclick={() =>
												(expandedParents = toggle(expandedParents, `${lane.id}:${technique.id}`))}
										>
											<i class="fa-solid fa-caret-{childrenOpen ? 'down' : 'right'}"></i>
											<span class="text-[10px]">{children.length}</span>
										</button>
									{/if}
								</div>

								{#if childrenOpen && children.length}
									<ul class="mt-1 space-y-0.5 border-t border-surface-300-700 pt-1 pl-2">
										{#each children as child (child.id)}
											{@const childPlaced = placedIds.has(`${child.id}:${lane.id}`)}
											{@const childDrag = {
												...child,
												tactics: child.tactics.length ? child.tactics : technique.tactics
											}}
											<li
												class="leading-snug {childPlaced
													? 'text-surface-500 opacity-60'
													: 'cursor-grab hover:text-primary-500'}"
												draggable={!childPlaced}
												ondragstart={(event) => !childPlaced && handleDragStart(event, childDrag)}
												ondragend={handleDragEnd}
											>
												<span class="font-mono text-[10px] text-surface-500">{child.ref_id}</span>
												{child.name}
												{#if childPlaced}
													<i class="fa-solid fa-check text-[9px] text-success-500"></i>
												{/if}
											</li>
										{/each}
									</ul>
								{/if}
							</div>
						{/each}
						{#if items.length === 0}
							<p class="text-xs text-surface-500 px-2 italic">{m.noResultFound()}</p>
						{/if}
					</div>
				{/if}
			</div>
		{/each}
	</div>
</div>
