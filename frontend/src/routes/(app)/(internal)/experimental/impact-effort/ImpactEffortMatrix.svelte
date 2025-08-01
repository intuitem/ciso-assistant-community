<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	interface Task {
		id: number;
		name: string;
		description?: string;
		impact: number;
		effort: number;
		category?: string;
	}

	interface CellData {
		impact: number;
		effort: number;
		tasks: Task[];
		count: number;
	}

	interface Props {
		tasks: Task[];
		width?: number;
		height?: number;
		showQuadrantLabels?: boolean;
		showGrid?: boolean;
		classContainer?: string;
	}

	let {
		tasks,
		width = 800,
		height = 600,
		showQuadrantLabels = true,
		showGrid = true,
		classContainer = ''
	}: Props = $props();

	// State
	let selectedCell: { impact: number; effort: number } | null = $state(null);
	let hoveredCell: { impact: number; effort: number } | null = $state(null);

	const dispatch = createEventDispatcher();

	// Calculate cell positions and group tasks
	const cellData = $derived(calculateCellData(tasks));
	const selectedTasks = $derived(
		selectedCell ? cellData[`${selectedCell.impact}-${selectedCell.effort}`]?.tasks || [] : []
	);

	function calculateCellData(tasks: Task[]): Record<string, CellData> {
		const cells: Record<string, CellData> = {};

		// Group tasks by impact/effort coordinates
		tasks.forEach((task) => {
			const key = `${task.impact}-${task.effort}`;
			if (!cells[key]) {
				cells[key] = {
					impact: task.impact,
					effort: task.effort,
					tasks: [],
					count: 0
				};
			}
			cells[key].tasks.push(task);
			cells[key].count++;
		});

		return cells;
	}

	function getPosition(impact: number, effort: number): { x: number; y: number } {
		// Convert 1-5 scale to SVG coordinates with padding
		const padding = 60;
		const chartWidth = width - padding * 2;
		const chartHeight = height - padding * 2;

		const x = padding + ((effort - 1) / 4) * chartWidth;
		const y = padding + ((5 - impact) / 4) * chartHeight; // Inverted Y for SVG

		return { x, y };
	}

	function getCircleRadius(count: number): number {
		// Scale radius based on number of tasks (min 8, max 30)
		const minRadius = 8;
		const maxRadius = 30;
		const maxCount = Math.max(...Object.values(cellData).map((cell) => cell.count));

		// If all cells have same count, return middle size
		if (maxCount === 1) return (minRadius + maxRadius) / 2;

		return minRadius + ((count - 1) / (maxCount - 1)) * (maxRadius - minRadius);
	}

	function getQuadrantClass(impact: number, effort: number): string {
		if (impact >= 4 && effort <= 2) return 'quick-wins';
		if (impact >= 4 && effort >= 3) return 'major-projects';
		if (impact <= 3 && effort <= 2) return 'fill-ins';
		return 'questionable';
	}

	function handleCellClick(cell: CellData): void {
		selectedCell =
			selectedCell?.impact === cell.impact && selectedCell?.effort === cell.effort
				? null
				: { impact: cell.impact, effort: cell.effort };

		dispatch('cellSelected', {
			cell: selectedCell,
			tasks: selectedTasks
		});
	}

	function handleTaskClick(task: Task): void {
		dispatch('taskSelected', { task });
	}

	function getPriorityScore(task: Task): string {
		// Simple impact/effort ratio
		return (task.impact / task.effort).toFixed(2);
	}

	// Sort tasks by priority score
	const sortedSelectedTasks = $derived(
		selectedTasks
			.slice()
			.sort((a, b) => parseFloat(getPriorityScore(b)) - parseFloat(getPriorityScore(a)))
	);
</script>

