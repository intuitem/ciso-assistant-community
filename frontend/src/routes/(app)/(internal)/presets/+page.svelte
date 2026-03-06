<script lang="ts">
	import type { PageData } from './$types';
	import { m } from '$paraglide/messages';
	import { getModalStore } from '$lib/components/Modals/stores';
	import ApplyPresetModal from '$lib/components/Modals/ApplyPresetModal.svelte';

	let { data }: { data: PageData } = $props();

	const modalStore = getModalStore();

	// --- Filter state ---
	let activeFilter: string = $state('all');

	// Collect all unique region tags across presets
	const allRegions: string[] = $derived(
		[...new Set(data.presets.flatMap((p: any) => p.profile?.region ?? []))].sort()
	);

	const filteredPresets = $derived(
		activeFilter === 'all'
			? data.presets
			: data.presets.filter((p: any) => (p.profile?.region ?? []).includes(activeFilter))
	);

	let presetsCollapsed = $state(false);

	// --- Expanded preset detail ---
	let expandedPresetId: string | null = $state(null);

	function toggleExpand(id: string) {
		expandedPresetId = expandedPresetId === id ? null : id;
	}

	// --- Apply logic ---
	function applyPreset(presetId: string, presetName: string) {
		modalStore.trigger({
			type: 'component',
			title: m.applyPreset(),
			body: m.applyPresetConfirm(),
			component: {
				ref: ApplyPresetModal,
				props: {
					presetName,
					domains: data.domains,
					onApply: async (payload: {
						folder_name?: string;
						folder_id?: string;
						create_objects?: boolean;
					}) => {
						try {
							const response = await fetch(`/presets/apply`, {
								method: 'POST',
								headers: { 'Content-Type': 'application/json' },
								body: JSON.stringify({
									preset_id: presetId,
									...payload
								})
							});
							if (response.ok) {
								const result = await response.json();
								window.location.href = `/preset-journeys/${result.journey_id}`;
								return { ok: true };
							}
							const err = await response.json().catch(() => ({}));
							const raw = err.error ?? err;
							let message: string;
							if (typeof raw === 'string') {
								message = raw;
							} else if (typeof raw === 'object') {
								message = Object.values(raw).flat().join(', ');
							} else {
								message = String(raw);
							}
							return { ok: false, error: message };
						} catch (e) {
							console.error('Failed to apply preset', e);
							return { ok: false, error: String(e) };
						}
					}
				}
			}
		});
	}

	// --- Helpers ---
	function getProfileTags(profile: Record<string, any> | null): string[] {
		if (!profile) return [];
		const tags: string[] = [];
		for (const [, value] of Object.entries(profile)) {
			if (Array.isArray(value)) {
				tags.push(...value);
			} else if (typeof value === 'string') {
				tags.push(value);
			}
		}
		return tags;
	}

	const REGION_FLAGS: Record<string, string> = {
		fr: '\u{1F1EB}\u{1F1F7}',
		eu: '\u{1F1EA}\u{1F1FA}',
		be: '\u{1F1E7}\u{1F1EA}',
		us: '\u{1F1FA}\u{1F1F8}',
		global: '\u{1F310}'
	};

	const OBJECT_TYPE_META: Record<string, { label: () => string; icon: string }> = {
		risk_assessment: { label: () => m.riskAssessment(), icon: 'fa-chart-line' },
		compliance_assessment: { label: () => m.complianceAssessment(), icon: 'fa-list-check' },
		ebios_rm_study: { label: () => m.ebiosRmStudy(), icon: 'fa-shield-halved' },
		task_template: { label: () => m.taskTemplate(), icon: 'fa-calendar-check' },
		organisation_objective: { label: () => m.organisationObjective(), icon: 'fa-bullseye' },
		organisation_issue: { label: () => m.organisationIssue(), icon: 'fa-triangle-exclamation' },
		perimeter: { label: () => m.perimeter(), icon: 'fa-draw-polygon' },
		processing: { label: () => m.processing(), icon: 'fa-gears' },
		entity: { label: () => m.entity(), icon: 'fa-building' },
		findings_assessment: { label: () => m.findingsAssessment(), icon: 'fa-binoculars' },
		asset: { label: () => m.asset(), icon: 'fa-gem' },
		risk_scenario: { label: () => m.riskScenario(), icon: 'fa-biohazard' }
	};

	function getProgressPercent(journey: any): number {
		const steps = journey.steps || [];
		if (steps.length === 0) return 0;
		const completed = steps.filter(
			(s: any) => s.status === 'done' || s.status === 'skipped'
		).length;
		return Math.round((completed / steps.length) * 100);
	}

	function getStepCounts(journey: any): { completed: number; total: number } {
		const steps = journey.steps || [];
		const completed = steps.filter(
			(s: any) => s.status === 'done' || s.status === 'skipped'
		).length;
		return { completed, total: steps.length };
	}

	function hasUpgrade(journey: any): boolean {
		return journey.latest_version && journey.latest_version > journey.version;
	}
