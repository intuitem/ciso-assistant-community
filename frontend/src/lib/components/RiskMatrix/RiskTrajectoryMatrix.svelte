<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { isDark } from '$lib/utils/helpers';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import RiskTrajectoryBurndown from './RiskTrajectoryBurndown.svelte';
	import RiskTrajectoryDot from './RiskTrajectoryDot.svelte';
	import RiskTrajectoryTimeline from './RiskTrajectoryTimeline.svelte';
	import {
		addDays,
		buildBurndown,
		buildMilestones,
		daysBetween,
		buildTrajectory,
		gridSize,
		isoDay,
		planScenario,
		reachesResidual,
		toDisplay,
		type ControlInfo,
		type Milestone,
		type Stage,
		type TrajectoryDot
	} from './trajectory';

	interface Props {
		riskMatrix: any;
		scenarios: any[];
		stages: Stage[];
		controls?: ControlInfo[];
		controlsError?: boolean;
		swapAxes?: boolean;
		flipVertical?: boolean;
		labelStandard?: string;
	}

	let {
		riskMatrix,
		scenarios,
		stages,
		controls = [],
		controlsError = false,
		swapAxes = page.data.settings?.risk_matrix_swap_axes ?? false,
		flipVertical = page.data.settings?.risk_matrix_flip_vertical ?? false,
		labelStandard = page.data.settings?.risk_matrix_labels ?? 'ISO'
	}: Props = $props();

	let speed = $state(1);
	let duration = $derived(900 / speed);
	let pause = $derived(900 / speed);

	let definition = $derived(JSON.parse(riskMatrix.json_definition));
	let riskGrid: number[][] = $derived(definition.grid ?? []);
	let levels = $derived(definition.risk ?? []);
	let probabilities = $derived(definition.probability ?? []);
	let impacts = $derived(definition.impact ?? []);
	let dims = $derived({ probabilities: probabilities.length, impacts: impacts.length });

	let orientation = $derived({ swapAxes, flipVertical });
	let size = $derived(gridSize(dims, orientation));
	let dots = $derived(buildTrajectory(scenarios, riskGrid, stages, orientation));

	let cells = $derived(
		riskGrid.flatMap((row, proba) =>
			row.map((levelIndex, impact) => ({
				...toDisplay({ proba, impact }, dims, orientation),
				level: levels[levelIndex]
			}))
		)
	);

	let xHeaders = $derived(swapAxes ? probabilities : impacts);
	let yHeaders = $derived.by(() => {
		const headers = swapAxes ? impacts : probabilities;
		return flipVertical ? headers : [...headers].reverse();
	});
	let xLabel = $derived(safeTranslate(`${swapAxes ? 'probability' : 'impact'}${labelStandard}`));
	let yLabel = $derived(safeTranslate(`${swapAxes ? 'impact' : 'probability'}${labelStandard}`));

	let mode: 'stages' | 'projection' = $state('stages');
	let stageIndex = $state(0);
	let playing = $state(false);
	let timer: ReturnType<typeof setTimeout> | undefined;

	let stagger = $derived(dots.length > 1 ? Math.min(60, 900 / dots.length) / speed : 0);
	let stepTime = $derived(duration + stagger * dots.length + pause);

	const today = isoDay(new Date());
	let currentIndex = $derived(stages.indexOf('current'));
	let residualIndex = $derived(stages.indexOf('residual'));
	let canProject = $derived(controls.length > 0 && currentIndex >= 0 && residualIndex >= 0);
	let controlMap = $derived(new Map(controls.map((c) => [c.id, c])));
	let plans = $derived(
		new Map(
			scenarios.map((s) => [
				s.id,
				planScenario(
					(s.applied_controls ?? []).map((c: { id: string }) => c.id),
					controlMap,
					today
				)
			])
		)
	);
	let milestones = $derived(buildMilestones(plans, today));
	let totalDays = $derived(Math.max(30, ...milestones.map((ms) => ms.offset)));
	let burndown = $derived(
		buildBurndown(dots, plans, { current: currentIndex, residual: residualIndex }, levels.length, [
			today,
			...milestones.map((ms) => ms.date)
		])
	);

	function pickDate(date: string) {
		stop();
		dayOffset = Math.min(totalDays, Math.max(0, daysBetween(today, date)));
	}
	let dayOffset = $state(0);
	let projectedDate = $derived(addDays(today, Math.round(dayOffset)));
	let hoveredMilestone: Milestone | null = $state(null);

	let labels = $derived(new Map(dots.map((dot) => [dot.id, dot.label])));
	const labelOf = (id: string) => labels.get(id) ?? id;

	function blockedControls(state: 'overdue' | 'unscheduled') {
		const found = new Map<string, { control: ControlInfo; scenarioIds: string[] }>();
		for (const [scenarioId, plan] of plans) {
			if (plan.state !== state) continue;
			for (const control of plan.controls) {
				const blocking =
					control.status !== 'active' &&
					(state === 'overdue' ? !!control.eta && control.eta < today : !control.eta);
				if (!blocking) continue;
				const entry = found.get(control.id) ?? { control, scenarioIds: [] };
				entry.scenarioIds.push(scenarioId);
				found.set(control.id, entry);
			}
		}
		return [...found.values()];
	}
	let overdue = $derived(blockedControls('overdue'));
	let unscheduled = $derived(blockedControls('unscheduled'));

	function dotStage(dot: TrajectoryDot) {
		if (mode === 'stages') return stageIndex;
		const plan = plans.get(dot.id);
		return plan && reachesResidual(plan, projectedDate) ? residualIndex : currentIndex;
	}

	function dotFlag(dot: TrajectoryDot) {
		if (mode === 'stages') return null;
		const state = plans.get(dot.id)?.state;
		return state === 'overdue' || state === 'unscheduled' ? state : null;
	}

	let reachedCount = $derived(
		dots.filter((dot) => {
			const plan = plans.get(dot.id);
			return plan && reachesResidual(plan, projectedDate);
		}).length
	);

	let moved = $derived(
		stageIndex === 0
			? []
			: dots.filter((dot) => {
					const [from, to] = [dot.cells[stageIndex - 1], dot.cells[stageIndex]];
					return from && to && (from.proba !== to.proba || from.impact !== to.impact);
				})
	);
	let worsenedCount = $derived(dots.filter((dot) => dot.worsened[stageIndex]).length);

	function stop() {
		clearTimeout(timer);
		playing = false;
	}

	function goTo(index: number) {
		stop();
		stageIndex = index;
	}

	function setMode(next: 'stages' | 'projection') {
		stop();
		mode = next;
		dayOffset = 0;
	}

	function advance() {
		if (stageIndex >= stages.length - 1) {
			playing = false;
			return;
		}
		stageIndex += 1;
		timer = setTimeout(advance, stepTime);
	}

	const frame = 40;

	function tick() {
		const step = totalDays / (8000 / speed / frame);
		dayOffset = Math.min(totalDays, dayOffset + step);
		if (dayOffset >= totalDays) {
			playing = false;
			return;
		}
		timer = setTimeout(tick, frame);
	}

	function play() {
		stop();
		playing = true;
		if (mode === 'projection') {
			if (dayOffset >= totalDays) dayOffset = 0;
			tick();
		} else if (stageIndex >= stages.length - 1) {
			stageIndex = 0;
			timer = setTimeout(advance, stepTime);
		} else {
			advance();
		}
	}

	onMount(() => {
		timer = setTimeout(play, 600);
		return () => clearTimeout(timer);
	});

	const textClass = (hex?: string) => (hex && isDark(hex) ? 'text-white' : 'text-black');