<div class="matrix-container {classContainer}">
	<!-- Matrix Section -->
	<div class="matrix-section">
		<svg {width} {height} class="matrix-svg">
			<!-- Background quadrants -->
			{#if showQuadrantLabels}
				<!-- Quick Wins - top left -->
				<rect
					x="60"
					y="60"
					width={(width - 120) * 0.4}
					height={(height - 120) * 0.4}
					class="quadrant quick-wins-bg"
				/>
				<!-- Major Projects - top right -->
				<rect
					x={60 + (width - 120) * 0.4}
					y="60"
					width={(width - 120) * 0.6}
					height={(height - 120) * 0.4}
					class="quadrant major-projects-bg"
				/>
				<!-- Fill-ins - bottom left -->
				<rect
					x="60"
					y={60 + (height - 120) * 0.4}
					width={(width - 120) * 0.4}
					height={(height - 120) * 0.6}
					class="quadrant fill-ins-bg"
				/>
				<!-- Questionable - bottom right -->
				<rect
					x={60 + (width - 120) * 0.4}
					y={60 + (height - 120) * 0.4}
					width={(width - 120) * 0.6}
					height={(height - 120) * 0.6}
					class="quadrant questionable-bg"
				/>
			{/if}

			<!-- Grid lines -->
			{#if showGrid}
				{#each [1, 2, 3, 4, 5] as i}
					<!-- Vertical lines -->
					<line
						x1={60 + ((i - 1) / 4) * (width - 120)}
						y1="60"
						x2={60 + ((i - 1) / 4) * (width - 120)}
						y2={height - 60}
						class="grid-line"
					/>
					<!-- Horizontal lines -->
					<line
						x1="60"
						y1={60 + ((i - 1) / 4) * (height - 120)}
						x2={width - 60}
						y2={60 + ((i - 1) / 4) * (height - 120)}
						class="grid-line"
					/>
				{/each}
			{/if}

			<!-- Axis labels -->
			<text x={width / 2} y={height - 20} text-anchor="middle" class="axis-label"> Effort → </text>
			<text
				x="25"
				y={height / 2}
				text-anchor="middle"
				class="axis-label"
				transform="rotate(-90, 25, {height / 2})"
			>
				Impact →
			</text>

			<!-- Axis ticks -->
			{#each [1, 2, 3, 4, 5] as i}
				<!-- X-axis ticks -->
				<text
					x={60 + ((i - 1) / 4) * (width - 120)}
					y={height - 35}
					text-anchor="middle"
					class="tick-label"
				>
					{i}
				</text>
				<!-- Y-axis ticks -->
				<text
					x="45"
					y={65 + ((5 - i) / 4) * (height - 120)}
					text-anchor="middle"
					class="tick-label"
				>
					{i}
				</text>
			{/each}

			<!-- Quadrant labels -->
			{#if showQuadrantLabels}
				<text x="150" y="85" class="quadrant-label">Quick Wins</text>
				<text x={width - 150} y="85" class="quadrant-label" text-anchor="end">Major Projects</text>
				<text x="150" y={height - 85} class="quadrant-label">Fill-ins</text>
				<text x={width - 150} y={height - 85} class="quadrant-label" text-anchor="end"
					>Questionable</text
				>
			{/if}

			<!-- Data points -->
			{#each Object.values(cellData) as cell}
				{#if cell.count > 0}
					{@const position = getPosition(cell.impact, cell.effort)}
					{@const radius = getCircleRadius(cell.count)}
					{@const isSelected =
						selectedCell?.impact === cell.impact && selectedCell?.effort === cell.effort}
					{@const isHovered =
						hoveredCell?.impact === cell.impact && hoveredCell?.effort === cell.effort}

					<circle
						cx={position.x}
						cy={position.y}
						r={radius}
						class="data-point {getQuadrantClass(cell.impact, cell.effort)}"
						class:selected={isSelected}
						class:hovered={isHovered}
						onclick={() => handleCellClick(cell)}
						onmouseenter={() => (hoveredCell = { impact: cell.impact, effort: cell.effort })}
						onmouseleave={() => (hoveredCell = null)}
						role="button"
						tabindex="0"
						aria-label="Impact {cell.impact}, Effort {cell.effort}: {cell.count} task{cell.count ===
						1
							? ''
							: 's'}"
					/>

					<!-- Task count label -->
					<text
						x={position.x}
						y={position.y}
						text-anchor="middle"
						dominant-baseline="central"
						class="count-label"
						class:selected={isSelected}
						style="pointer-events: none;"
					>
						{cell.count}
					</text>
				{/if}
			{/each}
		</svg>
	</div>

	<!-- Side Panel -->
	<div class="side-panel">
		<div class="panel-header">
			<h3>
				{#if selectedCell}
					Tasks: Impact {selectedCell.impact}, Effort {selectedCell.effort}
					<span class="task-count">({selectedTasks.length})</span>
				{:else}
					Select a circle to view tasks
				{/if}
			</h3>
		</div>

		<div class="task-list">
			{#if selectedTasks.length > 0}
				{#each sortedSelectedTasks as task, index}
					<div class="task-item" onclick={() => handleTaskClick(task)} role="button" tabindex="0">
						<div class="task-header">
							<span class="task-rank">#{index + 1}</span>
							<span class="task-name">{task.name}</span>
							<span class="priority-score">{getPriorityScore(task)}</span>
						</div>
						{#if task.description}
							<div class="task-description">{task.description}</div>
						{/if}
						<div class="task-meta">
							<span class="meta-item">Impact: {task.impact}</span>
							<span class="meta-item">Effort: {task.effort}</span>
							{#if task.category}
								<span class="meta-item category">{task.category}</span>
							{/if}
						</div>
					</div>
				{/each}
			{:else if selectedCell}
				<div class="empty-state">No tasks found for this position.</div>
			{:else}
				<div class="empty-state">Click on a circle in the matrix to view associated tasks.</div>
			{/if}
		</div>
	</div>
</div>

<style>
	.matrix-container {
		display: flex;
		gap: 20px;
		max-width: 1400px;
		margin: 0 auto;
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
	}

	.matrix-section {
		flex: 1;
		min-width: 600px;
	}

	.matrix-svg {
		border: 2px solid #e9ecef;
		border-radius: 8px;
		background: white;
		overflow: visible;
	}

	.quadrant {
		opacity: 0.1;
	}

	.quick-wins-bg {
		fill: #28a745;
	}
	.major-projects-bg {
		fill: #ffc107;
	}
	.fill-ins-bg {
		fill: #6c757d;
	}
	.questionable-bg {
		fill: #dc3545;
	}

	.grid-line {
		stroke: #dee2e6;
		stroke-width: 1;
		opacity: 0.5;
	}

	.axis-label {
		font-size: 14px;
		font-weight: 600;
		fill: #495057;
	}

	.tick-label {
		font-size: 12px;
		fill: #6c757d;
	}

	.quadrant-label {
		font-size: 12px;
		font-weight: 600;
		fill: #495057;
		opacity: 0.7;
	}

	.data-point {
		cursor: pointer;
		stroke: white;
		stroke-width: 2;
		transition: all 0.2s ease;
	}

	.data-point.quick-wins {
		fill: #28a745;
	}
	.data-point.major-projects {
		fill: #ffc107;
	}
	.data-point.fill-ins {
		fill: #6c757d;
	}
	.data-point.questionable {
		fill: #dc3545;
	}

	.data-point:hover,
	.data-point.hovered {
		stroke-width: 3;
		filter: brightness(1.1);
	}

	.data-point.selected {
		stroke: #007bff;
		stroke-width: 4;
		filter: brightness(1.2);
	}

	.count-label {
		font-size: 12px;
		font-weight: 600;
		fill: white;
		pointer-events: none;
	}

	.count-label.selected {
		font-size: 14px;
	}

	.side-panel {
		flex: 0 0 400px;
		background: white;
		border: 1px solid #e9ecef;
		border-radius: 8px;
		display: flex;
		flex-direction: column;
		max-height: 600px;
	}

	.panel-header {
		padding: 20px 20px 15px 20px;
		border-bottom: 1px solid #e9ecef;
		background: #f8f9fa;
		border-radius: 8px 8px 0 0;
	}

	.panel-header h3 {
		margin: 0;
		font-size: 16px;
		color: #495057;
	}

	.task-count {
		color: #6c757d;
		font-weight: normal;
	}

	.task-list {
		flex: 1;
		overflow-y: auto;
		padding: 10px;
	}

	.task-item {
		padding: 15px;
		border: 1px solid #e9ecef;
		border-radius: 6px;
		margin-bottom: 10px;
		cursor: pointer;
		transition: all 0.2s ease;
		background: white;
	}

	.task-item:hover {
		border-color: #007bff;
		box-shadow: 0 2px 4px rgba(0, 123, 255, 0.1);
	}

	.task-header {
		display: flex;
		align-items: center;
		gap: 10px;
		margin-bottom: 8px;
	}

	.task-rank {
		background: #007bff;
		color: white;
		padding: 2px 6px;
		border-radius: 3px;
		font-size: 11px;
		font-weight: 600;
		min-width: 24px;
		text-align: center;
	}

	.task-name {
		flex: 1;
		font-weight: 600;
		color: #212529;
	}

	.priority-score {
		background: #e9ecef;
		padding: 2px 6px;
		border-radius: 3px;
		font-size: 11px;
		font-weight: 600;
		color: #495057;
	}

	.task-description {
		color: #6c757d;
		font-size: 14px;
		margin-bottom: 8px;
		line-height: 1.4;
	}

	.task-meta {
		display: flex;
		gap: 8px;
		flex-wrap: wrap;
	}

	.meta-item {
		background: #f8f9fa;
		padding: 2px 6px;
		border-radius: 3px;
		font-size: 11px;
		color: #6c757d;
	}

	.meta-item.category {
		background: #e7f3ff;
		color: #0066cc;
	}

	.empty-state {
		text-align: center;
		color: #6c757d;
		padding: 40px 20px;
		font-style: italic;
	}

	@media (max-width: 1200px) {
		.matrix-container {
			flex-direction: column;
		}

		.side-panel {
			flex: none;
			max-height: 400px;
		}
	}
</style>
