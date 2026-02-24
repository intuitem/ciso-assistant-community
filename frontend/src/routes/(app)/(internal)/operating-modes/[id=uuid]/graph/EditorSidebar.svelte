<script lang="ts">
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';

	interface ElementaryActionItem {
		id: string;
		name: string;
		attack_stage: string;
		icon_fa_class?: string;
	}

	interface Props {
		elementaryActions: ElementaryActionItem[];
		placedNodeIds: Set<string>;
		onDragStart: (action: ElementaryActionItem, e: PointerEvent) => void;
	}

	let { elementaryActions, placedNodeIds, onDragStart }: Props = $props();

	let searchQuery = $state('');

	const STAGE_CONFIG = [
		{ key: 'ebiosReconnaissance', stage: 0, color: 'pink', icon: 'fa-magnifying-glass' },
		{ key: 'ebiosInitialAccess', stage: 1, color: 'violet', icon: 'fa-right-to-bracket' },
		{ key: 'ebiosDiscovery', stage: 2, color: 'orange', icon: 'fa-lightbulb' },
		{ key: 'ebiosExploitation', stage: 3, color: 'red', icon: 'fa-bolt' }
	];

	const STAGE_COLORS: Record<number, string> = {
		0: 'border-pink-400 bg-pink-50',
		1: 'border-violet-400 bg-violet-50',
		2: 'border-orange-400 bg-orange-50',
		3: 'border-red-400 bg-red-50'
	};

	const STAGE_BADGE_COLORS: Record<number, string> = {
		0: 'bg-pink-200 text-pink-800',
		1: 'bg-violet-200 text-violet-800',
		2: 'bg-orange-200 text-orange-800',
		3: 'bg-red-200 text-red-800'
	};

	// Map attack_stage display strings to numeric stages
	function getStageNumber(attackStage: string): number {
		if (attackStage.includes('Reconnaissance') || attackStage === 'ebiosReconnaissance')
			return 0;
		if (attackStage.includes('Initial') || attackStage === 'ebiosInitialAccess') return 1;
		if (attackStage.includes('Discovery') || attackStage === 'ebiosDiscovery') return 2;
		if (attackStage.includes('Exploitation') || attackStage === 'ebiosExploitation') return 3;
		return 0;
	}

	const groupedActions = $derived(() => {
		const groups: Record<number, ElementaryActionItem[]> = { 0: [], 1: [], 2: [], 3: [] };
		for (const ea of elementaryActions) {
			const stage = getStageNumber(ea.attack_stage);
			if (!groups[stage]) groups[stage] = [];
			const matchesSearch =
				!searchQuery ||
				ea.name.toLowerCase().includes(searchQuery.toLowerCase());
			if (matchesSearch) {
				groups[stage].push(ea);
			}
		}
		return groups;
	});

	let collapsedStages = $state(new Set<number>());

	function toggleStage(stage: number) {
		const next = new Set(collapsedStages);
		if (next.has(stage)) {
			next.delete(stage);
		} else {
			next.add(stage);
		}
		collapsedStages = next;
	}
</script>

<div class="w-64 bg-white border-r border-gray-200 flex flex-col h-full overflow-hidden">
	<div class="p-3 border-b border-gray-200">
		<h3 class="text-sm font-semibold text-gray-700 mb-2">
			{m.elementaryActions()}
		</h3>
		<input
			type="text"
			placeholder={m.searchPlaceholder()}
			bind:value={searchQuery}
			class="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:border-violet-500"
		/>
	</div>

	<div class="flex-1 overflow-y-auto p-2 space-y-2">
		{#each STAGE_CONFIG as stageConfig}
			{@const actions = groupedActions()[stageConfig.stage] ?? []}
			<div>
				<button
					class="w-full flex items-center justify-between px-2 py-1.5 text-xs font-semibold text-gray-600 hover:bg-gray-50 rounded"
					onclick={() => toggleStage(stageConfig.stage)}
				>
					<span class="flex items-center gap-1.5">
						<i class="fa-solid {stageConfig.icon} text-{stageConfig.color}-500"></i>
						{safeTranslate(stageConfig.key)}
					</span>
					<span class="flex items-center gap-1">
						<span class="text-gray-400">{actions.length}</span>
						<i
							class="fa-solid fa-chevron-{collapsedStages.has(stageConfig.stage)
								? 'right'
								: 'down'} text-[10px] text-gray-400"
						></i>
					</span>
				</button>

				{#if !collapsedStages.has(stageConfig.stage)}
					<div class="space-y-1 mt-1">
						{#each actions as action}
							{@const isPlaced = placedNodeIds.has(action.id)}
							<div
								class="flex items-center gap-2 px-2 py-1.5 rounded border text-xs
									{isPlaced
									? 'border-gray-200 bg-gray-100 text-gray-400 cursor-not-allowed opacity-50'
									: STAGE_COLORS[stageConfig.stage] + ' cursor-grab hover:shadow-sm'}"
								role={isPlaced ? 'presentation' : 'button'}
								onpointerdown={(e) => {
									if (!isPlaced) onDragStart(action, e);
								}}
							>
								{#if action.icon_fa_class}
									<i class="{action.icon_fa_class} text-[10px]"></i>
								{/if}
								<span class="truncate flex-1">{action.name}</span>
								{#if isPlaced}
									<i class="fa-solid fa-check text-[10px] text-green-500"></i>
								{/if}
							</div>
						{/each}
						{#if actions.length === 0}
							<p class="text-xs text-gray-400 px-2 italic">{m.noResultFound()}</p>
						{/if}
					</div>
				{/if}
			</div>
		{/each}
	</div>
</div>
