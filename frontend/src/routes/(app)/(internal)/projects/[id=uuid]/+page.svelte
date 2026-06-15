<script lang="ts">
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import { Tabs } from '@skeletonlabs/skeleton-svelte';
	import { invalidateAll } from '$app/navigation';
	import { page } from '$app/state';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import MarkdownField from '$lib/components/Forms/MarkdownField.svelte';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import Select from '$lib/components/Forms/Select.svelte';
	import SliderInput from '$lib/components/Forms/SliderInput.svelte';
	import { defaults, superForm } from 'sveltekit-superforms';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { z } from 'zod';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	let project = $derived(data.data);
	let priorityOptions = $derived(data.priorityOptions);
	let kindOptions = $derived(data.kindOptions);
	let currencyOptions = $derived(data.currencyOptions);
	let statusOptions = $derived(data.statusOptions);
	let healthOptions = $derived(data.healthOptions);

	const workspaceFieldsSchema = z.object({
		kind: z.string().optional(),
		parent_project: z.string().uuid().nullable().optional(),
		status: z.string().uuid().nullable().optional(),
		health: z.string().uuid().nullable().optional(),
		priority: z.coerce.number().int().min(1).max(4).nullable().optional(),
		linked_collection: z.string().uuid().nullable().optional(),
		responsibility_matrices: z.array(z.string().uuid()).default([]),
		filtering_labels: z.array(z.string().uuid()).default([]),
		owner: z.string().uuid().nullable().optional(),
		sponsor: z.string().uuid().nullable().optional(),
		currency: z.string().nullable().optional()
	});

	function snapshotWorkspaceFields(p: any) {
		return {
			kind: p.kind ?? 'project',
			parent_project: p.parent_project?.id ?? null,
			status: p.status?.id ?? null,
			health: p.health?.id ?? null,
			priority: p.priority ?? null,
			linked_collection: p.linked_collection?.id ?? null,
			responsibility_matrices: (p.responsibility_matrices ?? []).map((m: any) => m.id),
			filtering_labels: (p.filtering_labels ?? []).map((l: any) => l.id),
			owner: p.owner?.id ?? null,
			sponsor: p.sponsor?.id ?? null,
			currency: p.currency ?? ''
		};
	}

	const workspaceForm = superForm(
		defaults(snapshotWorkspaceFields(data.data), zod(workspaceFieldsSchema)),
		{
			dataType: 'json',
			SPA: true,
			validators: zod(workspaceFieldsSchema)
		}
	);

	function resetWorkspaceFields() {
		workspaceForm.form.set(snapshotWorkspaceFields(project));
	}

	const { form: workspaceFormData } = workspaceForm;

	let activeTab = $state('overview');
	// Opening a section resets workspaceForm — only one section can edit at a time.
	type EditSection = 'basics' | 'overview' | 'charter' | 'schedule' | 'scope' | 'linked' | 'people';
	let editingSection: EditSection | null = $state(null);
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
	const kindStripeMap: Record<string, string> = {
		portfolio: 'bg-purple-500',
		program: 'bg-blue-500',
		project: 'bg-slate-400'
	};
	const kindHeaderBgMap: Record<string, string> = {
		portfolio:
			'bg-gradient-to-br from-purple-50/70 via-white to-white dark:from-surface-800 dark:via-surface-950 dark:to-surface-950',
		program:
			'bg-gradient-to-br from-blue-50/70 via-white to-white dark:from-surface-800 dark:via-surface-950 dark:to-surface-950',
		project:
			'bg-gradient-to-br from-slate-50/70 via-white to-white dark:from-surface-800 dark:via-surface-950 dark:to-surface-950'
	};
	const priorityColorMap: Record<number, string> = {
		1: 'bg-red-100 text-red-700',
		2: 'bg-amber-100 text-amber-700',
		3: 'bg-blue-100 text-blue-700',
		4: 'bg-gray-100 text-gray-600'
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
				const pick = err?.detail ?? err?.non_field_errors ?? Object.values(err ?? {})[0];
				const text = Array.isArray(pick) ? pick[0] : pick;
				errorMessage = String(text || `HTTP ${res.status}`);
				return false;
			}
			await invalidateAll();
			return true;
		} finally {
			savingSection = null;
		}
	}

	let overviewProgressDraft: number | null = $state(null);

	function startOverviewEdit() {
		resetWorkspaceFields();
		overviewProgressDraft = project.progress ?? null;
		editingSection = 'overview';
	}

	async function saveOverview() {
		const payload = {
			status: $workspaceFormData.status,
			health: $workspaceFormData.health,
			priority: $workspaceFormData.priority,
			progress: overviewProgressDraft
		};
		if ((await patchProject(payload, 'overview')) === true) editingSection = null;
	}

	const charterFields = [
		{ key: 'purpose', label: m.purpose() },
		{ key: 'objectives', label: m.objectives() },
		{ key: 'success_criteria', label: m.successCriteria() },
		{ key: 'business_case', label: m.businessCase() },
		{ key: 'approval_requirements', label: m.approvalRequirements() },
		{ key: 'exit_criteria', label: m.exitCriteria() },
		{ key: 'organizational_alignment', label: m.organizationalAlignment() }
	] as const;

	let charterDraft: Record<string, string> = $state({});

	function startCharterEdit() {
		charterDraft = Object.fromEntries(charterFields.map((f) => [f.key, project[f.key] ?? '']));
		editingSection = 'charter';
	}

	async function saveCharter() {
		if ((await patchProject(charterDraft, 'charter')) === true) editingSection = null;
	}

	let scheduleDraft: {
		start_date: string | null;
		end_date: string | null;
		eta: string | null;
		budget: number | null;
		actual_cost: number | null;
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
		tolerances: {}
	});

	function startScheduleEdit() {
		resetWorkspaceFields();
		scheduleDraft = {
			start_date: project.start_date ?? null,
			end_date: project.end_date ?? null,
			eta: project.eta ?? null,
			budget: project.budget ?? null,
			actual_cost: project.actual_cost ?? null,
			tolerances: structuredClone(project.tolerances ?? {})
		};
		editingSection = 'schedule';
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
		// Project.currency is CharField(blank=True), so null is rejected — coerce.
		const payload = { ...scheduleDraft, currency: $workspaceFormData.currency ?? '' };
		if ((await patchProject(payload, 'schedule')) === true) editingSection = null;
	}

	const scopeFields = [
		{ key: 'deliverables', label: m.deliverables() },
		{ key: 'assumptions', label: m.assumptions() },
		{ key: 'constraints', label: m.constraints() },
		{ key: 'dependencies_note', label: m.dependenciesNote() }
	] as const;

	let scopeDraft: Record<string, string> = $state({});

	function startScopeEdit() {
		scopeDraft = Object.fromEntries(scopeFields.map((f) => [f.key, project[f.key] ?? '']));
		editingSection = 'scope';
	}

	async function saveScope() {
		if ((await patchProject(scopeDraft, 'scope')) === true) editingSection = null;
	}

	function startLinkedEdit() {
		resetWorkspaceFields();
		editingSection = 'linked';
	}

	async function saveLinked() {
		const payload = {
			linked_collection: $workspaceFormData.linked_collection,
			responsibility_matrices: $workspaceFormData.responsibility_matrices,
			filtering_labels: $workspaceFormData.filtering_labels
		};
		if ((await patchProject(payload, 'linked')) === true) editingSection = null;
	}

	function startPeopleEdit() {
		resetWorkspaceFields();
		editingSection = 'people';
	}

	async function savePeople() {
		const payload = {
			owner: $workspaceFormData.owner,
			sponsor: $workspaceFormData.sponsor
		};
		if ((await patchProject(payload, 'people')) === true) editingSection = null;
	}

	let basicsTextDraft: {
		name: string;
		ref_id: string;
		ref_link: string;
		description: string;
	} = $state({ name: '', ref_id: '', ref_link: '', description: '' });

	function startBasicsEdit() {
		resetWorkspaceFields();
		basicsTextDraft = {
			name: project.name ?? '',
			ref_id: project.ref_id ?? '',
			ref_link: project.ref_link ?? '',
			description: project.description ?? ''
		};
		editingSection = 'basics';
	}

	async function saveBasics() {
		const payload = {
			...basicsTextDraft,
			kind: $workspaceFormData.kind,
			parent_project: $workspaceFormData.parent_project
		};
		if ((await patchProject(payload, 'basics')) === true) editingSection = null;
	}

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
			progressChart = echarts.init(
				progressChartEl,
				document.documentElement.classList.contains('dark') ? 'dark' : null,
				{ renderer: 'svg' }
			);
			progressChart.setOption({
				backgroundColor: 'transparent',
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
			lifecycleChart = echarts.init(
				lifecycleChartEl,
				document.documentElement.classList.contains('dark') ? 'dark' : null,
				{ renderer: 'svg' }
			);
			const seriesLabels = [m.status(), m.projectHealth(), m.priority()];
			const esc = (s: unknown) =>
				String(s ?? '')
					.replace(/&/g, '&amp;')
					.replace(/</g, '&lt;')
					.replace(/>/g, '&gt;')
					.replace(/"/g, '&quot;')
					.replace(/'/g, '&#39;');
			lifecycleChart.setOption({
				backgroundColor: 'transparent',
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
							return `<div style="display:flex;justify-content:space-between;gap:12px;"><span>${p.marker} ${esc(label)}</span><strong>${esc(value)}</strong></div>`;
						});
						return `<div style="font-weight:600;margin-bottom:4px;">${esc(date)}</div>${lines.join('')}`;
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
						name: m.status(),
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
						name: m.priority(),
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

<div class="card bg-surface-50-950 shadow-sm m-4">
	<div class="h-1 rounded-t-container-token {kindStripeMap[project.kind] ?? 'bg-slate-400'}"></div>

	<div class="px-8 pt-6 pb-5 {kindHeaderBgMap[project.kind] ?? ''}">
		<div class="flex items-start justify-between gap-4 flex-wrap">
			<div class="min-w-0 grow">
				{#if editingSection !== 'basics'}
					<div class="group flex items-center gap-3 flex-wrap">
						<span
							class="badge text-sm font-semibold px-3 py-1 rounded-full {kindColorMap[
								project.kind
							] ?? 'bg-surface-100-900 text-surface-700-300'}"
							title={safeTranslate(project.kind)}
						>
							<i class="{kindIconMap[project.kind] ?? 'fa-solid fa-clipboard-list'} mr-1.5"></i>
							{safeTranslate(project.kind)}
						</span>
						<h1 class="text-3xl font-bold text-surface-900-100 truncate">{project.name}</h1>
						{#if project.ref_id}
							<span
								class="text-xs font-mono text-surface-600-400 bg-surface-50-950/70 border border-surface-200-800 px-2 py-0.5 rounded"
								>{project.ref_id}</span
							>
						{/if}
						<button
							onclick={startBasicsEdit}
							class="opacity-0 group-hover:opacity-100 transition-opacity text-surface-500 hover:text-primary-600"
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
							class="text-primary-600 hover:text-primary-800 hover:underline text-sm inline-flex items-center gap-1 mt-2"
						>
							<i class="fa-solid fa-arrow-up-right-from-square text-xs"></i>
							{project.ref_link}
						</a>
					{/if}
					{#if project.description}
						<div class="prose prose-sm max-w-3xl text-surface-700-300 mt-3">
							<MarkdownRenderer content={project.description} />
						</div>
					{/if}
				{:else}
					<div class="space-y-3 max-w-3xl">
						<Select
							form={workspaceForm}
							options={kindOptions}
							field="kind"
							label={m.kind()}
							disableDoubleDash={true}
						/>
						<label class="block">
							<span class="text-xs font-semibold text-surface-600-400 uppercase">{m.name()}</span>
							<input
								type="text"
								bind:value={basicsTextDraft.name}
								class="input w-full mt-1"
								required
							/>
						</label>
						<label class="block">
							<span class="text-xs font-semibold text-surface-600-400 uppercase">{m.refId()}</span>
							<input
								type="text"
								maxlength="100"
								bind:value={basicsTextDraft.ref_id}
								class="input w-full mt-1"
							/>
						</label>
						<label class="block">
							<span class="text-xs font-semibold text-surface-600-400 uppercase">{m.refLink()}</span
							>
							<input
								type="url"
								bind:value={basicsTextDraft.ref_link}
								class="input w-full mt-1"
								placeholder="https://…"
							/>
						</label>
						<AutocompleteSelect
							form={workspaceForm}
							optionsEndpoint="projects"
							optionsLabelField="auto"
							optionsExtraFields={[['folder', 'str']]}
							optionsInfoFields={{
								fields: [{ field: 'kind', translate: true }],
								position: 'prefix'
							}}
							optionsSelf={project}
							field="parent_project"
							nullable={true}
							label={m.parentProject()}
						/>
						<div class="block">
							<span class="text-xs font-semibold text-surface-600-400 uppercase"
								>{m.description()}</span
							>
							<div class="mt-1">
								<MarkdownField label="" bind:value={basicsTextDraft.description} rows={4} />
							</div>
						</div>
					</div>
				{/if}
			</div>

			{#if editingSection === 'basics'}
				<div class="shrink-0 flex gap-2">
					<button
						class="btn preset-tonal-surface btn-sm"
						onclick={() => (editingSection = null)}
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

		{#if errorMessage && editingSection === 'basics'}
			<div class="card preset-tonal-error p-3 mt-3 text-sm">{errorMessage}</div>
		{/if}
	</div>
	<div class="px-8 py-4 border-t border-surface-200-800">
		<div class="grid grid-cols-2 md:grid-cols-4 gap-6">
			<div class="flex flex-col gap-1.5">
				<div class="text-[10px] font-semibold text-surface-600-400 uppercase tracking-wider">
					{m.status()}
				</div>
				{#if project.status}
					<span
						class="badge text-sm font-semibold px-3 py-1 rounded-full self-start {statusColorMap[
							project.status?.name
						] ?? 'bg-surface-100-900 text-surface-600-400'}"
						>{safeTranslate(project.status.name)}</span
					>
				{:else}
					<span class="text-surface-500 text-sm italic">—</span>
				{/if}
			</div>

			<div class="flex flex-col gap-1.5">
				<div class="text-[10px] font-semibold text-surface-600-400 uppercase tracking-wider">
					{m.projectHealth()}
				</div>
				{#if project.health}
					<span
						class="badge text-sm font-semibold px-3 py-1 rounded-full self-start {healthColorMap[
							project.health?.name
						] ?? 'bg-surface-100-900 text-surface-600-400'}"
						>{safeTranslate(project.health.name)}</span
					>
				{:else}
					<span class="text-surface-500 text-sm italic">—</span>
				{/if}
			</div>

			<div class="flex flex-col gap-1.5">
				<div class="text-[10px] font-semibold text-surface-600-400 uppercase tracking-wider">
					{m.priority()}
				</div>
				{#if project.priority}
					<span
						class="badge text-sm font-semibold px-3 py-1 rounded-full self-start {priorityColorMap[
							project.priority
						] ?? 'bg-surface-100-900 text-surface-600-400'}">P{project.priority}</span
					>
				{:else}
					<span class="text-surface-500 text-sm italic">—</span>
				{/if}
			</div>

			<div class="flex flex-col gap-1.5">
				<div class="text-[10px] font-semibold text-surface-600-400 uppercase tracking-wider">
					{m.progress()}
				</div>
				<div class="flex items-center gap-3">
					<span class="text-lg font-bold text-surface-900-100 tabular-nums leading-none"
						>{progressValue}%</span
					>
					<div class="grow h-2 rounded-full bg-surface-200-800 overflow-hidden">
						<div class="h-full bg-primary-500 transition-all" style="width: {progressValue}%"></div>
					</div>
				</div>
			</div>
		</div>
	</div>
	<div class="px-8 py-3 bg-surface-50-950 border-t border-surface-200-800">
		<div class="grid grid-cols-2 md:grid-cols-4 gap-6 text-sm">
			<div>
				<div class="text-[10px] font-semibold text-surface-600-400 uppercase tracking-wider mb-1">
					{m.owner()}
				</div>
				{#if project.owner}
					<span class="text-surface-900-100 truncate block">{project.owner.str}</span>
				{:else}
					<span class="text-surface-500 italic">—</span>
				{/if}
			</div>
			<div>
				<div class="text-[10px] font-semibold text-surface-600-400 uppercase tracking-wider mb-1">
					{m.sponsor()}
				</div>
				{#if project.sponsor}
					<span class="text-surface-900-100 truncate block">{project.sponsor.str}</span>
				{:else}
					<span class="text-surface-500 italic">—</span>
				{/if}
			</div>
			<div>
				<div class="text-[10px] font-semibold text-surface-600-400 uppercase tracking-wider mb-1">
					{m.parentProject()}
				</div>
				{#if project.parent_project}
					<Anchor
						href="/projects/{project.parent_project.id}"
						class="text-primary-600 hover:text-primary-800 hover:underline truncate block"
					>
						{project.parent_project.str}
					</Anchor>
				{:else}
					<span class="text-surface-500 italic">—</span>
				{/if}
			</div>
			<div>
				<div class="text-[10px] font-semibold text-surface-600-400 uppercase tracking-wider mb-1">
					{m.subProjects()}
				</div>
				{#if project.sub_projects && project.sub_projects.length > 0}
					<div class="flex flex-wrap gap-1">
						{#each project.sub_projects as sub}
							<Anchor
								href="/projects/{sub.id}"
								class="text-xs px-2 py-0.5 bg-surface-50-950 border border-surface-200-800 rounded-full text-surface-700-300 hover:bg-surface-100-900 hover:border-surface-300-700 truncate max-w-[10rem]"
							>
								{sub.str}
							</Anchor>
						{/each}
					</div>
				{:else}
					<span class="text-surface-500 italic">—</span>
				{/if}
			</div>
		</div>
	</div>
	<Tabs value={activeTab} onValueChange={(e) => (activeTab = e.value)} class="w-full">
		<Tabs.List class="border-b border-surface-200-800 px-4">
			<Tabs.Trigger
				value="overview"
				class="px-4 py-3 text-sm font-medium text-surface-600-400 hover:text-surface-700-300 border-b-2 border-transparent transition-colors aria-[selected=true]:!text-primary-700 aria-[selected=true]:!border-primary-500"
			>
				<i class="fa-solid fa-gauge-high mr-2"></i>{m.overview()}
			</Tabs.Trigger>
			<Tabs.Trigger
				value="charter"
				class="px-4 py-3 text-sm font-medium text-surface-600-400 hover:text-surface-700-300 border-b-2 border-transparent transition-colors aria-[selected=true]:!text-primary-700 aria-[selected=true]:!border-primary-500"
			>
				<i class="fa-solid fa-file-contract mr-2"></i>{m.charter()}
			</Tabs.Trigger>
			<Tabs.Trigger
				value="schedule"
				class="px-4 py-3 text-sm font-medium text-surface-600-400 hover:text-surface-700-300 border-b-2 border-transparent transition-colors aria-[selected=true]:!text-primary-700 aria-[selected=true]:!border-primary-500"
			>
				<i class="fa-solid fa-calendar mr-2"></i>{m.tracking()}
			</Tabs.Trigger>
			{#if !isPortfolio}<Tabs.Trigger
					value="scope"
					class="px-4 py-3 text-sm font-medium text-surface-600-400 hover:text-surface-700-300 border-b-2 border-transparent transition-colors aria-[selected=true]:!text-primary-700 aria-[selected=true]:!border-primary-500"
				>
					<i class="fa-solid fa-bullseye mr-2"></i>{m.scope()}
				</Tabs.Trigger>{/if}
			<Tabs.Trigger
				value="linked"
				class="px-4 py-3 text-sm font-medium text-surface-600-400 hover:text-surface-700-300 border-b-2 border-transparent transition-colors aria-[selected=true]:!text-primary-700 aria-[selected=true]:!border-primary-500"
			>
				<i class="fa-solid fa-link mr-2"></i>{m.linked()}
			</Tabs.Trigger>
			<Tabs.Trigger
				value="people"
				class="px-4 py-3 text-sm font-medium text-surface-600-400 hover:text-surface-700-300 border-b-2 border-transparent transition-colors aria-[selected=true]:!text-primary-700 aria-[selected=true]:!border-primary-500"
			>
				<i class="fa-solid fa-users mr-2"></i>{m.people()}
			</Tabs.Trigger>
			<Tabs.Trigger
				value="analytics"
				class="px-4 py-3 text-sm font-medium text-surface-600-400 hover:text-surface-700-300 border-b-2 border-transparent transition-colors aria-[selected=true]:!text-primary-700 aria-[selected=true]:!border-primary-500"
			>
				<i class="fa-solid fa-chart-line mr-2"></i>{m.analytics()}
			</Tabs.Trigger>
		</Tabs.List>
		<Tabs.Content value="overview" class="p-6">
			<div class="flex justify-end mb-4">
				{#if editingSection !== 'overview'}
					<button class="btn preset-tonal-primary btn-sm" onclick={startOverviewEdit}>
						<i class="fa-solid fa-pen mr-2"></i>{m.edit()}
					</button>
				{:else}
					<div class="flex gap-2">
						<button
							class="btn preset-tonal-surface btn-sm"
							onclick={() => (editingSection = null)}
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

			{#if errorMessage && editingSection === 'overview'}
				<div class="card preset-tonal-error p-3 mb-4 text-sm">{errorMessage}</div>
			{/if}

			<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
				<div>
					{#if editingSection === 'overview'}
						<Select
							form={workspaceForm}
							options={statusOptions}
							field="status"
							label={m.status()}
						/>
					{:else}
						<div class="text-xs font-semibold text-surface-600-400 uppercase mb-1 block">
							{m.status()}
						</div>
						<span class="text-sm text-surface-900-100"
							>{project.status ? safeTranslate(project.status.name) : '--'}</span
						>
					{/if}
				</div>

				<div>
					{#if editingSection === 'overview'}
						<Select
							form={workspaceForm}
							options={healthOptions}
							field="health"
							label={m.projectHealth()}
						/>
					{:else}
						<div class="text-xs font-semibold text-surface-600-400 uppercase mb-1 block">
							{m.projectHealth()}
						</div>
						<span class="text-sm text-surface-900-100"
							>{project.health ? safeTranslate(project.health.name) : '--'}</span
						>
					{/if}
				</div>

				<div>
					{#if editingSection === 'overview'}
						<Select
							form={workspaceForm}
							options={priorityOptions}
							field="priority"
							translateOptions={false}
							label={m.priority()}
						/>
					{:else}
						<div class="text-xs font-semibold text-surface-600-400 uppercase mb-1 block">
							{m.priority()}
						</div>
						<span class="text-sm text-surface-900-100"
							>{project.priority ? `P${project.priority}` : '--'}</span
						>
					{/if}
				</div>

				<div>
					<label class="text-xs font-semibold text-surface-600-400 uppercase mb-1 block">
						{m.progress()}
					</label>
					{#if editingSection === 'overview'}
						<SliderInput
							mode="number"
							value={overviewProgressDraft}
							min={0}
							max={100}
							step={5}
							ariaLabel={m.progress()}
							onChange={(v) => (overviewProgressDraft = typeof v === 'number' ? v : null)}
						/>
					{:else}
						<span class="text-sm text-surface-900-100">{progressValue}%</span>
					{/if}
				</div>
			</div>
		</Tabs.Content>
		<Tabs.Content value="charter" class="p-6">
			<div class="flex justify-end mb-4">
				{#if editingSection !== 'charter'}
					<button class="btn preset-tonal-primary btn-sm" onclick={startCharterEdit}>
						<i class="fa-solid fa-pen mr-2"></i>{m.edit()}
					</button>
				{:else}
					<div class="flex gap-2">
						<button
							class="btn preset-tonal-surface btn-sm"
							onclick={() => (editingSection = null)}
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

			{#if errorMessage && editingSection === 'charter'}
				<div class="card preset-tonal-error p-3 mb-4 text-sm">{errorMessage}</div>
			{/if}

			<div class="space-y-6">
				{#each charterFields as section}
					<div class="border-l-2 border-surface-200-800 pl-4">
						<h3 class="text-xs font-semibold text-surface-600-400 uppercase tracking-wide mb-2">
							{section.label}
						</h3>
						{#if editingSection === 'charter'}
							<MarkdownField label="" bind:value={charterDraft[section.key]} rows={4} />
						{:else if project[section.key]}
							<div class="prose prose-sm max-w-none text-surface-900-100">
								<MarkdownRenderer content={project[section.key]} />
							</div>
						{:else}
							<p class="text-surface-500 italic text-sm">--</p>
						{/if}
					</div>
				{/each}
			</div>
		</Tabs.Content>
		<Tabs.Content value="schedule" class="p-6">
			<div class="flex justify-end mb-4">
				{#if editingSection !== 'schedule'}
					<button class="btn preset-tonal-primary btn-sm" onclick={startScheduleEdit}>
						<i class="fa-solid fa-pen mr-2"></i>{m.edit()}
					</button>
				{:else}
					<div class="flex gap-2">
						<button
							class="btn preset-tonal-surface btn-sm"
							onclick={() => (editingSection = null)}
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

			{#if errorMessage && editingSection === 'schedule'}
				<div class="card preset-tonal-error p-3 mb-4 text-sm">{errorMessage}</div>
			{/if}

			<section class="mb-8">
				<h3
					class="text-md font-semibold text-surface-800-200 border-b border-surface-200-800 pb-1 mb-4"
				>
					{m.schedule()}
				</h3>
				<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
					<div>
						<label
							for="sc-start"
							class="text-xs font-semibold text-surface-600-400 uppercase mb-1 block"
						>
							{m.startDate()}
						</label>
						{#if editingSection === 'schedule'}
							<input
								id="sc-start"
								type="date"
								bind:value={scheduleDraft.start_date}
								class="input w-full"
							/>
						{:else}
							<span class="text-sm text-surface-900-100">{project.start_date ?? '--'}</span>
						{/if}
					</div>
					<div>
						<label
							for="sc-end"
							class="text-xs font-semibold text-surface-600-400 uppercase mb-1 block"
						>
							{m.endDate()}
						</label>
						{#if editingSection === 'schedule'}
							<input
								id="sc-end"
								type="date"
								bind:value={scheduleDraft.end_date}
								class="input w-full"
							/>
						{:else}
							<span class="text-sm text-surface-900-100">{project.end_date ?? '--'}</span>
						{/if}
					</div>
					<div>
						<label
							for="sc-eta"
							class="text-xs font-semibold text-surface-600-400 uppercase mb-1 block"
						>
							{m.eta()}
						</label>
						{#if editingSection === 'schedule'}
							<input id="sc-eta" type="date" bind:value={scheduleDraft.eta} class="input w-full" />
						{:else}
							<span class="text-sm text-surface-900-100">{project.eta ?? '--'}</span>
						{/if}
					</div>
					<div>
						<div class="text-xs font-semibold text-surface-600-400 uppercase mb-1">
							{m.closedAt()}
						</div>
						<span class="text-sm text-surface-900-100">{project.closed_at ?? '--'}</span>
					</div>
				</div>
			</section>

			<section class="mb-8">
				<h3
					class="text-md font-semibold text-surface-800-200 border-b border-surface-200-800 pb-1 mb-4"
				>
					{m.financials()}
				</h3>
				{#if editingSection === 'schedule'}
					<div class="grid grid-cols-1 md:grid-cols-3 gap-3">
						<label class="block">
							<span class="text-xs font-semibold text-surface-600-400 uppercase">
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
							<span class="text-xs font-semibold text-surface-600-400 uppercase"
								>{m.actualCost()}</span
							>
							<input
								type="number"
								step="0.01"
								bind:value={scheduleDraft.actual_cost}
								class="input w-full mt-1"
							/>
						</label>
						<Select
							form={workspaceForm}
							options={currencyOptions}
							field="currency"
							label={m.currency()}
							translateOptions={false}
						/>
					</div>
				{:else if project.budget == null && project.actual_cost == null}
					<span class="text-sm text-surface-500 italic">--</span>
				{:else}
					<div class="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
						<div>
							<div class="text-xs font-semibold text-surface-600-400 uppercase">
								{m.expectedBudget()}
							</div>
							<div class="text-sm text-surface-900-100">
								{project.budget ?? '--'}{#if project.currency}&nbsp;{project.currency}{/if}
							</div>
						</div>
						<div>
							<div class="text-xs font-semibold text-surface-600-400 uppercase">
								{m.actualCost()}
							</div>
							<div class="text-sm text-surface-900-100">
								{project.actual_cost ?? '--'}{#if project.currency}&nbsp;{project.currency}{/if}
							</div>
						</div>
						<div>
							<div class="text-xs font-semibold text-surface-600-400 uppercase">
								{m.remaining()}
							</div>
							<div
								class="text-sm font-medium"
								class:text-surface-900-100={budgetRemaining == null || budgetRemaining >= 0}
								class:text-red-600={budgetRemaining != null && budgetRemaining < 0}
							>
								{budgetRemaining ?? '--'}{#if project.currency}&nbsp;{project.currency}{/if}
							</div>
						</div>
					</div>
					{#if project.budget != null && Number(project.budget) > 0}
						<div class="flex items-center gap-2">
							<div class="grow h-2 rounded-full bg-surface-200-800 overflow-hidden">
								<div
									class="h-full {budgetBarColor} transition-all"
									style="width: {Math.min(budgetSpentPct, 100)}%"
								></div>
							</div>
							<span class="text-xs text-surface-700-300 shrink-0 tabular-nums">
								{budgetSpentPct.toFixed(0)}%
							</span>
						</div>
					{/if}
				{/if}
			</section>

			<section>
				<h3
					class="text-md font-semibold text-surface-800-200 border-b border-surface-200-800 pb-1 mb-2"
				>
					{m.tolerances()}
				</h3>
				<p class="text-xs text-surface-600-400 mb-4">{m.tolerancesHelpText()}</p>

				{#if editingSection === 'schedule'}
					<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
						<fieldset class="border border-surface-200-800 rounded p-3">
							<legend class="text-xs font-semibold text-surface-600-400 uppercase px-1"
								>{m.time()}</legend
							>
							<div class="grid grid-cols-2 gap-2 mt-2">
								<label class="text-xs text-surface-600-400">
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
								<label class="text-xs text-surface-600-400">
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
						<fieldset class="border border-surface-200-800 rounded p-3">
							<legend class="text-xs font-semibold text-surface-600-400 uppercase px-1"
								>{m.cost()}</legend
							>
							<div class="grid grid-cols-2 gap-2 mt-2">
								<label class="text-xs text-surface-600-400">
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
								<label class="text-xs text-surface-600-400">
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
							<span class="text-xs font-semibold text-surface-600-400 uppercase">{m.scope()}</span>
							<input
								type="text"
								bind:value={scheduleDraft.tolerances.scope}
								class="input w-full mt-1"
							/>
						</label>
						<label class="block">
							<span class="text-xs font-semibold text-surface-600-400 uppercase">{m.quality()}</span
							>
							<input
								type="text"
								bind:value={scheduleDraft.tolerances.quality}
								class="input w-full mt-1"
							/>
						</label>
						<label class="block">
							<span class="text-xs font-semibold text-surface-600-400 uppercase"
								>{m.benefits()}</span
							>
							<input
								type="text"
								bind:value={scheduleDraft.tolerances.benefits}
								class="input w-full mt-1"
							/>
						</label>
						<label class="block">
							<span class="text-xs font-semibold text-surface-600-400 uppercase">{m.risk()}</span>
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
						<p class="text-surface-500 italic text-sm">--</p>
					{:else}
						<dl class="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
							{#if t.time}
								<div class="border-l-2 border-surface-200-800 pl-3">
									<dt class="text-xs font-semibold text-surface-600-400 uppercase">{m.time()}</dt>
									<dd class="text-surface-900-100">
										+{t.time.plus_days ?? 0} / −{t.time.minus_days ?? 0}
										{m.days()}
									</dd>
								</div>
							{/if}
							{#if t.cost}
								<div class="border-l-2 border-surface-200-800 pl-3">
									<dt class="text-xs font-semibold text-surface-600-400 uppercase">{m.cost()}</dt>
									<dd class="text-surface-900-100">
										+{t.cost.plus_pct ?? 0}% / −{t.cost.minus_pct ?? 0}%
									</dd>
								</div>
							{/if}
							{#each ['scope', 'quality', 'benefits', 'risk'] as k}
								{#if t[k]}
									<div class="border-l-2 border-surface-200-800 pl-3">
										<dt class="text-xs font-semibold text-surface-600-400 uppercase">
											{safeTranslate(k)}
										</dt>
										<dd class="text-surface-900-100">{t[k]}</dd>
									</div>
								{/if}
							{/each}
						</dl>
					{/if}
				{/if}
			</section>
		</Tabs.Content>
		{#if !isPortfolio}<Tabs.Content value="scope" class="p-6">
				<div class="flex justify-end mb-4">
					{#if editingSection !== 'scope'}
						<button class="btn preset-tonal-primary btn-sm" onclick={startScopeEdit}>
							<i class="fa-solid fa-pen mr-2"></i>{m.edit()}
						</button>
					{:else}
						<div class="flex gap-2">
							<button
								class="btn preset-tonal-surface btn-sm"
								onclick={() => (editingSection = null)}
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

				{#if errorMessage && editingSection === 'scope'}
					<div class="card preset-tonal-error p-3 mb-4 text-sm">{errorMessage}</div>
				{/if}

				<div class="space-y-6">
					{#each scopeFields as section}
						<div class="border-l-2 border-surface-200-800 pl-4">
							<h3 class="text-xs font-semibold text-surface-600-400 uppercase tracking-wide mb-2">
								{section.label}
							</h3>
							{#if editingSection === 'scope'}
								<MarkdownField label="" bind:value={scopeDraft[section.key]} rows={4} />
							{:else if project[section.key]}
								<div class="prose prose-sm max-w-none text-surface-900-100">
									<MarkdownRenderer content={project[section.key]} />
								</div>
							{:else}
								<p class="text-surface-500 italic text-sm">--</p>
							{/if}
						</div>
					{/each}
				</div>
			</Tabs.Content>
		{/if}
		<Tabs.Content value="linked" class="p-6">
			<div class="flex justify-end mb-4">
				{#if editingSection !== 'linked'}
					<button class="btn preset-tonal-primary btn-sm" onclick={startLinkedEdit}>
						<i class="fa-solid fa-pen mr-2"></i>{m.edit()}
					</button>
				{:else}
					<div class="flex gap-2">
						<button
							class="btn preset-tonal-surface btn-sm"
							onclick={() => (editingSection = null)}
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

			{#if errorMessage && editingSection === 'linked'}
				<div class="card preset-tonal-error p-3 mb-4 text-sm">{errorMessage}</div>
			{/if}

			<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
				<div>
					{#if editingSection === 'linked'}
						<AutocompleteSelect
							form={workspaceForm}
							optionsEndpoint="generic-collections"
							optionsLabelField="auto"
							optionsExtraFields={[['folder', 'str']]}
							field="linked_collection"
							nullable={true}
							label={m.linkedCollection()}
						/>
					{:else}
						<div class="text-xs font-semibold text-surface-600-400 uppercase mb-1 block">
							{m.linkedCollection()}
						</div>
						{#if project.linked_collection}
							<Anchor
								href="/generic-collections/{project.linked_collection.id}"
								class="text-primary-600 hover:text-primary-800 hover:underline text-sm"
							>
								{project.linked_collection.str}
							</Anchor>
						{:else}
							<span class="text-surface-500 text-sm">--</span>
						{/if}
					{/if}
				</div>

				<div class="md:col-span-2">
					{#if editingSection === 'linked'}
						<AutocompleteSelect
							form={workspaceForm}
							optionsEndpoint="responsibility-matrices"
							optionsLabelField="auto"
							optionsExtraFields={[['folder', 'str']]}
							field="responsibility_matrices"
							multiple={true}
							label={m.responsibilityMatrices()}
						/>
					{:else}
						<div class="text-xs font-semibold text-surface-600-400 uppercase mb-1 block">
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
							<span class="text-surface-500 text-sm italic">{m.noResponsibilityMatrices()}</span>
						{/if}
					{/if}
				</div>

				<div class="md:col-span-2">
					{#if editingSection === 'linked'}
						<AutocompleteSelect
							multiple
							form={workspaceForm}
							createFromSelection={true}
							optionsEndpoint="filtering-labels"
							optionsLabelField="label"
							field="filtering_labels"
							helpText={m.labelsHelpText()}
							label={m.labels()}
							translateOptions={false}
							allowUserOptions="append"
						/>
					{:else}
						<div class="text-xs font-semibold text-surface-600-400 uppercase mb-1 block">
							{m.labels()}
						</div>
						{#if project.filtering_labels && project.filtering_labels.length > 0}
							<div class="flex flex-wrap gap-1.5">
								{#each project.filtering_labels as label}
									<span
										class="badge text-xs font-medium px-2 py-0.5 rounded bg-surface-100-900 text-surface-700-300 border border-surface-200-800"
									>
										{label.str}
									</span>
								{/each}
							</div>
						{:else}
							<span class="text-surface-500 text-sm italic">--</span>
						{/if}
					{/if}
				</div>
			</div>
		</Tabs.Content>
		<Tabs.Content value="people" class="p-6">
			<div class="flex justify-end mb-4">
				{#if editingSection !== 'people'}
					<button class="btn preset-tonal-primary btn-sm" onclick={startPeopleEdit}>
						<i class="fa-solid fa-pen mr-2"></i>{m.edit()}
					</button>
				{:else}
					<div class="flex gap-2">
						<button
							class="btn preset-tonal-surface btn-sm"
							onclick={() => (editingSection = null)}
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

			{#if errorMessage && editingSection === 'people'}
				<div class="card preset-tonal-error p-3 mb-4 text-sm">{errorMessage}</div>
			{/if}

			<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
				<div>
					{#if editingSection === 'people'}
						<AutocompleteSelect
							form={workspaceForm}
							optionsEndpoint="actors?user__is_third_party=False"
							optionsLabelField="str"
							optionsInfoFields={{
								fields: [{ field: 'type', translate: true }],
								position: 'prefix'
							}}
							field="owner"
							nullable={true}
							label={m.owner()}
							helpText={m.projectOwnerHelpText()}
						/>
					{:else}
						<div class="text-xs font-semibold text-surface-600-400 uppercase mb-1 block">
							{m.owner()}
						</div>
						<p class="text-xs text-surface-600-400 mb-2">{m.projectOwnerHelpText()}</p>
						<span class="text-sm text-surface-900-100">{project.owner?.str ?? '--'}</span>
					{/if}
				</div>

				<div>
					{#if editingSection === 'people'}
						<AutocompleteSelect
							form={workspaceForm}
							optionsEndpoint="actors?user__is_third_party=False"
							optionsLabelField="str"
							optionsInfoFields={{
								fields: [{ field: 'type', translate: true }],
								position: 'prefix'
							}}
							field="sponsor"
							nullable={true}
							label={m.sponsor()}
							helpText={m.projectSponsorHelpText()}
						/>
					{:else}
						<div class="text-xs font-semibold text-surface-600-400 uppercase mb-1 block">
							{m.sponsor()}
						</div>
						<p class="text-xs text-surface-600-400 mb-2">{m.projectSponsorHelpText()}</p>
						<span class="text-sm text-surface-900-100">{project.sponsor?.str ?? '--'}</span>
					{/if}
				</div>
			</div>
		</Tabs.Content>
		<Tabs.Content value="analytics" class="p-6">
			{#if snapshots.length === 0}
				<div class="text-center py-12 text-surface-500">
					<i class="fa-solid fa-chart-line text-3xl mb-3"></i>
					<p class="text-sm">{m.noSnapshotsYet()}</p>
				</div>
			{:else}
				<div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
					<div
						class="relative rounded-lg bg-surface-50-950 border border-surface-200-800 p-4 overflow-hidden shadow-sm"
					>
						<div class="absolute top-0 inset-x-0 h-1 bg-primary-500"></div>
						<div
							class="text-[10px] font-semibold text-surface-600-400 uppercase tracking-wider mb-2"
						>
							{m.progress()}
						</div>
						<div class="flex items-baseline gap-2">
							<span class="text-3xl font-bold text-surface-900-100 tabular-nums leading-none"
								>{latestSnapshot?.progress ?? 0}<span class="text-lg text-surface-600-400">%</span
								></span
							>
						</div>
						{#if progressDelta7d != null}
							<div class="flex items-center gap-1 mt-2 text-xs font-medium">
								{#if progressDelta7d > 0}
									<i class="fa-solid fa-arrow-trend-up text-green-600"></i>
									<span class="text-green-600 tabular-nums">+{progressDelta7d}</span>
								{:else if progressDelta7d < 0}
									<i class="fa-solid fa-arrow-trend-down text-red-600"></i>
									<span class="text-red-600 tabular-nums">{progressDelta7d}</span>
								{:else}
									<i class="fa-solid fa-minus text-surface-500"></i>
									<span class="text-surface-600-400 tabular-nums">0</span>
								{/if}
								<span class="text-surface-500">{m.last7Days()}</span>
							</div>
						{/if}
					</div>
					<div
						class="relative rounded-lg bg-surface-50-950 border border-surface-200-800 p-4 overflow-hidden shadow-sm"
					>
						<div class="absolute top-0 inset-x-0 h-1 bg-blue-500"></div>
						<div
							class="text-[10px] font-semibold text-surface-600-400 uppercase tracking-wider mb-2"
						>
							{m.status()}
						</div>
						{#if latestSnapshot?.status}
							<span
								class="badge text-sm font-semibold px-3 py-1 rounded-full {statusColorMap[
									latestSnapshot.status
								] ?? 'bg-surface-100-900 text-surface-600-400'}"
							>
								{safeTranslate(latestSnapshot.status)}
							</span>
						{:else}
							<span class="text-surface-500 italic text-sm">—</span>
						{/if}
					</div>
					<div
						class="relative rounded-lg bg-surface-50-950 border border-surface-200-800 p-4 overflow-hidden shadow-sm"
					>
						<div
							class="absolute top-0 inset-x-0 h-1 {latestSnapshot?.health === 'green'
								? 'bg-green-500'
								: latestSnapshot?.health === 'amber'
									? 'bg-amber-500'
									: latestSnapshot?.health === 'red'
										? 'bg-red-500'
										: 'bg-surface-300-700'}"
						></div>
						<div
							class="text-[10px] font-semibold text-surface-600-400 uppercase tracking-wider mb-2"
						>
							{m.projectHealth()}
						</div>
						{#if latestSnapshot?.health}
							<span
								class="badge text-sm font-semibold px-3 py-1 rounded-full {healthColorMap[
									latestSnapshot.health
								] ?? 'bg-surface-100-900 text-surface-600-400'}"
							>
								{safeTranslate(latestSnapshot.health)}
							</span>
						{:else}
							<span class="text-surface-500 italic text-sm">—</span>
						{/if}
					</div>
					<div
						class="relative rounded-lg bg-surface-50-950 border border-surface-200-800 p-4 overflow-hidden shadow-sm"
					>
						<div class="absolute top-0 inset-x-0 h-1 bg-amber-500"></div>
						<div
							class="text-[10px] font-semibold text-surface-600-400 uppercase tracking-wider mb-2"
						>
							{m.actualCost()}
						</div>
						{#if latestSnapshot?.actual_cost != null}
							<div class="flex items-baseline gap-1">
								<span class="text-3xl font-bold text-surface-900-100 tabular-nums leading-none">
									{latestSnapshot.actual_cost}
								</span>
								{#if latestSnapshot.currency}
									<span class="text-sm text-surface-600-400">{latestSnapshot.currency}</span>
								{/if}
							</div>
							{#if latestSnapshot.budget}
								<div class="text-xs text-surface-600-400 mt-2 tabular-nums">
									of {latestSnapshot.budget}
									{latestSnapshot.currency ?? ''}
								</div>
							{/if}
						{:else}
							<span class="text-surface-500 italic text-sm">—</span>
						{/if}
					</div>
				</div>
				<div class="mb-6">
					<div class="text-xs font-semibold text-surface-600-400 uppercase tracking-wide mb-2">
						{m.lifecycle()} — {m.timeline()}
					</div>
					<div bind:this={lifecycleChartEl} style="width: 100%; height: 320px;"></div>
				</div>
				<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
					<div>
						<div class="text-xs font-semibold text-surface-600-400 uppercase tracking-wide mb-2">
							{m.progress()}
						</div>
						<div bind:this={progressChartEl} style="width: 100%; height: 240px;"></div>
					</div>
					<div>
						<div class="text-xs font-semibold text-surface-600-400 uppercase tracking-wide mb-2">
							{m.financials()}
						</div>
						<div bind:this={budgetChartEl} style="width: 100%; height: 240px;"></div>
					</div>
				</div>
			{/if}
		</Tabs.Content>
	</Tabs>
</div>
