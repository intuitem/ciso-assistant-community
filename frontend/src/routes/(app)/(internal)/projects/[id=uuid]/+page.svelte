<script lang="ts">
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import { Tabs, Progress } from '@skeletonlabs/skeleton-svelte';
	import { invalidateAll } from '$app/navigation';
	import { page } from '$app/state';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import MarkdownField from '$lib/components/Forms/MarkdownField.svelte';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	let project = $derived(data.data);
	let statusOptions = $derived(data.statusOptions);
	let healthOptions = $derived(data.healthOptions);
	let priorityOptions = $derived(data.priorityOptions);
	let actorOptions = $derived(data.actorOptions);
	let collectionOptions = $derived(data.collectionOptions);
	let projectOptions = $derived(data.projectOptions);

	let activeTab = $state('overview');
	let savingSection: string | null = $state(null);
	let errorMessage = $state('');

	const kindIconMap: Record<string, string> = {
		portfolio: 'fa-solid fa-folder-tree',
		program: 'fa-solid fa-diagram-project',
		project: 'fa-solid fa-clipboard-list'
	};
	const kindColorMap: Record<string, string> = {
		portfolio: 'bg-purple-100 text-purple-700',
		program: 'bg-blue-100 text-blue-700',
		project: 'bg-gray-100 text-gray-700'
	};
	let isPortfolio = $derived(project.kind === 'portfolio');

	const statusColorMap: Record<string, string> = {
		draft: 'bg-gray-100 text-gray-600',
		initiated: 'bg-blue-50 text-blue-700',
		planning: 'bg-indigo-100 text-indigo-700',
		in_progress: 'bg-blue-100 text-blue-700',
		on_hold: 'bg-amber-100 text-amber-700',
		closing: 'bg-purple-100 text-purple-700',
		closed: 'bg-green-100 text-green-700',
		cancelled: 'bg-red-100 text-red-600'
	};

	const healthColorMap: Record<string, string> = {
		green: 'bg-green-100 text-green-700',
		amber: 'bg-amber-100 text-amber-700',
		red: 'bg-red-100 text-red-600'
	};

	async function patchProject(payload: Record<string, unknown>, section: string) {
		savingSection = section;
		errorMessage = '';
		try {
			const res = await fetch(page.url.pathname, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(payload)
			});
			if (!res.ok) {
				const err = await res.json().catch(() => ({}));
				errorMessage = typeof err === 'string' ? err : JSON.stringify(err);
				return false;
			}
			await invalidateAll();
			return true;
		} finally {
			savingSection = null;
		}
	}

	// --- Overview tab (lifecycle indicators) ---
	let overviewEditing = $state(false);
	let overviewDraft: {
		status: string | null;
		priority: number | null;
		health: string | null;
		progress: number | null;
	} = $state({ status: null, priority: null, health: null, progress: null });

	function startOverviewEdit() {
		const statusId = statusOptions.find((t: any) => t.name === project.status)?.id;
		const healthId = healthOptions.find((t: any) => t.name === project.health)?.id;
		const priorityValue = priorityOptions.find((p: any) => p.label === project.priority)?.value;
		overviewDraft = {
			status: statusId ?? null,
			priority: priorityValue ?? null,
			health: healthId ?? null,
			progress: project.progress ?? null
		};
		overviewEditing = true;
	}

	async function saveOverview() {
		if ((await patchProject(overviewDraft, 'overview')) === true) overviewEditing = false;
	}

	// --- Charter tab (the why) ---
	const charterFields = [
		{ key: 'purpose', label: m.purpose() },
		{ key: 'objectives', label: m.objectives() },
		{ key: 'success_criteria', label: m.successCriteria() },
		{ key: 'business_case', label: m.businessCase() },
		{ key: 'approval_requirements', label: m.approvalRequirements() },
		{ key: 'exit_criteria', label: m.exitCriteria() },
		{ key: 'organizational_alignment', label: m.organizationalAlignment() }
	] as const;

	let charterEditing = $state(false);
	let charterDraft: Record<string, string> = $state({});

	function startCharterEdit() {
		charterDraft = Object.fromEntries(charterFields.map((f) => [f.key, project[f.key] ?? '']));
		charterEditing = true;
	}

	async function saveCharter() {
		if ((await patchProject(charterDraft, 'charter')) === true) charterEditing = false;
	}

	// --- Schedule tab (when + how much) ---
	let scheduleEditing = $state(false);
	let scheduleDraft: {
		start_date: string | null;
		end_date: string | null;
		eta: string | null;
		budget: number | null;
		actual_cost: number | null;
		currency: string;
		tolerances: {
			time?: { plus_days?: number; minus_days?: number };
			cost?: { plus_pct?: number; minus_pct?: number };
			scope?: string;
			quality?: string;
			benefits?: string;
			risk?: string;
		};
	} = $state({
		start_date: null,
		end_date: null,
		eta: null,
		budget: null,
		actual_cost: null,
		currency: '',
		tolerances: {}
	});

	function startScheduleEdit() {
		scheduleDraft = {
			start_date: project.start_date ?? null,
			end_date: project.end_date ?? null,
			eta: project.eta ?? null,
			budget: project.budget ?? null,
			actual_cost: project.actual_cost ?? null,
			currency: project.currency ?? '',
			tolerances: structuredClone(project.tolerances ?? {})
		};
		scheduleEditing = true;
	}

	let budgetSpentPct = $derived(
		project.budget && Number(project.budget) > 0
			? (Number(project.actual_cost ?? 0) / Number(project.budget)) * 100
			: 0
	);
	let budgetRemaining = $derived(
		project.budget != null ? Number(project.budget) - Number(project.actual_cost ?? 0) : null
	);
	let budgetBarColor = $derived(
		budgetSpentPct > 100 ? 'bg-red-500' : budgetSpentPct > 80 ? 'bg-amber-500' : 'bg-green-500'
	);

	async function saveSchedule() {
		if ((await patchProject(scheduleDraft, 'schedule')) === true) scheduleEditing = false;
	}

	// --- Scope tab (the what) ---
	const scopeFields = [
		{ key: 'deliverables', label: m.deliverables() },
		{ key: 'assumptions', label: m.assumptions() },
		{ key: 'constraints', label: m.constraints() },
		{ key: 'dependencies_note', label: m.dependenciesNote() }
	] as const;

	let scopeEditing = $state(false);
	let scopeDraft: Record<string, string> = $state({});

	function startScopeEdit() {
		scopeDraft = Object.fromEntries(scopeFields.map((f) => [f.key, project[f.key] ?? '']));
		scopeEditing = true;
	}

	async function saveScope() {
		if ((await patchProject(scopeDraft, 'scope')) === true) scopeEditing = false;
	}

	// --- Linked tab (other CISO Assistant objects) ---
	let linkedEditing = $state(false);
	let linkedDraft: { linked_collection: string | null; parent_project: string | null } = $state({
		linked_collection: null,
		parent_project: null
	});

	function startLinkedEdit() {
		linkedDraft = {
			linked_collection: project.linked_collection?.id ?? null,
			parent_project: project.parent_project?.id ?? null
		};
		linkedEditing = true;
	}

	async function saveLinked() {
		if ((await patchProject(linkedDraft, 'linked')) === true) linkedEditing = false;
	}

	// --- People tab (owner + sponsor) ---
	let peopleEditing = $state(false);
	let peopleDraft: { owner: string | null; sponsor: string | null } = $state({
		owner: null,
		sponsor: null
	});

	function startPeopleEdit() {
		peopleDraft = {
			owner: project.owner?.id ?? null,
			sponsor: project.sponsor?.id ?? null
		};
		peopleEditing = true;
	}

	async function savePeople() {
		if ((await patchProject(peopleDraft, 'people')) === true) peopleEditing = false;
	}

	// --- Header basics (name, ref_id, ref_link, description) ---
	let basicsEditing = $state(false);
	let basicsDraft: {
		name: string;
		ref_id: string;
		ref_link: string;
		description: string;
	} = $state({ name: '', ref_id: '', ref_link: '', description: '' });

	function startBasicsEdit() {
		basicsDraft = {
			name: project.name ?? '',
			ref_id: project.ref_id ?? '',
			ref_link: project.ref_link ?? '',
			description: project.description ?? ''
		};
		basicsEditing = true;
	}

	async function saveBasics() {
		if ((await patchProject(basicsDraft, 'basics')) === true) basicsEditing = false;
	}

	// --- Analytics tab ---
	let snapshots = $derived(data.snapshots ?? []);
	let latestSnapshot = $derived(
		snapshots.length > 0 ? snapshots[snapshots.length - 1].metrics : null
	);
	let snapshot7dAgo = $derived(
		snapshots.length >= 8 ? snapshots[snapshots.length - 8].metrics : null
	);
	let progressDelta7d = $derived(
		latestSnapshot?.progress != null && snapshot7dAgo?.progress != null
			? latestSnapshot.progress - snapshot7dAgo.progress
			: null
	);

	let progressChartEl: HTMLDivElement | null = $state(null);
	let budgetChartEl: HTMLDivElement | null = $state(null);
	let lifecycleChartEl: HTMLDivElement | null = $state(null);
	let progressChart: any = $state(null);
	let budgetChart: any = $state(null);
	let lifecycleChart: any = $state(null);

	const statusYOrder = [
		'cancelled',
		'on_hold',
		'draft',
		'initiated',
		'planning',
		'in_progress',
		'closing',
		'closed'
	];
	const healthYOrder = ['red', 'amber', 'green'];

	async function renderCharts() {
		if (snapshots.length === 0) return;
		const echarts = await import('echarts');
		const dates = snapshots.map((s: any) => s.date);

		if (progressChartEl) {
			progressChart?.dispose?.();
			progressChart = echarts.init(progressChartEl, null, { renderer: 'svg' });
			progressChart.setOption({
				grid: { left: 40, right: 20, top: 20, bottom: 30 },
				xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 10 } },
				yAxis: { type: 'value', min: 0, max: 100, axisLabel: { formatter: '{value}%' } },
				tooltip: { trigger: 'axis' },
				series: [
					{
						type: 'line',
						smooth: true,
						symbol: 'circle',
						symbolSize: 4,
						lineStyle: { width: 2 },
						areaStyle: { opacity: 0.1 },
						data: snapshots.map((s: any) => s.metrics.progress ?? null),
						connectNulls: true
					}
				]
			});
		}

		if (lifecycleChartEl) {
			lifecycleChart?.dispose?.();
			lifecycleChart = echarts.init(lifecycleChartEl, null, { renderer: 'svg' });
			const seriesLabels = [m.projectStatus(), m.projectHealth(), m.projectPriority()];
			lifecycleChart.setOption({
				tooltip: {
					trigger: 'axis',
					formatter: (params: any[]) => {
						if (!params || params.length === 0) return '';
						const date = params[0].axisValueLabel ?? params[0].axisValue ?? '';
						const lines = params.map((p) => {
							const label = seriesLabels[p.seriesIndex] ?? '';
							const raw = p.value;
							let value: string;
							if (raw == null || raw === '') value = '--';
							else if (p.seriesIndex === 2) value = `P${raw}`;
							else value = safeTranslate(String(raw));
							return `<div style="display:flex;justify-content:space-between;gap:12px;"><span>${p.marker} ${label}</span><strong>${value}</strong></div>`;
						});
						return `<div style="font-weight:600;margin-bottom:4px;">${date}</div>${lines.join('')}`;
					}
				},
				axisPointer: { link: [{ xAxisIndex: 'all' }] },
				grid: [
					{ left: 90, right: 20, top: 30, height: 80 },
					{ left: 90, right: 20, top: 150, height: 60 },
					{ left: 90, right: 20, top: 240, height: 60 }
				],
				xAxis: [
					{ type: 'category', data: dates, gridIndex: 0, axisLabel: { show: false } },
					{ type: 'category', data: dates, gridIndex: 1, axisLabel: { show: false } },
					{ type: 'category', data: dates, gridIndex: 2, axisLabel: { fontSize: 10 } }
				],
				yAxis: [
					{
						type: 'category',
						data: statusYOrder,
						gridIndex: 0,
						name: m.projectStatus(),
						nameLocation: 'middle',
						nameGap: 78,
						nameTextStyle: { fontSize: 10, fontWeight: 'bold' },
						axisLabel: { fontSize: 9, formatter: (v: string) => safeTranslate(v) }
					},
					{
						type: 'category',
						data: healthYOrder,
						gridIndex: 1,
						name: m.projectHealth(),
						nameLocation: 'middle',
						nameGap: 78,
						nameTextStyle: { fontSize: 10, fontWeight: 'bold' },
						axisLabel: { fontSize: 9, formatter: (v: string) => safeTranslate(v) }
					},
					{
						type: 'value',
						min: 1,
						max: 4,
						interval: 1,
						inverse: true,
						gridIndex: 2,
						name: m.projectPriority(),
						nameLocation: 'middle',
						nameGap: 78,
						nameTextStyle: { fontSize: 10, fontWeight: 'bold' },
						axisLabel: { fontSize: 9, formatter: (v: number) => `P${v}` }
					}
				],
				series: [
					{
						type: 'line',
						step: 'end',
						symbol: 'none',
						lineStyle: { width: 2, color: '#3b82f6' },
						areaStyle: { color: '#3b82f6', opacity: 0.15 },
						data: snapshots.map((s: any) => s.metrics.status),
						xAxisIndex: 0,
						yAxisIndex: 0,
						connectNulls: true
					},
					{
						type: 'line',
						step: 'end',
						symbol: 'none',
						lineStyle: { width: 2, color: '#7c3aed' },
						areaStyle: { color: '#7c3aed', opacity: 0.15 },
						data: snapshots.map((s: any) => s.metrics.health),
						xAxisIndex: 1,
						yAxisIndex: 1,
						connectNulls: true
					},
					{
						type: 'line',
						step: 'end',
						symbol: 'none',
						lineStyle: { width: 2, color: '#f97316' },
						areaStyle: { color: '#f97316', opacity: 0.15 },
						data: snapshots.map((s: any) => s.metrics.priority),
						xAxisIndex: 2,
						yAxisIndex: 2,
						connectNulls: true
					}
				]
			});
		}

		if (budgetChartEl) {
			budgetChart?.dispose?.();
			budgetChart = echarts.init(budgetChartEl, null, { renderer: 'svg' });
			const budgetSeries = snapshots.map((s: any) => s.metrics.budget ?? null);
			const actualSeries = snapshots.map((s: any) => s.metrics.actual_cost ?? null);
			budgetChart.setOption({
				grid: { left: 60, right: 20, top: 30, bottom: 30 },
				xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 10 } },
				yAxis: { type: 'value' },
				tooltip: { trigger: 'axis' },
				legend: { top: 0, textStyle: { fontSize: 11 } },
				series: [
					{
						name: m.expectedBudget(),
						type: 'line',
						data: budgetSeries,
						lineStyle: { type: 'dashed', width: 2 },
						symbol: 'none',
						connectNulls: true
					},
					{
						name: m.actualCost(),
						type: 'line',
						data: actualSeries,
						lineStyle: { width: 2 },
						areaStyle: { opacity: 0.15 },
						symbol: 'circle',
						symbolSize: 4,
						connectNulls: true
					}
				]
			});
		}
	}

	$effect(() => {
		if (activeTab === 'analytics') {
			void snapshots;
			setTimeout(renderCharts, 0);
		} else {
			progressChart?.dispose?.();
			budgetChart?.dispose?.();
			lifecycleChart?.dispose?.();
			progressChart = null;
			budgetChart = null;
			lifecycleChart = null;
		}
	});

	let progressValue = $derived(project.progress ?? 0);
