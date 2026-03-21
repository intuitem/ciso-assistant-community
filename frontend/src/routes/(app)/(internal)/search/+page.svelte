<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';

	const MODEL_META: Record<string, { label: string; icon: string }> = {
		folders: { label: 'domains', icon: 'fa-solid fa-sitemap' },
		perimeters: { label: 'perimeters', icon: 'fa-solid fa-cubes' },
		threats: { label: 'threats', icon: 'fa-solid fa-biohazard' },
		'risk-matrices': { label: 'riskMatrices', icon: 'fa-solid fa-table-cells-large' },
		frameworks: { label: 'frameworks', icon: 'fa-solid fa-book' },
		'risk-assessments': { label: 'riskAssessments', icon: 'fa-solid fa-magnifying-glass-chart' },
		'compliance-assessments': {
			label: 'complianceAssessments',
			icon: 'fa-solid fa-clipboard-check'
		},
		'risk-scenarios': { label: 'riskScenarios', icon: 'fa-solid fa-clone' },
		assets: { label: 'assets', icon: 'fa-solid fa-gem' },
		'applied-controls': { label: 'appliedControls', icon: 'fa-solid fa-fire-extinguisher' },
		policies: { label: 'policies', icon: 'fa-solid fa-file-alt' },
		'reference-controls': { label: 'referenceControls', icon: 'fa-solid fa-gears' },
		evidences: { label: 'evidences', icon: 'fa-solid fa-file-circle-check' },
		'risk-acceptances': { label: 'riskAcceptances', icon: 'fa-solid fa-signature' },
		'security-exceptions': {
			label: 'securityExceptions',
			icon: 'fa-solid fa-circle-exclamation'
		},
		findings: { label: 'findings', icon: 'fa-solid fa-search' },
		incidents: { label: 'incidents', icon: 'fa-solid fa-bug' },
		entities: { label: 'entities', icon: 'fa-solid fa-building' },
		'ebios-rm': { label: 'ebiosRM', icon: 'fa-solid fa-gopuram' },
		'feared-events': { label: 'fearedEvents', icon: 'fa-solid fa-face-frown' },
		'strategic-scenarios': { label: 'strategicScenarios', icon: 'fa-solid fa-chess' },
		'attack-paths': { label: 'attackPaths', icon: 'fa-solid fa-route' }
	};

	interface SearchResult {
		type: string;
		id: string;
		name: string;
		ref_id: string;
		description: string;
		score: number;
		url: string;
	}

	let { data } = $props();

	let searchInput = $state(data.query);
	let activeTypeFilter = $state('');

	const results: SearchResult[] = $derived(data.results);
	const query = $derived(data.query);

	// Group results by type
	const groupedResults = $derived.by(() => {
		const filtered = activeTypeFilter
			? results.filter((r) => r.type === activeTypeFilter)
			: results;
		const groups: Record<string, SearchResult[]> = {};
		for (const r of filtered) {
			(groups[r.type] ??= []).push(r);
		}
		return groups;
	});

	// Unique types present in results (for filter chips)
	const availableTypes = $derived([...new Set(results.map((r) => r.type))]);

	function submitSearch() {
		const q = searchInput.trim();
		if (!q) return;
		goto(`/search?q=${encodeURIComponent(q)}`, { invalidateAll: true });
	}

	function toggleTypeFilter(type: string) {
		activeTypeFilter = activeTypeFilter === type ? '' : type;
	}

	function getModelLabel(type: string): string {
		const meta = MODEL_META[type];
		if (meta) return safeTranslate(meta.label);
		return type;
	}

	function getModelIcon(type: string): string {
		return MODEL_META[type]?.icon ?? 'fa-solid fa-circle';
	}
</script>

