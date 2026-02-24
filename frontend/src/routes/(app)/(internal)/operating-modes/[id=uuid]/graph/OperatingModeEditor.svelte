<script lang="ts">
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import ActionNode from './nodes/ActionNode.svelte';
	import LogicGateNode from './nodes/LogicGateNode.svelte';
	import EditorSidebar from './EditorSidebar.svelte';
	import { enhance } from '$app/forms';

	// ---- Types ----

	interface ElementaryActionItem {
		id: string;
		name: string;
		attack_stage: string;
		icon_fa_class?: string;
	}

	interface CanvasNode {
		id: string;
		elementaryActionId: string;
		label: string;
		iconClass: string;
		stage: number;
		x: number;
		y: number;
	}

	interface Edge {
		id: string;
		sourceId: string;
		targetId: string;
	}

	interface KillChainStep {
		elementary_action: any;
		antecedents: any[];
		logic_operator?: string | null;
	}

	// ---- Props ----

	interface Props {
		elementaryActions: ElementaryActionItem[];
		killChainSteps: KillChainStep[];
		operatingModeId: string;
		graphData: {
			nodes: any[];
			links: any[];
			panelNodes: Record<string, string[]>;
		};
		onSaved?: () => void;
	}

	let { elementaryActions, killChainSteps, operatingModeId, graphData, onSaved }: Props =
		$props();

	// ---- Constants ----

	const PANEL_WIDTH = 200;
	const PANEL_GAP = 60;
	const PANEL_PADDING_TOP = 60;
	const NODE_VERTICAL_GAP = 70;
	const CANVAS_PADDING = 40;
	const TOTAL_WIDTH = 4 * PANEL_WIDTH + 3 * PANEL_GAP + 2 * CANVAS_PADDING;

	const STAGE_LABELS = [
		{ key: 'ebiosReconnaissance', icon: '\uf002', color: '#ec4899' },
		{ key: 'ebiosInitialAccess', icon: '\uf504', color: '#8b5cf6' },
		{ key: 'ebiosDiscovery', icon: '\uf0eb', color: '#f97316' },
		{ key: 'ebiosExploitation', icon: '\uf0e7', color: '#ef4444' }
	];

	const STAGE_BG = ['#fdf2f8', '#f5f3ff', '#fff7ed', '#fef2f2'];
	const STAGE_BORDER = ['#fbcfe8', '#ddd6fe', '#fed7aa', '#fecaca'];

	// ---- State ----

	let canvasNodes = $state<CanvasNode[]>([]);
	let edges = $state<Edge[]>([]);
	let logicOps = $state<Map<string, 'AND' | 'OR'>>(new Map());
	let selectedNodeId = $state<string | null>(null);
	let drawing = $state<{ fromId: string; x: number; y: number } | null>(null);
	let draggingNode = $state<{ nodeId: string; offsetX: number; offsetY: number } | null>(null);
	let dragGhost = $state<{
		action: ElementaryActionItem;
		x: number;
		y: number;
	} | null>(null);
	let saving = $state(false);
	let dirty = $state(false);
	let svgEl: SVGSVGElement | undefined = $state(undefined);

	// Pan/zoom state
	let viewBox = $state({ x: 0, y: 0, w: TOTAL_WIDTH, h: 600 });
	let isPanning = $state(false);
	let panStart = $state({ x: 0, y: 0, vx: 0, vy: 0 });

	// ---- Stage helpers ----

	function getStageNumber(attackStage: string): number {
		if (attackStage.includes('Reconnaissance') || attackStage === 'ebiosReconnaissance') return 0;
		if (attackStage.includes('Initial') || attackStage === 'ebiosInitialAccess') return 1;
		if (attackStage.includes('Discovery') || attackStage === 'ebiosDiscovery') return 2;
		if (attackStage.includes('Exploitation') || attackStage === 'ebiosExploitation') return 3;
		return 0;
	}

	function getPanelX(stage: number): number {
		return CANVAS_PADDING + stage * (PANEL_WIDTH + PANEL_GAP);
	}

	function getPanelCenterX(stage: number): number {
		return getPanelX(stage) + PANEL_WIDTH / 2;
	}

	function getStageFromX(x: number): number {
		for (let s = 3; s >= 0; s--) {
			if (x >= getPanelX(s)) return s;
		}
		return 0;
	}

	// ---- Initialize from existing data ----

	function initFromKillChain() {
		const nodes: CanvasNode[] = [];
		const edgeList: Edge[] = [];
		const ops = new Map<string, 'AND' | 'OR'>();

		// Track node counts per stage for positioning
		const stageCount: Record<number, number> = { 0: 0, 1: 0, 2: 0, 3: 0 };

		// Build a set of elementary action IDs that are in kill chain steps
		const kcEaIds = new Set<string>();
		for (const step of killChainSteps) {
			const eaId =
				typeof step.elementary_action === 'object'
					? step.elementary_action.id
					: step.elementary_action;
			kcEaIds.add(eaId);
		}

		// Create nodes for each kill chain step
		for (const step of killChainSteps) {
			const eaId =
				typeof step.elementary_action === 'object'
					? step.elementary_action.id
					: step.elementary_action;
			const ea = elementaryActions.find((a) => a.id === eaId);
			if (!ea) continue;

			const stage = getStageNumber(ea.attack_stage);
			const count = stageCount[stage] ?? 0;

			nodes.push({
				id: eaId,
				elementaryActionId: eaId,
				label: ea.name,
				iconClass: ea.icon_fa_class ?? '',
				stage,
				x: getPanelCenterX(stage),
				y: PANEL_PADDING_TOP + 40 + count * NODE_VERTICAL_GAP
			});
			stageCount[stage] = count + 1;

			// Edges from antecedents
			const antecedents = step.antecedents ?? [];
			for (const ant of antecedents) {
				const antId = typeof ant === 'object' ? ant.id : ant;
				edgeList.push({
					id: `${antId}-${eaId}`,
					sourceId: antId,
					targetId: eaId
				});
			}

			// Logic operator
			if (step.logic_operator && antecedents.length > 1) {
				ops.set(eaId, step.logic_operator as 'AND' | 'OR');
			}
		}

		canvasNodes = nodes;
		edges = edgeList;
		logicOps = ops;
	}

	$effect(() => {
		initFromKillChain();
	});

	// ---- Derived state ----

	const placedNodeIds = $derived(new Set(canvasNodes.map((n) => n.id)));

	// Compute logic gate positions: for nodes with 2+ antecedents
	const logicGates = $derived(() => {
		const gates: { id: string; targetId: string; x: number; y: number; operator: 'AND' | 'OR' }[] =
			[];
		const edgesByTarget = new Map<string, Edge[]>();
		for (const edge of edges) {
			const list = edgesByTarget.get(edge.targetId) ?? [];
			list.push(edge);
			edgesByTarget.set(edge.targetId, list);
		}

		for (const [targetId, targetEdges] of edgesByTarget) {
			if (targetEdges.length < 2) continue;
			const targetNode = canvasNodes.find((n) => n.id === targetId);
			if (!targetNode) continue;

			// Position gate between sources and target
			let avgSourceX = 0;
			let avgSourceY = 0;
			let count = 0;
			for (const edge of targetEdges) {
				const src = canvasNodes.find((n) => n.id === edge.sourceId);
				if (src) {
					avgSourceX += src.x;
					avgSourceY += src.y;
					count++;
				}
			}
			if (count > 0) {
				avgSourceX /= count;
				avgSourceY /= count;
			}

			gates.push({
				id: `gate-${targetId}`,
				targetId,
				x: (avgSourceX + targetNode.x) / 2,
				y: (avgSourceY + targetNode.y) / 2,
				operator: logicOps.get(targetId) ?? 'AND'
			});
		}
		return gates;
	});

	// Compute canvas height based on node positions
	const canvasHeight = $derived(() => {
		let maxY = 400;
		for (const node of canvasNodes) {
			if (node.y + 60 > maxY) maxY = node.y + 60;
		}
		return maxY + 100;
	});

	// ---- SVG coordinate conversion ----

	function svgPoint(e: PointerEvent): { x: number; y: number } {
		if (!svgEl) return { x: e.clientX, y: e.clientY };
		const rect = svgEl.getBoundingClientRect();
		const scaleX = viewBox.w / rect.width;
		const scaleY = viewBox.h / rect.height;
		return {
			x: viewBox.x + (e.clientX - rect.left) * scaleX,
			y: viewBox.y + (e.clientY - rect.top) * scaleY
		};
	}

	// ---- Drag from sidebar ----

	function handleSidebarDragStart(action: ElementaryActionItem, e: PointerEvent) {
		dragGhost = { action, x: e.clientX, y: e.clientY };

		function onMove(ev: PointerEvent) {
			if (dragGhost) {
				dragGhost = { ...dragGhost, x: ev.clientX, y: ev.clientY };
			}
		}

		function onUp(ev: PointerEvent) {
			window.removeEventListener('pointermove', onMove);
			window.removeEventListener('pointerup', onUp);
			if (dragGhost) {
				const pt = svgPoint(ev);
				const stage = getStageFromX(pt.x);
				const expectedStage = getStageNumber(action.attack_stage);

				// Only allow dropping in the correct stage panel
				if (stage === expectedStage) {
					addNode(action, pt.x, pt.y, stage);
				}
				dragGhost = null;
			}
		}

		window.addEventListener('pointermove', onMove);
		window.addEventListener('pointerup', onUp);
	}

	function addNode(action: ElementaryActionItem, x: number, y: number, stage: number) {
		if (placedNodeIds.has(action.id)) return;

		// Snap x to panel center
		const cx = getPanelCenterX(stage);

		// Find next available y
		const nodesInStage = canvasNodes.filter((n) => n.stage === stage);
		const maxY = nodesInStage.reduce(
			(max, n) => Math.max(max, n.y),
			PANEL_PADDING_TOP + 40 - NODE_VERTICAL_GAP
		);

		canvasNodes = [
			...canvasNodes,
			{
				id: action.id,
				elementaryActionId: action.id,
				label: action.name,
				iconClass: action.icon_fa_class ?? '',
				stage,
				x: cx,
				y: Math.max(y, maxY + NODE_VERTICAL_GAP)
			}
		];
		dirty = true;
	}

	// ---- Node dragging ----

	function handleNodePointerDown(nodeId: string, e: PointerEvent) {
		selectedNodeId = nodeId;
		const node = canvasNodes.find((n) => n.id === nodeId);
		if (!node) return;
		const pt = svgPoint(e);
		draggingNode = { nodeId, offsetX: pt.x - node.x, offsetY: pt.y - node.y };

		function onMove(ev: PointerEvent) {
			if (!draggingNode) return;
			const pt2 = svgPoint(ev);
			const n = canvasNodes.find((n) => n.id === draggingNode!.nodeId);
			if (!n) return;

			// Constrain to stage column
			const panelX = getPanelX(n.stage);
			const newX = Math.max(
				panelX + 70,
				Math.min(panelX + PANEL_WIDTH - 70, pt2.x - draggingNode!.offsetX)
			);
			const newY = Math.max(PANEL_PADDING_TOP + 20, pt2.y - draggingNode!.offsetY);

			canvasNodes = canvasNodes.map((cn) =>
				cn.id === draggingNode!.nodeId ? { ...cn, x: newX, y: newY } : cn
			);
		}

		function onUp() {
			window.removeEventListener('pointermove', onMove);
			window.removeEventListener('pointerup', onUp);
			draggingNode = null;
			dirty = true;
		}

		window.addEventListener('pointermove', onMove);
		window.addEventListener('pointerup', onUp);
	}

	// ---- Connection drawing ----

	function handleOutputPointerDown(nodeId: string, e: PointerEvent) {
		const pt = svgPoint(e);
		drawing = { fromId: nodeId, x: pt.x, y: pt.y };

		function onMove(ev: PointerEvent) {
			if (!drawing) return;
			const pt2 = svgPoint(ev);
			drawing = { ...drawing, x: pt2.x, y: pt2.y };
		}

		function onUp() {
			window.removeEventListener('pointermove', onMove);
			window.removeEventListener('pointerup', onUp);
			drawing = null;
		}

		window.addEventListener('pointermove', onMove);
		window.addEventListener('pointerup', onUp);
	}

	function handleInputPointerUp(targetId: string, _e: PointerEvent) {
		if (!drawing) return;
		const sourceId = drawing.fromId;
		drawing = null;

		// Validate connection
		if (sourceId === targetId) return;
		const sourceNode = canvasNodes.find((n) => n.id === sourceId);
		const targetNode = canvasNodes.find((n) => n.id === targetId);
		if (!sourceNode || !targetNode) return;

		// Stage validation: source stage must be <= target stage
		if (sourceNode.stage > targetNode.stage) return;

		// KNOW stage can't have antecedents
		if (targetNode.stage === 0) return;

		// Check duplicate
		if (edges.some((e) => e.sourceId === sourceId && e.targetId === targetId)) return;

		edges = [...edges, { id: `${sourceId}-${targetId}`, sourceId, targetId }];

		// Auto-set AND if this is the second antecedent
		const targetEdges = edges.filter((e) => e.targetId === targetId);
		if (targetEdges.length === 2 && !logicOps.has(targetId)) {
			logicOps = new Map(logicOps).set(targetId, 'AND');
		}

		dirty = true;
	}

	// ---- Delete ----

	function handleDeleteNode(nodeId: string) {
		canvasNodes = canvasNodes.filter((n) => n.id !== nodeId);
		edges = edges.filter((e) => e.sourceId !== nodeId && e.targetId !== nodeId);
		const newOps = new Map(logicOps);
		newOps.delete(nodeId);
		logicOps = newOps;
		selectedNodeId = null;
		dirty = true;
	}

	function handleDeleteEdge(edgeId: string) {
		const edge = edges.find((e) => e.id === edgeId);
		edges = edges.filter((e) => e.id !== edgeId);

		// If target now has <= 1 antecedent, remove logic operator
		if (edge) {
			const remaining = edges.filter((e) => e.targetId === edge.targetId);
			if (remaining.length <= 1) {
				const newOps = new Map(logicOps);
				newOps.delete(edge.targetId);
				logicOps = newOps;
			}
		}
		dirty = true;
	}

	// ---- Logic gate toggle ----

	function handleToggleGate(gateId: string) {
		// gateId is "gate-{targetNodeId}"
		const targetId = gateId.replace('gate-', '');
		const current = logicOps.get(targetId) ?? 'AND';
		logicOps = new Map(logicOps).set(targetId, current === 'AND' ? 'OR' : 'AND');
		dirty = true;
	}

	// ---- Pan/Zoom ----

	function handleWheel(e: WheelEvent) {
		e.preventDefault();
		const zoomFactor = e.deltaY > 0 ? 1.1 : 0.9;
		const newW = viewBox.w * zoomFactor;
		const newH = viewBox.h * zoomFactor;
		// Zoom toward cursor
		if (!svgEl) return;
		const rect = svgEl.getBoundingClientRect();
		const mx = (e.clientX - rect.left) / rect.width;
		const my = (e.clientY - rect.top) / rect.height;
		viewBox = {
			x: viewBox.x + (viewBox.w - newW) * mx,
			y: viewBox.y + (viewBox.h - newH) * my,
			w: newW,
			h: newH
		};
	}

	function handleBgPointerDown(e: PointerEvent) {
		if (e.target === svgEl || (e.target as Element)?.classList?.contains('canvas-bg')) {
			selectedNodeId = null;
			isPanning = true;
			panStart = { x: e.clientX, y: e.clientY, vx: viewBox.x, vy: viewBox.y };

			function onMove(ev: PointerEvent) {
				if (!isPanning) return;
				const rect = svgEl!.getBoundingClientRect();
				const scaleX = viewBox.w / rect.width;
				const scaleY = viewBox.h / rect.height;
				viewBox = {
					...viewBox,
					x: panStart.vx - (ev.clientX - panStart.x) * scaleX,
					y: panStart.vy - (ev.clientY - panStart.y) * scaleY
				};
			}

			function onUp() {
				isPanning = false;
				window.removeEventListener('pointermove', onMove);
				window.removeEventListener('pointerup', onUp);
			}

			window.addEventListener('pointermove', onMove);
			window.addEventListener('pointerup', onUp);
		}
	}

	// ---- Edge path computation ----

	function edgePath(
		sourceId: string,
		targetId: string,
		gateNode?: { x: number; y: number }
	): string {
		const src = canvasNodes.find((n) => n.id === sourceId);
		const tgt = gateNode ?? canvasNodes.find((n) => n.id === targetId);
		if (!src || !tgt) return '';

		const sx = src.x + 70; // right handle
		const sy = src.y;
		const tx = gateNode ? tgt.x - 18 : (canvasNodes.find((n) => n.id === targetId)?.x ?? 0) - 70;
		const ty = tgt.y;

		const dx = (tx - sx) / 2;
		return `M${sx},${sy} C${sx + dx},${sy} ${tx - dx},${ty} ${tx},${ty}`;
	}

	function gateToTargetPath(gate: { x: number; y: number }, targetId: string): string {
		const tgt = canvasNodes.find((n) => n.id === targetId);
		if (!tgt) return '';
		const sx = gate.x + 18;
		const sy = gate.y;
		const tx = tgt.x - 70;
		const ty = tgt.y;
		const dx = (tx - sx) / 2;
		return `M${sx},${sy} C${sx + dx},${sy} ${tx - dx},${ty} ${tx},${ty}`;
	}

	// ---- Save ----

	function buildKillChainStepsJson(): string {
		const steps: any[] = [];
		for (const node of canvasNodes) {
			const antecedentIds = edges
				.filter((e) => e.targetId === node.id)
				.map((e) => e.sourceId);

			steps.push({
				elementary_action: node.elementaryActionId,
				antecedents: antecedentIds,
				logic_operator:
					antecedentIds.length > 1 ? logicOps.get(node.id) ?? 'AND' : null,
				is_highlighted: false
			});
		}
		return JSON.stringify(steps);
	}

	// ---- Keyboard ----

	function handleKeyDown(e: KeyboardEvent) {
		if (e.key === 'Delete' || e.key === 'Backspace') {
			if (selectedNodeId) {
				handleDeleteNode(selectedNodeId);
			}
		}
		if (e.key === 'Escape') {
			selectedNodeId = null;
			drawing = null;
		}
	}