</script>

<div class="card bg-white shadow-sm m-4">
	<!-- Header bar -->
	<div class="p-6 border-b border-gray-200">
		<div class="flex items-start justify-between gap-4 flex-wrap">
			<div class="min-w-0 grow">
				{#if !basicsEditing}
					<div class="group flex items-baseline gap-3">
						<span
							class="badge text-xs font-medium px-2 py-0.5 rounded-full self-center {kindColorMap[
								project.kind
							] ?? 'bg-gray-100 text-gray-700'}"
							title={safeTranslate(project.kind)}
						>
							<i class="{kindIconMap[project.kind] ?? 'fa-solid fa-clipboard-list'} mr-1"></i>
							{safeTranslate(project.kind)}
						</span>
						<h1 class="text-2xl font-semibold text-gray-900 truncate">{project.name}</h1>
						{#if project.ref_id}
							<span class="text-sm text-gray-500">{project.ref_id}</span>
						{/if}
						<button
							onclick={startBasicsEdit}
							class="opacity-0 group-hover:opacity-100 transition-opacity text-gray-400 hover:text-primary-600"
							aria-label={m.edit()}
							title={m.edit()}
						>
							<i class="fa-solid fa-pen text-sm"></i>
						</button>
					</div>
					{#if project.ref_link}
						<a
							href={project.ref_link}
							target="_blank"
							rel="noopener noreferrer"
							class="text-primary-600 hover:text-primary-800 hover:underline text-sm inline-flex items-center gap-1 mt-1"
						>
							<i class="fa-solid fa-arrow-up-right-from-square text-xs"></i>
							{project.ref_link}
						</a>
					{/if}
					{#if project.description}
						<div class="prose prose-sm max-w-none text-gray-700 mt-3">
							<MarkdownRenderer content={project.description} />
						</div>
					{/if}
				{:else}
					<div class="space-y-3 max-w-3xl">
						<label class="block">
							<span class="text-xs font-semibold text-gray-500 uppercase">{m.name()}</span>
							<input type="text" bind:value={basicsDraft.name} class="input w-full mt-1" required />
						</label>
						<label class="block">
							<span class="text-xs font-semibold text-gray-500 uppercase">{m.refId()}</span>
							<input
								type="text"
								maxlength="100"
								bind:value={basicsDraft.ref_id}
								class="input w-full mt-1"
							/>
						</label>
						<label class="block">
							<span class="text-xs font-semibold text-gray-500 uppercase">{m.refLink()}</span>
							<input
								type="url"
								bind:value={basicsDraft.ref_link}
								class="input w-full mt-1"
								placeholder="https://…"
							/>
						</label>
						<div class="block">
							<span class="text-xs font-semibold text-gray-500 uppercase">{m.description()}</span>
							<div class="mt-1">
								<MarkdownField label="" bind:value={basicsDraft.description} rows={4} />
							</div>
						</div>
					</div>
				{/if}
			</div>

			{#if basicsEditing}
				<div class="shrink-0 flex gap-2">
					<button
						class="btn preset-tonal-surface btn-sm"
						onclick={() => (basicsEditing = false)}
						disabled={savingSection === 'basics'}>{m.cancel()}</button
					>
					<button
						class="btn preset-filled-primary-500 btn-sm"
						onclick={saveBasics}
						disabled={savingSection === 'basics'}
					>
						{#if savingSection === 'basics'}<i class="fa-solid fa-spinner fa-spin mr-2"
							></i>{/if}{m.save()}
					</button>
				</div>
			{/if}
		</div>

		{#if errorMessage && basicsEditing}
			<div class="card preset-tonal-error p-3 mt-3 text-sm">{errorMessage}</div>
		{/if}

		<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mt-4">
			<div>
				<div class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
					{m.projectStatus()}
				</div>
				{#if project.status}
					<span
						class="badge text-xs font-medium px-2 py-0.5 rounded-full {statusColorMap[
							project.status
						] ?? 'bg-gray-100 text-gray-600'}">{safeTranslate(project.status)}</span
					>
				{:else}
					<span class="text-gray-400 text-sm">--</span>
				{/if}
			</div>
			<div>
				<div class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
					{m.projectHealth()}
				</div>
				{#if project.health}
					<span
						class="badge text-xs font-medium px-2 py-0.5 rounded-full {healthColorMap[
							project.health
						] ?? 'bg-gray-100 text-gray-600'}">{safeTranslate(project.health)}</span
					>
				{:else}
					<span class="text-gray-400 text-sm">--</span>
				{/if}
			</div>
			<div>
				<div class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
					{m.projectPriority()}
				</div>
				<span class="text-sm text-gray-900">{project.priority ?? '--'}</span>
			</div>
			<div>
				<div class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
					{m.owner()}
				</div>
				<span class="text-sm text-gray-900 truncate block">{project.owner?.str ?? '--'}</span>
			</div>
			<div>
				<div class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
					{m.sponsor()}
				</div>
				<span class="text-sm text-gray-900 truncate block">{project.sponsor?.str ?? '--'}</span>
			</div>
			<div>
				<div class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
					{m.progress()}
				</div>
				<div class="flex items-center gap-2">
					<Progress value={progressValue} max={100}>
						<Progress.Track class="h-2 rounded-full grow">
							<Progress.Range class="bg-primary-500 rounded-full" />
						</Progress.Track>
					</Progress>
					<span class="text-xs text-gray-700 shrink-0">{progressValue}%</span>
				</div>
			</div>
		</div>
	</div>

	<!-- Tab bar -->
	<Tabs value={activeTab} onValueChange={(e) => (activeTab = e.value)} class="w-full">
		<Tabs.List class="border-b border-gray-200 px-4">
			<Tabs.Trigger
				value="overview"
				class="px-4 py-3 text-sm font-medium text-gray-500 hover:text-gray-700 border-b-2 border-transparent transition-colors aria-[selected=true]:!text-primary-700 aria-[selected=true]:!border-primary-500"
			>
				<i class="fa-solid fa-chart-pie mr-2"></i>{m.overview()}
			</Tabs.Trigger>
			<Tabs.Trigger
				value="charter"
				class="px-4 py-3 text-sm font-medium text-gray-500 hover:text-gray-700 border-b-2 border-transparent transition-colors aria-[selected=true]:!text-primary-700 aria-[selected=true]:!border-primary-500"
			>
				<i class="fa-solid fa-file-contract mr-2"></i>{m.charter()}
			</Tabs.Trigger>
			<Tabs.Trigger
				value="schedule"
				class="px-4 py-3 text-sm font-medium text-gray-500 hover:text-gray-700 border-b-2 border-transparent transition-colors aria-[selected=true]:!text-primary-700 aria-[selected=true]:!border-primary-500"
			>
				<i class="fa-solid fa-calendar mr-2"></i>{m.schedule()}
			</Tabs.Trigger>
			{#if !isPortfolio}<Tabs.Trigger
				value="scope"
				class="px-4 py-3 text-sm font-medium text-gray-500 hover:text-gray-700 border-b-2 border-transparent transition-colors aria-[selected=true]:!text-primary-700 aria-[selected=true]:!border-primary-500"
			>
				<i class="fa-solid fa-bullseye mr-2"></i>{m.scope()}
			</Tabs.Trigger>{/if}
			<Tabs.Trigger
				value="linked"
				class="px-4 py-3 text-sm font-medium text-gray-500 hover:text-gray-700 border-b-2 border-transparent transition-colors aria-[selected=true]:!text-primary-700 aria-[selected=true]:!border-primary-500"
			>
				<i class="fa-solid fa-link mr-2"></i>{m.linked()}
			</Tabs.Trigger>
			<Tabs.Trigger
				value="people"
				class="px-4 py-3 text-sm font-medium text-gray-500 hover:text-gray-700 border-b-2 border-transparent transition-colors aria-[selected=true]:!text-primary-700 aria-[selected=true]:!border-primary-500"
			>
				<i class="fa-solid fa-people-arrows mr-2"></i>{m.people()}
			</Tabs.Trigger>
			<Tabs.Trigger
				value="analytics"
				class="px-4 py-3 text-sm font-medium text-gray-500 hover:text-gray-700 border-b-2 border-transparent transition-colors aria-[selected=true]:!text-primary-700 aria-[selected=true]:!border-primary-500"
			>
				<i class="fa-solid fa-chart-line mr-2"></i>{m.analytics()}
			</Tabs.Trigger>
		</Tabs.List>

		<!-- OVERVIEW -->
		<Tabs.Content value="overview" class="p-6">
			<div class="flex items-center justify-between mb-4">
				<h2 class="text-lg font-semibold">{m.lifecycle()}</h2>
				{#if !overviewEditing}
					<button class="btn preset-tonal-primary btn-sm" onclick={startOverviewEdit}>
						<i class="fa-solid fa-pen mr-2"></i>{m.edit()}
					</button>
				{:else}
					<div class="flex gap-2">
						<button
							class="btn preset-tonal-surface btn-sm"
							onclick={() => (overviewEditing = false)}
							disabled={savingSection === 'overview'}>{m.cancel()}</button
						>
						<button
							class="btn preset-filled-primary-500 btn-sm"
							onclick={saveOverview}
							disabled={savingSection === 'overview'}
						>
							{#if savingSection === 'overview'}<i class="fa-solid fa-spinner fa-spin mr-2"
								></i>{/if}{m.save()}
						</button>
					</div>
				{/if}
			</div>

			{#if errorMessage && overviewEditing}
				<div class="card preset-tonal-error p-3 mb-4 text-sm">{errorMessage}</div>
			{/if}

			<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
				<div>
					<label for="ov-status" class="text-xs font-semibold text-gray-500 uppercase mb-1 block">
						{m.projectStatus()}
					</label>
					{#if overviewEditing}
						<select id="ov-status" bind:value={overviewDraft.status} class="select w-full">
							<option value={null}>--</option>
							{#each statusOptions as opt}
								<option value={opt.id}>{safeTranslate(opt.translated_name ?? opt.name)}</option>
							{/each}
						</select>
					{:else}
						<span class="text-sm text-gray-900">{safeTranslate(project.status ?? '--')}</span>
					{/if}
				</div>

				<div>
					<label for="ov-health" class="text-xs font-semibold text-gray-500 uppercase mb-1 block">
						{m.projectHealth()}
					</label>
					{#if overviewEditing}
						<select id="ov-health" bind:value={overviewDraft.health} class="select w-full">
							<option value={null}>--</option>
							{#each healthOptions as opt}
								<option value={opt.id}>{safeTranslate(opt.translated_name ?? opt.name)}</option>
							{/each}
						</select>
					{:else}
						<span class="text-sm text-gray-900">{safeTranslate(project.health ?? '--')}</span>
					{/if}
				</div>

				<div>
					<label for="ov-priority" class="text-xs font-semibold text-gray-500 uppercase mb-1 block">
						{m.projectPriority()}
					</label>
					{#if overviewEditing}
						<select id="ov-priority" bind:value={overviewDraft.priority} class="select w-full">
							<option value={null}>--</option>
							{#each priorityOptions as opt}
								<option value={opt.value}>{opt.label}</option>
							{/each}
						</select>
					{:else}
						<span class="text-sm text-gray-900">{project.priority ?? '--'}</span>
					{/if}
				</div>

				<div>
					<label for="ov-progress" class="text-xs font-semibold text-gray-500 uppercase mb-1 block">
						{m.progress()}
					</label>
					{#if overviewEditing}
						<input
							id="ov-progress"
							type="number"
							min="0"
							max="100"
							bind:value={overviewDraft.progress}
							class="input w-full"
						/>
					{:else}
						<span class="text-sm text-gray-900">{progressValue}%</span>
					{/if}
				</div>
			</div>
		</Tabs.Content>

		<!-- CHARTER -->
		<Tabs.Content value="charter" class="p-6">
			<div class="flex items-center justify-between mb-4">
				<h2 class="text-lg font-semibold">{m.charter()}</h2>
				{#if !charterEditing}
					<button class="btn preset-tonal-primary btn-sm" onclick={startCharterEdit}>
						<i class="fa-solid fa-pen mr-2"></i>{m.edit()}
					</button>
				{:else}
					<div class="flex gap-2">
						<button
							class="btn preset-tonal-surface btn-sm"
							onclick={() => (charterEditing = false)}
							disabled={savingSection === 'charter'}>{m.cancel()}</button
						>
						<button
							class="btn preset-filled-primary-500 btn-sm"
							onclick={saveCharter}
							disabled={savingSection === 'charter'}
						>
							{#if savingSection === 'charter'}<i class="fa-solid fa-spinner fa-spin mr-2"
								></i>{/if}{m.save()}
						</button>
					</div>
				{/if}
			</div>

			{#if errorMessage && charterEditing}
				<div class="card preset-tonal-error p-3 mb-4 text-sm">{errorMessage}</div>
			{/if}

			<div class="space-y-6">
				{#each charterFields as section}
					<div class="border-l-2 border-gray-200 pl-4">
						<h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
							{section.label}
						</h3>
						{#if charterEditing}
							<MarkdownField
								label=""
								bind:value={charterDraft[section.key]}
								rows={4}
								placeholder={section.label}
							/>
						{:else if project[section.key]}
							<div class="prose prose-sm max-w-none text-gray-900">
								<MarkdownRenderer content={project[section.key]} />
							</div>
						{:else}
							<p class="text-gray-400 italic text-sm">--</p>
						{/if}
					</div>
				{/each}
			</div>
		</Tabs.Content>

		<!-- SCHEDULE -->
		<Tabs.Content value="schedule" class="p-6">
			<div class="flex items-center justify-between mb-4">
				<h2 class="text-lg font-semibold">{m.schedule()}</h2>
				{#if !scheduleEditing}
					<button class="btn preset-tonal-primary btn-sm" onclick={startScheduleEdit}>
						<i class="fa-solid fa-pen mr-2"></i>{m.edit()}
					</button>
				{:else}
					<div class="flex gap-2">
						<button
							class="btn preset-tonal-surface btn-sm"
							onclick={() => (scheduleEditing = false)}
							disabled={savingSection === 'schedule'}>{m.cancel()}</button
						>
						<button
							class="btn preset-filled-primary-500 btn-sm"
							onclick={saveSchedule}
							disabled={savingSection === 'schedule'}
						>
							{#if savingSection === 'schedule'}<i class="fa-solid fa-spinner fa-spin mr-2"
								></i>{/if}{m.save()}
						</button>
					</div>
				{/if}
			</div>

			{#if errorMessage && scheduleEditing}
				<div class="card preset-tonal-error p-3 mb-4 text-sm">{errorMessage}</div>
			{/if}

			<div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
				<div>
					<label for="sc-start" class="text-xs font-semibold text-gray-500 uppercase mb-1 block">
						{m.startDate()}
					</label>
					{#if scheduleEditing}
						<input
							id="sc-start"
							type="date"
							bind:value={scheduleDraft.start_date}
							class="input w-full"
						/>
					{:else}
						<span class="text-sm text-gray-900">{project.start_date ?? '--'}</span>
					{/if}
				</div>
				<div>
					<label for="sc-end" class="text-xs font-semibold text-gray-500 uppercase mb-1 block">
						{m.endDate()}
					</label>
					{#if scheduleEditing}
						<input
							id="sc-end"
							type="date"
							bind:value={scheduleDraft.end_date}
							class="input w-full"
						/>
					{:else}
						<span class="text-sm text-gray-900">{project.end_date ?? '--'}</span>
					{/if}
				</div>
				<div>
					<label for="sc-eta" class="text-xs font-semibold text-gray-500 uppercase mb-1 block">
						{m.eta()}
					</label>
					{#if scheduleEditing}
						<input id="sc-eta" type="date" bind:value={scheduleDraft.eta} class="input w-full" />
					{:else}
						<span class="text-sm text-gray-900">{project.eta ?? '--'}</span>
					{/if}
				</div>
				<div>
					<div class="text-xs font-semibold text-gray-500 uppercase mb-1">{m.closedAt()}</div>
					<span class="text-sm text-gray-900">{project.closed_at ?? '--'}</span>
				</div>
				<div class="md:col-span-2">
					<div class="flex items-baseline justify-between mb-2">
						<h3 class="text-sm font-semibold text-gray-700">{m.financials()}</h3>
					</div>
					{#if scheduleEditing}
						<div class="grid grid-cols-1 md:grid-cols-3 gap-3">
							<label class="block">
								<span class="text-xs font-semibold text-gray-500 uppercase">
									{m.expectedBudget()}
								</span>
								<input
									type="number"
									step="0.01"
									bind:value={scheduleDraft.budget}
									class="input w-full mt-1"
								/>
							</label>
							<label class="block">
								<span class="text-xs font-semibold text-gray-500 uppercase">{m.actualCost()}</span>
								<input
									type="number"
									step="0.01"
									bind:value={scheduleDraft.actual_cost}
									class="input w-full mt-1"
								/>
							</label>
							<label class="block">
								<span class="text-xs font-semibold text-gray-500 uppercase">{m.currency()}</span>
								<input
									type="text"
									maxlength="3"
									bind:value={scheduleDraft.currency}
									class="input w-full mt-1"
								/>
							</label>
						</div>
					{:else if project.budget == null && project.actual_cost == null}
						<span class="text-sm text-gray-400 italic">--</span>
					{:else}
						<div class="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
							<div>
								<div class="text-xs font-semibold text-gray-500 uppercase">
									{m.expectedBudget()}
								</div>
								<div class="text-sm text-gray-900">
									{project.budget ?? '--'}
									{project.currency ?? ''}
								</div>
							</div>
							<div>
								<div class="text-xs font-semibold text-gray-500 uppercase">{m.actualCost()}</div>
								<div class="text-sm text-gray-900">
									{project.actual_cost ?? '--'}
									{project.currency ?? ''}
								</div>
							</div>
							<div>
								<div class="text-xs font-semibold text-gray-500 uppercase">{m.remaining()}</div>
								<div
									class="text-sm font-medium"
									class:text-gray-900={budgetRemaining == null || budgetRemaining >= 0}
									class:text-red-600={budgetRemaining != null && budgetRemaining < 0}
								>
									{budgetRemaining ?? '--'}
									{project.currency ?? ''}
								</div>
							</div>
						</div>
						{#if project.budget != null && Number(project.budget) > 0}
							<div class="flex items-center gap-2">
								<div class="grow h-2 rounded-full bg-gray-200 overflow-hidden">
									<div
										class="h-full {budgetBarColor} transition-all"
										style="width: {Math.min(budgetSpentPct, 100)}%"
									></div>
								</div>
								<span class="text-xs text-gray-700 shrink-0 tabular-nums">
									{budgetSpentPct.toFixed(0)}%
								</span>
							</div>
						{/if}
					{/if}
				</div>
			</div>

			<div>
				<div class="flex items-center justify-between mb-2">
					<h3 class="text-md font-semibold">{m.tolerances()}</h3>
				</div>
				<p class="text-xs text-gray-500 mb-4">{m.tolerancesHelpText()}</p>

				{#if scheduleEditing}
					<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
						<fieldset class="border border-gray-200 rounded p-3">
							<legend class="text-xs font-semibold text-gray-500 uppercase px-1">{m.time()}</legend>
							<div class="grid grid-cols-2 gap-2 mt-2">
								<label class="text-xs text-gray-600">
									+ {m.days()}
									<input
										type="number"
										min="0"
										bind:value={
											() => scheduleDraft.tolerances.time?.plus_days,
											(v) => {
												scheduleDraft.tolerances.time = {
													...scheduleDraft.tolerances.time,
													plus_days: v
												};
											}
										}
										class="input w-full mt-1"
									/>
								</label>
								<label class="text-xs text-gray-600">
									− {m.days()}
									<input
										type="number"
										min="0"
										bind:value={
											() => scheduleDraft.tolerances.time?.minus_days,
											(v) => {
												scheduleDraft.tolerances.time = {
													...scheduleDraft.tolerances.time,
													minus_days: v
												};
											}
										}
										class="input w-full mt-1"
									/>
								</label>
							</div>
						</fieldset>
						<fieldset class="border border-gray-200 rounded p-3">
							<legend class="text-xs font-semibold text-gray-500 uppercase px-1">{m.cost()}</legend>
							<div class="grid grid-cols-2 gap-2 mt-2">
								<label class="text-xs text-gray-600">
									+ %
									<input
										type="number"
										min="0"
										step="0.1"
										bind:value={
											() => scheduleDraft.tolerances.cost?.plus_pct,
											(v) => {
												scheduleDraft.tolerances.cost = {
													...scheduleDraft.tolerances.cost,
													plus_pct: v
												};
											}
										}
										class="input w-full mt-1"
									/>
								</label>
								<label class="text-xs text-gray-600">
									− %
									<input
										type="number"
										min="0"
										step="0.1"
										bind:value={
											() => scheduleDraft.tolerances.cost?.minus_pct,
											(v) => {
												scheduleDraft.tolerances.cost = {
													...scheduleDraft.tolerances.cost,
													minus_pct: v
												};
											}
										}
										class="input w-full mt-1"
									/>
								</label>
							</div>
						</fieldset>
						<label class="block">
							<span class="text-xs font-semibold text-gray-500 uppercase">{m.scope()}</span>
							<input
								type="text"
								bind:value={scheduleDraft.tolerances.scope}
								class="input w-full mt-1"
							/>
						</label>
						<label class="block">
							<span class="text-xs font-semibold text-gray-500 uppercase">{m.quality()}</span>
							<input
								type="text"
								bind:value={scheduleDraft.tolerances.quality}
								class="input w-full mt-1"
							/>
						</label>
						<label class="block">
							<span class="text-xs font-semibold text-gray-500 uppercase">{m.benefits()}</span>
							<input
								type="text"
								bind:value={scheduleDraft.tolerances.benefits}
								class="input w-full mt-1"
							/>
						</label>
						<label class="block">
							<span class="text-xs font-semibold text-gray-500 uppercase">{m.risk()}</span>
							<input
								type="text"
								bind:value={scheduleDraft.tolerances.risk}
								class="input w-full mt-1"
							/>
						</label>
					</div>
				{:else}
					{@const t = project.tolerances ?? {}}
					{#if !t || Object.keys(t).length === 0}
						<p class="text-gray-400 italic text-sm">--</p>
					{:else}
						<dl class="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
							{#if t.time}
								<div class="border-l-2 border-gray-200 pl-3">
									<dt class="text-xs font-semibold text-gray-500 uppercase">{m.time()}</dt>
									<dd class="text-gray-900">
										+{t.time.plus_days ?? 0} / −{t.time.minus_days ?? 0}
										{m.days()}
									</dd>
								</div>
							{/if}
							{#if t.cost}
								<div class="border-l-2 border-gray-200 pl-3">
									<dt class="text-xs font-semibold text-gray-500 uppercase">{m.cost()}</dt>
									<dd class="text-gray-900">
										+{t.cost.plus_pct ?? 0}% / −{t.cost.minus_pct ?? 0}%
									</dd>
								</div>
							{/if}
							{#each ['scope', 'quality', 'benefits', 'risk'] as k}
								{#if t[k]}
									<div class="border-l-2 border-gray-200 pl-3">
										<dt class="text-xs font-semibold text-gray-500 uppercase">
											{safeTranslate(k)}
										</dt>
										<dd class="text-gray-900">{t[k]}</dd>
									</div>
								{/if}
							{/each}
						</dl>
					{/if}
				{/if}
			</div>
		</Tabs.Content>

		<!-- SCOPE -->
		{#if !isPortfolio}<Tabs.Content value="scope" class="p-6">
			<div class="flex items-center justify-between mb-4">
				<h2 class="text-lg font-semibold">{m.scope()}</h2>
				{#if !scopeEditing}
					<button class="btn preset-tonal-primary btn-sm" onclick={startScopeEdit}>
						<i class="fa-solid fa-pen mr-2"></i>{m.edit()}
					</button>
				{:else}
					<div class="flex gap-2">
						<button
							class="btn preset-tonal-surface btn-sm"
							onclick={() => (scopeEditing = false)}
							disabled={savingSection === 'scope'}>{m.cancel()}</button
						>
						<button
							class="btn preset-filled-primary-500 btn-sm"
							onclick={saveScope}
							disabled={savingSection === 'scope'}
						>
							{#if savingSection === 'scope'}<i class="fa-solid fa-spinner fa-spin mr-2"
								></i>{/if}{m.save()}
						</button>
					</div>
				{/if}
			</div>

			{#if errorMessage && scopeEditing}
				<div class="card preset-tonal-error p-3 mb-4 text-sm">{errorMessage}</div>
			{/if}

			<div class="space-y-6">
				{#each scopeFields as section}
					<div class="border-l-2 border-gray-200 pl-4">
						<h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
							{section.label}
						</h3>
						{#if scopeEditing}
							<MarkdownField
								label=""
								bind:value={scopeDraft[section.key]}
								rows={4}
								placeholder={section.label}
							/>
						{:else if project[section.key]}
							<div class="prose prose-sm max-w-none text-gray-900">
								<MarkdownRenderer content={project[section.key]} />
							</div>
						{:else}
							<p class="text-gray-400 italic text-sm">--</p>
						{/if}
					</div>
				{/each}
			</div>
		</Tabs.Content>

{/if}

		<!-- LINKED -->
		<Tabs.Content value="linked" class="p-6">
			<div class="flex items-center justify-between mb-4">
				<h2 class="text-lg font-semibold">{m.linked()}</h2>
				{#if !linkedEditing}
					<button class="btn preset-tonal-primary btn-sm" onclick={startLinkedEdit}>
						<i class="fa-solid fa-pen mr-2"></i>{m.edit()}
					</button>
				{:else}
					<div class="flex gap-2">
						<button
							class="btn preset-tonal-surface btn-sm"
							onclick={() => (linkedEditing = false)}
							disabled={savingSection === 'linked'}>{m.cancel()}</button
						>
						<button
							class="btn preset-filled-primary-500 btn-sm"
							onclick={saveLinked}
							disabled={savingSection === 'linked'}
						>
							{#if savingSection === 'linked'}<i class="fa-solid fa-spinner fa-spin mr-2"
								></i>{/if}{m.save()}
						</button>
					</div>
				{/if}
			</div>

			{#if errorMessage && linkedEditing}
				<div class="card preset-tonal-error p-3 mb-4 text-sm">{errorMessage}</div>
			{/if}

			<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
				<div>
					<label for="lk-coll" class="text-xs font-semibold text-gray-500 uppercase mb-1 block">
						{m.linkedCollection()}
					</label>
					{#if linkedEditing}
						<select id="lk-coll" bind:value={linkedDraft.linked_collection} class="select w-full">
							<option value={null}>--</option>
							{#each collectionOptions as opt}
								<option value={opt.id}>{opt.str ?? opt.name}</option>
							{/each}
						</select>
					{:else if project.linked_collection}
						<Anchor
							href="/generic-collections/{project.linked_collection.id}"
							class="text-primary-600 hover:text-primary-800 hover:underline text-sm"
						>
							{project.linked_collection.str}
						</Anchor>
					{:else}
						<span class="text-gray-400 text-sm">--</span>
					{/if}
				</div>

				<div>
					<label for="lk-parent" class="text-xs font-semibold text-gray-500 uppercase mb-1 block">
						{m.parentProject()}
					</label>
					{#if linkedEditing}
						<select id="lk-parent" bind:value={linkedDraft.parent_project} class="select w-full">
							<option value={null}>--</option>
							{#each projectOptions as opt}
								<option value={opt.id}>{opt.str ?? opt.name}</option>
							{/each}
						</select>
					{:else if project.parent_project}
						<Anchor
							href="/projects/{project.parent_project.id}"
							class="text-primary-600 hover:text-primary-800 hover:underline text-sm"
						>
							{project.parent_project.str}
						</Anchor>
					{:else}
						<span class="text-gray-400 text-sm">--</span>
					{/if}
				</div>

				<div>
					<div class="text-xs font-semibold text-gray-500 uppercase mb-1">{m.subProjects()}</div>
					{#if project.sub_projects && project.sub_projects.length > 0}
						<ul class="space-y-1">
							{#each project.sub_projects as sub}
								<li class="text-sm">
									<Anchor
										href="/projects/{sub.id}"
										class="text-primary-600 hover:text-primary-800 hover:underline"
									>
										{sub.str}
									</Anchor>
								</li>
							{/each}
						</ul>
					{:else}
						<span class="text-gray-400 text-sm italic">{m.noSubProjects()}</span>
					{/if}
				</div>

				<div>
					<div class="text-xs font-semibold text-gray-500 uppercase mb-1">
						{m.responsibilityMatrices()}
					</div>
					{#if project.responsibility_matrices && project.responsibility_matrices.length > 0}
						<ul class="space-y-1">
							{#each project.responsibility_matrices as matrix}
								<li class="text-sm">
									<Anchor
										href="/responsibility-matrices/{matrix.id}"
										class="text-primary-600 hover:text-primary-800 hover:underline"
									>
										{matrix.str}
									</Anchor>
								</li>
							{/each}
						</ul>
					{:else}
						<span class="text-gray-400 text-sm italic">{m.noResponsibilityMatrices()}</span>
					{/if}
				</div>
			</div>
		</Tabs.Content>

		<!-- PEOPLE -->
		<Tabs.Content value="people" class="p-6">
			<div class="flex items-center justify-between mb-4">
				<h2 class="text-lg font-semibold">{m.people()}</h2>
				{#if !peopleEditing}
					<button class="btn preset-tonal-primary btn-sm" onclick={startPeopleEdit}>
						<i class="fa-solid fa-pen mr-2"></i>{m.edit()}
					</button>
				{:else}
					<div class="flex gap-2">
						<button
							class="btn preset-tonal-surface btn-sm"
							onclick={() => (peopleEditing = false)}
							disabled={savingSection === 'people'}>{m.cancel()}</button
						>
						<button
							class="btn preset-filled-primary-500 btn-sm"
							onclick={savePeople}
							disabled={savingSection === 'people'}
						>
							{#if savingSection === 'people'}<i class="fa-solid fa-spinner fa-spin mr-2"
								></i>{/if}{m.save()}
						</button>
					</div>
				{/if}
			</div>

			{#if errorMessage && peopleEditing}
				<div class="card preset-tonal-error p-3 mb-4 text-sm">{errorMessage}</div>
			{/if}

			<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
				<div>
					<label for="pp-owner" class="text-xs font-semibold text-gray-500 uppercase mb-1 block">
						{m.owner()}
					</label>
					<p class="text-xs text-gray-500 mb-2">{m.projectOwnerHelpText()}</p>
					{#if peopleEditing}
						<select id="pp-owner" bind:value={peopleDraft.owner} class="select w-full">
							<option value={null}>--</option>
							{#each actorOptions as opt}
								<option value={opt.id}>{opt.str ?? opt.email ?? opt.id}</option>
							{/each}
						</select>
					{:else}
						<span class="text-sm text-gray-900">{project.owner?.str ?? '--'}</span>
					{/if}
				</div>

				<div>
					<label for="pp-sponsor" class="text-xs font-semibold text-gray-500 uppercase mb-1 block">
						{m.sponsor()}
					</label>
					<p class="text-xs text-gray-500 mb-2">{m.projectSponsorHelpText()}</p>
					{#if peopleEditing}
						<select id="pp-sponsor" bind:value={peopleDraft.sponsor} class="select w-full">
							<option value={null}>--</option>
							{#each actorOptions as opt}
								<option value={opt.id}>{opt.str ?? opt.email ?? opt.id}</option>
							{/each}
						</select>
					{:else}
						<span class="text-sm text-gray-900">{project.sponsor?.str ?? '--'}</span>
					{/if}
				</div>
			</div>
		</Tabs.Content>

		<!-- ANALYTICS -->
		<Tabs.Content value="analytics" class="p-6">
			<h2 class="text-lg font-semibold mb-4">{m.analytics()}</h2>

			{#if snapshots.length === 0}
				<div class="text-center py-12 text-gray-400">
					<i class="fa-solid fa-chart-line text-3xl mb-3"></i>
					<p class="text-sm">{m.noSnapshotsYet()}</p>
				</div>
			{:else}
				<!-- KPI strip -->
				<div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
					<div class="rounded-lg bg-gray-50 p-4">
						<div class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
							{m.progress()}
						</div>
						<div class="flex items-baseline gap-2">
							<span class="text-2xl font-bold text-gray-900">{latestSnapshot?.progress ?? 0}%</span>
							{#if progressDelta7d != null}
								<span
									class="text-xs font-medium"
									class:text-green-600={progressDelta7d > 0}
									class:text-gray-500={progressDelta7d === 0}
									class:text-red-600={progressDelta7d < 0}
								>
									{progressDelta7d >= 0 ? '+' : ''}{progressDelta7d}
									{m.last7Days()}
								</span>
							{/if}
						</div>
					</div>
					<div class="rounded-lg bg-gray-50 p-4">
						<div class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
							{m.projectStatus()}
						</div>
						<span
							class="badge text-sm font-medium px-2.5 py-0.5 rounded-full {statusColorMap[
								latestSnapshot?.status
							] ?? 'bg-gray-100 text-gray-600'}"
						>
							{safeTranslate(latestSnapshot?.status ?? '--')}
						</span>
					</div>
					<div class="rounded-lg bg-gray-50 p-4">
						<div class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
							{m.projectHealth()}
						</div>
						<span
							class="badge text-sm font-medium px-2.5 py-0.5 rounded-full {healthColorMap[
								latestSnapshot?.health
							] ?? 'bg-gray-100 text-gray-600'}"
						>
							{safeTranslate(latestSnapshot?.health ?? '--')}
						</span>
					</div>
					<div class="rounded-lg bg-gray-50 p-4">
						<div class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
							{m.actualCost()}
						</div>
						<div class="text-lg font-bold text-gray-900">
							{latestSnapshot?.actual_cost ?? '--'}
							{#if latestSnapshot?.budget}
								<span class="text-xs text-gray-500 font-normal">
									/ {latestSnapshot.budget}
									{latestSnapshot.currency ?? ''}
								</span>
							{/if}
						</div>
					</div>
				</div>

				<!-- Lifecycle multi-curve area chart -->
				<div class="mb-6">
					<div class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
						{m.lifecycle()} — {m.timeline()}
					</div>
					<div bind:this={lifecycleChartEl} style="width: 100%; height: 320px;"></div>
				</div>

				<!-- Charts -->
				<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
					<div>
						<div class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
							{m.progress()}
						</div>
						<div bind:this={progressChartEl} style="width: 100%; height: 240px;"></div>
					</div>
					<div>
						<div class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
							{m.financials()}
						</div>
						<div bind:this={budgetChartEl} style="width: 100%; height: 240px;"></div>
					</div>
				</div>
			{/if}
		</Tabs.Content>
	</Tabs>
</div>