<div class="max-w-4xl mx-auto">
	<!-- Search bar -->
	<form onsubmit={(e) => { e.preventDefault(); submitSearch(); }} class="mb-6">
		<div class="flex items-center gap-3 rounded-xl bg-white shadow-sm ring-1 ring-gray-200 px-4 py-3">
			<i class="fa-solid fa-magnifying-glass text-gray-400"></i>
			<input
				type="text"
				bind:value={searchInput}
				placeholder={m.searchEllipsis()}
				class="flex-1 bg-transparent text-sm text-gray-900 placeholder-gray-400 outline-none border-none ring-0 focus:outline-none focus:ring-0"
			/>
			<button
				type="submit"
				class="rounded-lg bg-violet-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-violet-700 transition-colors cursor-pointer"
			>
				{m.search()}
			</button>
		</div>
	</form>

	{#if query}
		<!-- Results header -->
		<div class="flex items-center justify-between mb-4">
			<h2 class="text-lg font-semibold text-gray-900">
				{data.count}
				{data.count === 1 ? m.searchResult() : m.searchResults()}
				{m.searchFor()}
				<span class="text-violet-600">"{query}"</span>
			</h2>
		</div>

		<!-- Type filter chips -->
		{#if availableTypes.length > 1}
			<div class="flex flex-wrap gap-2 mb-5">
				<button
					class="rounded-full px-3 py-1 text-xs font-medium transition-colors cursor-pointer
						{activeTypeFilter === ''
						? 'bg-violet-100 text-violet-700 ring-1 ring-violet-300'
						: 'bg-gray-100 text-gray-600 hover:bg-gray-200'}"
					onclick={() => (activeTypeFilter = '')}
				>
					{m.all()}
				</button>
				{#each availableTypes as type}
					<button
						class="rounded-full px-3 py-1 text-xs font-medium transition-colors cursor-pointer flex items-center gap-1.5
							{activeTypeFilter === type
							? 'bg-violet-100 text-violet-700 ring-1 ring-violet-300'
							: 'bg-gray-100 text-gray-600 hover:bg-gray-200'}"
						onclick={() => toggleTypeFilter(type)}
					>
						<i class="{getModelIcon(type)} text-[10px]"></i>
						{getModelLabel(type)}
						<span class="text-[10px] opacity-60">
							({results.filter((r) => r.type === type).length})
						</span>
					</button>
				{/each}
			</div>
		{/if}

		<!-- Results grouped by type -->
		{#if Object.keys(groupedResults).length > 0}
			{#each Object.entries(groupedResults) as [type, items]}
				<div class="mb-6">
					<div class="flex items-center gap-2 mb-2 px-1">
						<i class="{getModelIcon(type)} text-xs text-gray-400"></i>
						<h3 class="text-xs font-semibold uppercase tracking-wider text-gray-400">
							{getModelLabel(type)}
						</h3>
					</div>
					<div class="space-y-1">
						{#each items as result}
							<a
								href={result.url}
								class="flex items-start gap-3 rounded-lg px-3 py-2.5 hover:bg-violet-50 transition-colors group"
							>
								<i
									class="{getModelIcon(result.type)} w-4 mt-0.5 text-center text-xs text-gray-400 group-hover:text-violet-500"
								></i>
								<div class="flex-1 min-w-0">
									<div class="flex items-center gap-2">
										<span
											class="text-sm font-medium text-gray-900 group-hover:text-violet-900 truncate"
										>
											{result.name}
										</span>
										{#if result.ref_id}
											<span
												class="shrink-0 rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-mono text-gray-500"
											>
												{result.ref_id}
											</span>
										{/if}
									</div>
									{#if result.description}
										<p class="text-xs text-gray-500 truncate mt-0.5">
											{result.description}
										</p>
									{/if}
								</div>
								<span class="shrink-0 text-[10px] text-gray-300 group-hover:text-violet-400 mt-1">
									↵
								</span>
							</a>
						{/each}
					</div>
				</div>
			{/each}
		{:else}
			<div class="flex flex-col items-center justify-center py-16 text-gray-400">
				<i class="fa-solid fa-magnifying-glass text-3xl mb-3"></i>
				<span class="text-sm">{m.commandPaletteNoResults()}</span>
			</div>
		{/if}
	{:else}
		<!-- Empty state -->
		<div class="flex flex-col items-center justify-center py-16 text-gray-400">
			<i class="fa-solid fa-magnifying-glass text-3xl mb-3"></i>
			<span class="text-sm">{m.searchPrompt()}</span>
		</div>
	{/if}
</div>