</script>

<div class="flex flex-col gap-8 p-2">
	<!-- ═══════════════ ACTIVE JOURNEYS ═══════════════ -->
	<section>
		<div class="flex items-center gap-3 mb-4">
			<div class="flex items-center justify-center w-8 h-8 rounded-lg bg-indigo-100">
				<i class="fa-solid fa-route text-indigo-600 text-sm"></i>
			</div>
			<h2 class="text-lg font-semibold text-gray-800">{m.activeJourneys()}</h2>
			{#if data.journeys.length > 0}
				<span
					class="ml-1 inline-flex items-center justify-center w-5 h-5 rounded-full bg-indigo-100 text-xs font-semibold text-indigo-700"
				>
					{data.journeys.length}
				</span>
			{/if}
		</div>

		{#if data.journeys.length === 0}
			<div
				class="relative overflow-hidden rounded-xl border border-dashed border-gray-300 bg-white/60 p-10 text-center"
			>
				<div class="relative z-10 flex flex-col items-center gap-2">
					<i class="fa-solid fa-route text-3xl text-gray-300"></i>
					<p class="text-sm text-gray-400">{m.noActiveJourneys()}</p>
				</div>
			</div>
		{:else}
			<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
				{#each data.journeys as journey}
					{@const progress = getProgressPercent(journey)}
					{@const counts = getStepCounts(journey)}
					<a
						href="/preset-journeys/{journey.id}"
						class="group relative flex flex-col rounded-xl border border-gray-200 bg-white p-5 shadow-sm
							hover:shadow-md hover:border-indigo-200 transition-all duration-200"
					>
						<!-- Progress accent bar at top -->
						<div class="absolute top-0 left-0 right-0 h-1 rounded-t-xl bg-gray-100 overflow-hidden">
							<div
								class="h-full rounded-t-xl transition-all duration-500 ease-out"
								class:bg-indigo-500={progress < 100}
								class:bg-emerald-500={progress === 100}
								style="width: {progress}%"
							></div>
						</div>

						<div class="flex items-start justify-between gap-3 mt-1">
							<div class="flex-1 min-w-0">
								<div class="flex items-center gap-2 mb-1">
									<h3
										class="font-semibold text-gray-800 truncate group-hover:text-indigo-700 transition-colors"
									>
										{journey.name}
									</h3>
									{#if hasUpgrade(journey)}
										<span
											class="inline-flex items-center gap-1 rounded-full bg-amber-50 border border-amber-200 px-2 py-0.5 text-[11px] font-medium text-amber-700"
										>
											<i class="fa-solid fa-arrow-up text-[9px]"></i>
											{m.upgradeAvailable()}
										</span>
									{/if}
								</div>
								{#if journey.folder?.str}
									<span class="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 border border-indigo-100 px-2.5 py-0.5 text-[11px] font-medium text-indigo-600 mb-0.5 max-w-fit">
										<i class="fa-solid fa-sitemap text-[9px]"></i>
										<span class="truncate">{journey.folder.str}</span>
									</span>
								{/if}
								{#if journey.description}
									<p class="text-sm text-gray-400 line-clamp-1">{journey.description}</p>
								{/if}
							</div>

							<!-- Progress ring -->
							<div class="shrink-0 flex flex-col items-center">
								<div class="relative w-12 h-12">
									<svg class="w-12 h-12 -rotate-90" viewBox="0 0 48 48">
										<circle
											cx="24"
											cy="24"
											r="20"
											fill="none"
											stroke-width="3"
											class="stroke-gray-100"
										/>
										<circle
											cx="24"
											cy="24"
											r="20"
											fill="none"
											stroke-width="3"
											stroke-linecap="round"
											class:stroke-indigo-500={progress < 100}
											class:stroke-emerald-500={progress === 100}
											stroke-dasharray="{(progress / 100) * 125.6} 125.6"
											style="transition: stroke-dasharray 0.5s ease-out"
										/>
									</svg>
									<span
										class="absolute inset-0 flex items-center justify-center text-xs font-bold"
										class:text-indigo-600={progress < 100}
										class:text-emerald-600={progress === 100}
									>
										{progress}%
									</span>
								</div>
							</div>
						</div>

						<!-- Step summary -->
						<div class="flex items-center justify-between mt-3 pt-3 border-t border-gray-100">
							<span class="text-xs text-gray-400">
								{m.stepsCompleted({
									completed: String(counts.completed),
									total: String(counts.total)
								})}
							</span>
							<span
								class="inline-flex items-center gap-1 text-xs font-medium text-indigo-500 group-hover:text-indigo-600 transition-colors"
							>
								{m.continueJourney()}
								<i
									class="fa-solid fa-arrow-right text-[10px] group-hover:translate-x-0.5 transition-transform"
								></i>
							</span>
						</div>
					</a>
				{/each}
			</div>
		{/if}
	</section>

	<!-- ═══════════════ AVAILABLE PRESETS ═══════════════ -->
	<section>
		<div class="flex items-center justify-between mb-4">
			<button
				class="flex items-center gap-3 cursor-pointer"
				onclick={() => (presetsCollapsed = !presetsCollapsed)}
			>
				<div class="flex items-center justify-center w-8 h-8 rounded-lg bg-violet-100">
					<i class="fa-solid fa-box-open text-violet-600 text-sm"></i>
				</div>
				<h2 class="text-lg font-semibold text-gray-800">{m.availablePresets()}</h2>
				<i
					class="fa-solid fa-chevron-down text-xs text-gray-400 transition-transform duration-200 {presetsCollapsed
						? '-rotate-90'
						: ''}"
				></i>
			</button>

			<!-- Region filter pills -->
			{#if allRegions.length > 1}
				<div class="flex items-center gap-1.5">
					<button
						class="px-3 py-1 rounded-full text-xs font-medium transition-all duration-150 cursor-pointer
							{activeFilter === 'all'
							? 'bg-gray-800 text-white shadow-sm'
							: 'bg-white text-gray-500 border border-gray-200 hover:border-gray-300 hover:text-gray-700'}"
						onclick={() => (activeFilter = 'all')}
					>
						{m.showAll()}
					</button>
					{#each allRegions as region}
						<button
							class="px-3 py-1 rounded-full text-xs font-medium transition-all duration-150 cursor-pointer
								{activeFilter === region
								? 'bg-gray-800 text-white shadow-sm'
								: 'bg-white text-gray-500 border border-gray-200 hover:border-gray-300 hover:text-gray-700'}"
							onclick={() => (activeFilter = region)}
						>
							{REGION_FLAGS[region] ?? ''}
							{region.toUpperCase()}
						</button>
					{/each}
				</div>
			{/if}
		</div>

		{#if !presetsCollapsed}
			{#if data.presets.length === 0}
				<div
					class="flex flex-col items-center justify-center rounded-xl border border-dashed border-gray-300 bg-white/60 p-10 text-center"
				>
					<i class="fa-solid fa-box-open text-3xl text-gray-300 mb-2"></i>
					<p class="text-sm text-gray-400">{m.noPresetsAvailable()}</p>
				</div>
			{:else}
				<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
					{#each filteredPresets as preset (preset.id)}
						{@const isExpanded = expandedPresetId === preset.id}
						<div
							class="group flex flex-col rounded-xl border bg-white shadow-sm transition-all duration-200
							{isExpanded
								? 'border-violet-300 shadow-md ring-1 ring-violet-100'
								: 'border-gray-200 hover:shadow-md hover:border-gray-300'}"
						>
							<!-- Card header — always visible -->
							<button
								class="flex items-start gap-3 p-4 pb-3 text-left w-full cursor-pointer"
								onclick={() => toggleExpand(preset.id)}
							>
								<div class="flex-1 min-w-0">
									<h3 class="font-semibold text-[15px] text-gray-800 leading-tight">
										{preset.name}
									</h3>
									{#if preset.description}
										<p class="text-sm text-gray-400 mt-1" class:line-clamp-2={!isExpanded}>
											{preset.description}
										</p>
									{/if}
								</div>
								<i
									class="fa-solid fa-chevron-down text-[10px] text-gray-300 mt-1.5 transition-transform duration-200
									{isExpanded ? 'rotate-180' : ''}"
								></i>
							</button>

							<!-- Tags — always visible -->
							{#if preset.profile}
								<div class="flex flex-wrap gap-1 px-4 pb-3">
									{#each getProfileTags(preset.profile) as tag}
										{@const flag = REGION_FLAGS[tag]}
										<span
											class="inline-flex items-center gap-1 rounded-full bg-gray-50 border border-gray-100 px-2 py-0.5 text-[11px] text-gray-500"
										>
											{#if flag}{flag}{/if}
											{tag}
										</span>
									{/each}
								</div>
							{/if}

							<!-- Expanded detail -->
							{#if isExpanded && preset.scaffolded_objects?.length}
								<div class="px-4 pb-3 border-t border-gray-100 pt-3">
									<div class="grid grid-cols-2 gap-x-4 gap-y-1.5">
										{#each preset.scaffolded_objects as obj}
											{@const meta = OBJECT_TYPE_META[obj.type]}
											{#if meta}
												<div class="flex items-center gap-1.5 text-xs text-gray-500">
													<i class="fa-solid {meta.icon} w-3.5 text-center text-gray-400"></i>
													<span
														>{obj.count}
														{meta.label()}{obj.count > 1 ? 's' : ''}</span
													>
												</div>
											{/if}
										{/each}
									</div>
								</div>
							{/if}

							<!-- Apply button -->
							<div class="px-4 pb-4 mt-auto">
								<button
									type="button"
									class="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-sm font-medium
									transition-all duration-150 cursor-pointer
									bg-violet-600 text-white hover:bg-violet-700 active:bg-violet-800 shadow-sm"
									onclick={() => applyPreset(preset.id, preset.name)}
								>
									<i class="fa-solid fa-play text-[10px]"></i>
									{m.applyPreset()}
								</button>
							</div>
						</div>
					{/each}
				</div>

				{#if filteredPresets.length === 0}
					<div class="flex flex-col items-center py-10 text-gray-400">
						<i class="fa-solid fa-filter-circle-xmark text-2xl mb-2"></i>
						<p class="text-sm">{m.noMatchingPresets()}</p>
					</div>
				{/if}
			{/if}
		{/if}
	</section>
</div>
