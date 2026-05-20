<script lang="ts">
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import { Tabs, Progress } from '@skeletonlabs/skeleton-svelte';
	import { invalidateAll } from '$app/navigation';
	import { page } from '$app/state';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
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
		currency: '',
		tolerances: {}
	});

	function startScheduleEdit() {
		scheduleDraft = {
			start_date: project.start_date ?? null,
			end_date: project.end_date ?? null,
			eta: project.eta ?? null,
			budget: project.budget ?? null,
			currency: project.currency ?? '',
			tolerances: structuredClone(project.tolerances ?? {})
		};
		scheduleEditing = true;
	}

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

	let progressValue = $derived(project.progress ?? 0);
</script>

<div class="card bg-white shadow-sm m-4">
	<!-- Header bar -->
	<div class="p-6 border-b border-gray-200">
		<div class="flex items-start justify-between gap-4 flex-wrap">
			<div class="min-w-0">
				<div class="flex items-baseline gap-3">
					<h1 class="text-2xl font-semibold text-gray-900 truncate">{project.name}</h1>
					{#if project.ref_id}
						<span class="text-sm text-gray-500">{project.ref_id}</span>
					{/if}
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
			</div>
		</div>

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
			<Tabs.Trigger value="overview" class="px-4 py-3 text-sm font-medium">
				<i class="fa-solid fa-chart-pie mr-2"></i>{m.overview()}
			</Tabs.Trigger>
			<Tabs.Trigger value="charter" class="px-4 py-3 text-sm font-medium">
				<i class="fa-solid fa-file-contract mr-2"></i>{m.charter()}
			</Tabs.Trigger>
			<Tabs.Trigger value="schedule" class="px-4 py-3 text-sm font-medium">
				<i class="fa-solid fa-calendar mr-2"></i>{m.schedule()}
			</Tabs.Trigger>
			<Tabs.Trigger value="scope" class="px-4 py-3 text-sm font-medium">
				<i class="fa-solid fa-bullseye mr-2"></i>{m.scope()}
			</Tabs.Trigger>
			<Tabs.Trigger value="linked" class="px-4 py-3 text-sm font-medium">
				<i class="fa-solid fa-link mr-2"></i>{m.linked()}
			</Tabs.Trigger>
			<Tabs.Trigger value="people" class="px-4 py-3 text-sm font-medium">
				<i class="fa-solid fa-people-arrows mr-2"></i>{m.people()}
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
							<textarea
								bind:value={charterDraft[section.key]}
								class="textarea w-full"
								rows="4"
								placeholder={section.label}
							></textarea>
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
				<div>
					<label for="sc-budget" class="text-xs font-semibold text-gray-500 uppercase mb-1 block">
						{m.budget()}
					</label>
					{#if scheduleEditing}
						<input
							id="sc-budget"
							type="number"
							step="0.01"
							bind:value={scheduleDraft.budget}
							class="input w-full"
						/>
					{:else}
						<span class="text-sm text-gray-900">{project.budget ?? '--'}</span>
					{/if}
				</div>
				<div>
					<label for="sc-currency" class="text-xs font-semibold text-gray-500 uppercase mb-1 block">
						{m.currency()}
					</label>
					{#if scheduleEditing}
						<input
							id="sc-currency"
							type="text"
							maxlength="3"
							bind:value={scheduleDraft.currency}
							class="input w-full"
						/>
					{:else}
						<span class="text-sm text-gray-900">{project.currency || '--'}</span>
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
		<Tabs.Content value="scope" class="p-6">
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
							<textarea
								bind:value={scopeDraft[section.key]}
								class="textarea w-full"
								rows="4"
								placeholder={section.label}
							></textarea>
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
	</Tabs>
</div>
