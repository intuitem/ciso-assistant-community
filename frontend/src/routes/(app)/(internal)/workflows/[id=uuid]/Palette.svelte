<script lang="ts">
	import { m } from '$paraglide/messages';

	interface PaletteItem {
		type: string;
		triggerType?: string;
		icon: string;
		label: string;
	}

	interface Props {
		onAdd: (nodeType: string, triggerType?: string) => void;
	}

	let { onAdd }: Props = $props();

	// Task and subprocess nodes are hidden for the MVP (human tasks land with
	// the TaskNode integration; subprocess needs its mapping UI + recursion
	// guard). The engine still executes them for graphs that carry them.
	const TRIGGER_ITEMS = $derived<PaletteItem[]>([
		{ type: 'trigger', triggerType: 'manual', icon: 'fa-hand-pointer', label: m.triggerManual() },
		{
			type: 'trigger',
			triggerType: 'webhook',
			icon: 'fa-satellite-dish',
			label: m.triggerWebhook()
		},
		{ type: 'trigger', triggerType: 'schedule', icon: 'fa-clock', label: m.triggerSchedule() },
		{
			type: 'trigger',
			triggerType: 'internal_event',
			icon: 'fa-rss',
			label: m.triggerInternalEvent()
		}
	]);
	const STEP_ITEMS = $derived<PaletteItem[]>([
		{ type: 'condition', icon: 'fa-code-branch', label: m.workflowNodeCondition() },
		{ type: 'action', icon: 'fa-bolt', label: m.workflowNodeAction() },
		{ type: 'loop', icon: 'fa-rotate', label: m.workflowNodeLoop() },
		{ type: 'end', icon: 'fa-flag-checkered', label: m.workflowNodeEnd() }
	]);

	let nodeSearch = $state('');
	const GROUPS = $derived(
		[
			{ key: 'triggers', label: m.workflowTriggers(), items: TRIGGER_ITEMS },
			{ key: 'steps', label: m.workflowSteps(), items: STEP_ITEMS }
		]
			.map((group) => ({
				...group,
				items: group.items.filter((item) =>
					item.label.toLowerCase().includes(nodeSearch.trim().toLowerCase())
				)
			}))
			.filter((group) => group.items.length > 0)
	);

	function handleDragStart(event: DragEvent, item: PaletteItem) {
		event.dataTransfer?.setData(
			'application/ciso-workflow-node',
			JSON.stringify({ type: item.type, triggerType: item.triggerType })
		);
		if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move';
	}
</script>

<aside
	class="w-52 shrink-0 h-full border-r border-surface-200-800 bg-surface-100-900 flex flex-col"
>
	<div class="p-3 pb-0 shrink-0">
		<h3 class="text-xs font-semibold uppercase tracking-wide text-surface-600-400 mb-2">
			{m.nodePalette()}
		</h3>
		<div class="relative mb-2">
			<i
				class="fa-solid fa-magnifying-glass absolute left-2 top-1/2 -translate-y-1/2 text-[10px] text-surface-400-600 pointer-events-none"
			></i>
			<input
				type="search"
				class="input w-full text-xs pl-6 pr-1.5 py-1"
				placeholder={m.searchNodeTypes()}
				bind:value={nodeSearch}
				data-testid="palette-search"
			/>
		</div>
	</div>
	<div class="px-3 pb-3 flex-1 min-h-0 overflow-y-auto">
		{#each GROUPS as group (group.key)}
			<h4
				class="text-[10px] font-semibold uppercase tracking-wide text-surface-500 mt-2 mb-1.5 first:mt-0"
			>
				{group.label}
			</h4>
			<div class="flex flex-col gap-1.5">
				{#each group.items as item (item.type + (item.triggerType ?? ''))}
					<button
						type="button"
						draggable="true"
						ondragstart={(e) => handleDragStart(e, item)}
						onclick={() => onAdd(item.type, item.triggerType)}
						class="flex items-center gap-2 px-2.5 py-2 rounded-base border border-surface-200-800 bg-surface-50-950 text-xs text-surface-800-200 cursor-grab hover:border-primary-400 hover:shadow-sm transition-all text-left"
						data-testid="palette-{item.triggerType
							? `${item.type}-${item.triggerType}`
							: item.type}"
					>
						<i class="fa-solid {item.icon} w-4 text-center text-surface-600-400"></i>
						<span class="font-medium">{item.label}</span>
						<i class="fa-solid fa-grip-vertical ml-auto text-[9px] text-surface-400-600"></i>
					</button>
				{/each}
			</div>
		{:else}
			<p class="text-[10px] text-surface-500">{m.noNodeTypeMatches()}</p>
		{/each}
		<p class="mt-3 text-[10px] leading-relaxed text-surface-500">
			{m.workflowBuilderHint()}
		</p>
	</div>
</aside>