</script>

{#snippet controlChips(entries: { control: ControlInfo; scenarioIds: string[] }[], tone: string)}
	{#each entries as { control, scenarioIds } (control.id)}
		<span class="badge {tone} text-xs">
			{control.ref_id ? `${control.ref_id} ` : ''}{control.name}
			<i class="fa-solid fa-arrow-right text-[10px]"></i>
			{scenarioIds.map(labelOf).join(', ')}
		</span>
	{/each}
{/snippet}

{#if riskGrid.length === 0}
	<div class="flex items-center justify-center p-8 text-surface-600-400 italic">
		<i class="fa-solid fa-triangle-exclamation mr-2"></i>
		{m.riskMatrixEmpty()}
	</div>
{:else}
	<div class="flex flex-col gap-4">
		<div class="flex flex-wrap items-center gap-2">
			{#if canProject || controlsError}
				<div class="flex rounded-base border border-surface-200-800 p-0.5 mr-2">
					<button
						class="btn btn-sm {mode === 'stages' ? 'preset-filled-surface-900-100' : ''}"
						onclick={() => setMode('stages')}
						data-testid="trajectory-mode-stages"
					>
						<i class="fa-solid fa-layer-group mr-1"></i>{m.trajectoryStages()}
					</button>
					<button
						class="btn btn-sm {mode === 'projection' ? 'preset-filled-surface-900-100' : ''}"
						onclick={() => setMode('projection')}
						disabled={controlsError}
						title={controlsError ? m.trajectoryControlsLoadError() : undefined}
						data-testid="trajectory-mode-projection"
					>
						<i class="fa-solid fa-calendar-days mr-1"></i>{m.trajectoryProjection()}
					</button>
				</div>
				{#if controlsError}
					<span class="text-xs text-warning-600-400" data-testid="trajectory-controls-error">
						<i class="fa-solid fa-triangle-exclamation mr-1"></i>{m.trajectoryControlsLoadError()}
					</span>
				{/if}
			{/if}
			<button
				class="btn btn-sm preset-filled-primary-500"
				onclick={() => (playing ? stop() : play())}
				data-testid="trajectory-play"
			>
				<i class="fa-solid {playing ? 'fa-pause' : 'fa-play'} mr-2"></i>
				{playing ? m.pause() : m.play()}
			</button>
			{#if mode === 'stages'}
				<div class="flex items-center gap-1">
					{#each stages as stage, i}
						{#if i > 0}
							<i class="fa-solid fa-chevron-right text-xs text-surface-400-600"></i>
						{/if}
						<button
							class="btn btn-sm {i === stageIndex
								? 'preset-filled-surface-900-100'
								: 'preset-tonal-surface'}"
							onclick={() => goTo(i)}
							data-testid="trajectory-stage-{stage}"
						>
							{safeTranslate(`${stage}Risk`)}
						</button>
					{/each}
				</div>
			{/if}
			<label class="flex items-center gap-2 ml-4 text-sm text-surface-600-400">
				<i class="fa-solid fa-gauge-high"></i>
				<span>{m.speed()}</span>
				<input
					type="range"
					min="0.25"
					max="2"
					step="0.25"
					bind:value={speed}
					class="w-28 accent-primary-500"
					data-testid="trajectory-speed"
				/>
				<span class="w-10 tabular-nums">{speed}×</span>
			</label>
			<span class="ml-auto text-sm text-surface-600-400">
				{#if mode === 'projection'}
					{m.trajectoryReachedCount({ count: reachedCount, total: dots.length })}
				{:else if stageIndex > 0}
					{m.trajectoryMovedCount({ count: moved.length, total: dots.length })}
					{#if worsenedCount > 0}
						<span class="text-red-500 font-semibold">
							· {m.trajectoryWorsenedCount({ count: worsenedCount })}
						</span>
					{/if}
				{/if}
			</span>
		</div>

		{#if mode === 'projection'}
			<RiskTrajectoryTimeline
				{today}
				{totalDays}
				bind:dayOffset
				bind:hovered={hoveredMilestone}
				{milestones}
				{labelOf}
				onscrub={() => stop()}
			/>
		{/if}

		<div class="flex flex-row items-center">
			<div class="font-semibold text-lg -rotate-90 whitespace-nowrap w-8">{yLabel}</div>
			<div class="flex flex-col w-full">
				<div
					class="grid gap-1 w-full"
					style="grid-template-columns: auto repeat({size.cols}, minmax(0, 1fr)); grid-template-rows: repeat({size.rows}, minmax(5.5rem, 1fr)) auto;"
					data-testid="trajectory-matrix"
				>
					{#each yHeaders as header, row}
						<div
							class="flex items-center justify-center text-center p-2 font-semibold text-sm border-2 border-dotted border-black bg-surface-200-800 {textClass(
								header.hexcolor
							)}"
							style="grid-row: {row + 1}; grid-column: 1; {header.hexcolor
								? `background: ${header.hexcolor};`
								: ''}"
						>
							{header.name}
						</div>
					{/each}
					{#each cells as cell}
						<div
							style="grid-row: {cell.row + 1}; grid-column: {cell.col + 2}; background-color: {cell
								.level?.hexcolor};"
						></div>
					{/each}
					<div
						class="relative pointer-events-none"
						style="grid-row: 1 / span {size.rows}; grid-column: 2 / span {size.cols};"
					>
						{#each dots as dot, i (dot.id)}
							<RiskTrajectoryDot
								{dot}
								stageIndex={dotStage(dot)}
								{duration}
								delay={mode === 'stages' ? i * stagger : 0}
								flag={dotFlag(dot)}
								highlighted={hoveredMilestone?.scenarioIds.includes(dot.id) ?? false}
								dimmed={!!hoveredMilestone && !hoveredMilestone.scenarioIds.includes(dot.id)}
							/>
						{/each}
					</div>
					{#each xHeaders as header, col}
						<div
							class="flex items-center justify-center text-center p-2 font-semibold text-sm border-2 border-dotted border-black bg-surface-200-800 {textClass(
								header.hexcolor
							)}"
							style="grid-row: {size.rows + 1}; grid-column: {col + 2}; {header.hexcolor
								? `background: ${header.hexcolor};`
								: ''}"
						>
							{header.name}
						</div>
					{/each}
				</div>
				<div class="font-semibold text-lg text-center p-2">{xLabel}</div>
			</div>
		</div>

		{#if mode === 'projection'}
			<div class="flex flex-col gap-1">
				<h3 class="text-sm font-semibold text-surface-800-200">{m.trajectoryBurndownTitle()}</h3>
				<RiskTrajectoryBurndown
					points={burndown}
					{levels}
					start={today}
					end={addDays(today, totalDays)}
					cursor={projectedDate}
					onpick={pickDate}
				/>
			</div>
		{/if}

		{#if mode === 'projection' && (overdue.length > 0 || unscheduled.length > 0)}
			<div class="flex flex-col gap-2 text-sm">
				{#if overdue.length > 0}
					<div class="flex flex-wrap items-center gap-2">
						<span class="font-semibold text-amber-600">
							<i class="fa-solid fa-clock mr-1"></i>{m.overdue()}
						</span>
						{@render controlChips(overdue, 'preset-tonal-warning')}
					</div>
				{/if}
				{#if unscheduled.length > 0}
					<div class="flex flex-wrap items-center gap-2">
						<span class="font-semibold text-surface-600-400">
							<i class="fa-solid fa-calendar-xmark mr-1"></i>{m.trajectoryNoEta()}
						</span>
						{@render controlChips(unscheduled, 'preset-tonal-surface')}
					</div>
				{/if}
			</div>
		{/if}
	</div>
{/if}