</script>

<svelte:window onkeydown={handleKeyDown} />

<div class="flex h-[80vh] bg-gray-50 rounded-lg overflow-hidden border border-gray-200">
	<!-- Sidebar -->
	<EditorSidebar
		{elementaryActions}
		{placedNodeIds}
		onDragStart={handleSidebarDragStart}
	/>

	<!-- Canvas area -->
	<div class="flex-1 flex flex-col overflow-hidden">
		<!-- Toolbar -->
		<div
			class="flex items-center justify-between px-4 py-2 bg-white border-b border-gray-200"
		>
			<div class="flex items-center gap-2 text-sm text-gray-500">
				<i class="fa-solid fa-info-circle"></i>
				<span>{m.graphEditorHelp()}</span>
			</div>
			<div class="flex items-center gap-2">
				{#if dirty}
					<span class="text-xs text-amber-600 flex items-center gap-1">
						<i class="fa-solid fa-circle text-[6px]"></i>
						{m.unsavedChanges()}
					</span>
				{/if}
				<form
					method="POST"
					action="?/saveGraph"
					use:enhance={() => {
						saving = true;
						return async ({ update }) => {
							saving = false;
							dirty = false;
							onSaved?.();
							await update();
						};
					}}
				>
					<input type="hidden" name="kill_chain_steps" value={buildKillChainStepsJson()} />
					<button
						type="submit"
						class="btn preset-filled-primary-500 text-sm px-4 py-1.5"
						disabled={saving || !dirty}
					>
						{#if saving}
							<i class="fa-solid fa-spinner fa-spin mr-1"></i>
						{:else}
							<i class="fa-solid fa-save mr-1"></i>
						{/if}
						{m.save()}
					</button>
				</form>
			</div>
		</div>

		<!-- SVG Canvas -->
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<svg
			bind:this={svgEl}
			class="flex-1 w-full"
			viewBox="{viewBox.x} {viewBox.y} {viewBox.w} {viewBox.h}"
			onwheel={handleWheel}
			onpointerdown={handleBgPointerDown}
			style="touch-action: none"
		>
			<!-- Background -->
			<rect
				class="canvas-bg"
				x={viewBox.x - 1000}
				y={viewBox.y - 1000}
				width={viewBox.w + 2000}
				height={viewBox.h + 2000}
				fill="#f8fafc"
			/>

			<!-- Stage panels -->
			{#each STAGE_LABELS as stageLabel, i}
				{@const px = getPanelX(i)}
				{@const ph = canvasHeight()}
				<rect
					x={px}
					y={0}
					width={PANEL_WIDTH}
					height={ph}
					rx="8"
					fill={STAGE_BG[i]}
					stroke={STAGE_BORDER[i]}
					stroke-width="1"
					stroke-dasharray="6 3"
				/>
				<!-- Stage label -->
				<text
					x={px + PANEL_WIDTH / 2}
					y={28}
					font-size="13"
					font-weight="700"
					fill={stageLabel.color}
					text-anchor="middle"
				>
					{safeTranslate(stageLabel.key)}
				</text>
			{/each}

			<!-- Edges -->
			{#each edges as edge}
				{@const targetEdges = edges.filter((e) => e.targetId === edge.targetId)}
				{@const gate = targetEdges.length >= 2
					? logicGates().find((g) => g.targetId === edge.targetId)
					: null}

				{#if gate}
					<!-- Edge goes to logic gate -->
					<path
						d={edgePath(edge.sourceId, edge.targetId, gate)}
						fill="none"
						stroke="#8FA1B9"
						stroke-width="1.5"
						class="pointer-events-none"
					/>
				{:else}
					<!-- Direct edge -->
					<!-- svelte-ignore a11y_no_static_element_interactions -->
					<g>
						<path
							d={edgePath(edge.sourceId, edge.targetId)}
							fill="none"
							stroke="#8FA1B9"
							stroke-width="1.5"
						/>
						<!-- Invisible wider path for click target -->
						<path
							d={edgePath(edge.sourceId, edge.targetId)}
							fill="none"
							stroke="transparent"
							stroke-width="12"
							class="cursor-pointer"
							onpointerdown={(e) => {
								e.stopPropagation();
								handleDeleteEdge(edge.id);
							}}
						/>
						<!-- Arrow head -->
						{#if canvasNodes.find((n) => n.id === edge.targetId)}
							{@const tgt = canvasNodes.find((n) => n.id === edge.targetId)}
							{#if tgt}
								<polygon
									points="-6,-4 0,0 -6,4"
									transform="translate({tgt.x - 70}, {tgt.y})"
									fill="#4D179A"
								/>
							{/if}
						{/if}
					</g>
				{/if}
			{/each}

			<!-- Gate-to-target edges -->
			{#each logicGates() as gate}
				{@const tgt = canvasNodes.find((n) => n.id === gate.targetId)}
				<path
					d={gateToTargetPath(gate, gate.targetId)}
					fill="none"
					stroke="#8FA1B9"
					stroke-width="1.5"
					class="pointer-events-none"
				/>
				<!-- Arrow head -->
				{#if tgt}
					<polygon
						points="-6,-4 0,0 -6,4"
						transform="translate({tgt.x - 70}, {tgt.y})"
						fill="#4D179A"
					/>
				{/if}
			{/each}

			<!-- Drawing preview -->
			{#if drawing}
				{@const srcNode = canvasNodes.find((n) => n.id === drawing.fromId)}
				{#if srcNode}
					<line
						x1={srcNode.x + 70}
						y1={srcNode.y}
						x2={drawing.x}
						y2={drawing.y}
						stroke="#4D179A"
						stroke-width="2"
						stroke-dasharray="6 3"
						class="pointer-events-none"
					/>
				{/if}
			{/if}

			<!-- Logic gate nodes -->
			{#each logicGates() as gate}
				<LogicGateNode
					id={gate.id}
					x={gate.x}
					y={gate.y}
					operator={gate.operator}
					onToggle={handleToggleGate}
				/>
			{/each}

			<!-- Action nodes -->
			{#each canvasNodes as node}
				<ActionNode
					id={node.id}
					x={node.x}
					y={node.y}
					label={node.label}
					iconClass={node.iconClass}
					stage={node.stage}
					selected={selectedNodeId === node.id}
					onPointerDownNode={handleNodePointerDown}
					onPointerDownOutput={handleOutputPointerDown}
					onPointerUpInput={handleInputPointerUp}
					onDelete={handleDeleteNode}
				/>
			{/each}
		</svg>
	</div>

	<!-- Drag ghost overlay -->
	{#if dragGhost}
		<div
			class="fixed pointer-events-none z-50 bg-white border border-violet-400 shadow-lg rounded px-3 py-1.5 text-xs font-medium text-gray-700 opacity-80"
			style="left: {dragGhost.x + 12}px; top: {dragGhost.y - 10}px;"
		>
			{dragGhost.action.name}
		</div>
	{/if}
</div>
