<script lang="ts">
	import { goto } from '$app/navigation';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';

	const MODEL_META: Record<string, { label: string; icon: string; color: string }> = {
		folders: { label: 'domains', icon: 'fa-solid fa-sitemap', color: '#6366f1' },
		perimeters: { label: 'perimeters', icon: 'fa-solid fa-cubes', color: '#8b5cf6' },
		threats: { label: 'threats', icon: 'fa-solid fa-biohazard', color: '#ef4444' },
		'risk-matrices': {
			label: 'riskMatrices',
			icon: 'fa-solid fa-table-cells-large',
			color: '#f59e0b'
		},
		frameworks: { label: 'frameworks', icon: 'fa-solid fa-book', color: '#3b82f6' },
		'risk-assessments': {
			label: 'riskAssessments',
			icon: 'fa-solid fa-magnifying-glass-chart',
			color: '#ec4899'
		},
		'compliance-assessments': {
			label: 'complianceAssessments',
			icon: 'fa-solid fa-clipboard-check',
			color: '#10b981'
		},
		'risk-scenarios': { label: 'riskScenarios', icon: 'fa-solid fa-clone', color: '#f97316' },
		assets: { label: 'assets', icon: 'fa-solid fa-gem', color: '#06b6d4' },
		'applied-controls': {
			label: 'appliedControls',
			icon: 'fa-solid fa-fire-extinguisher',
			color: '#14b8a6'
		},
		policies: { label: 'policies', icon: 'fa-solid fa-file-alt', color: '#6366f1' },
		'reference-controls': {
			label: 'referenceControls',
			icon: 'fa-solid fa-gears',
			color: '#64748b'
		},
		evidences: { label: 'evidences', icon: 'fa-solid fa-file-circle-check', color: '#22c55e' },
		'risk-acceptances': {
			label: 'riskAcceptances',
			icon: 'fa-solid fa-signature',
			color: '#a855f7'
		},
		'security-exceptions': {
			label: 'securityExceptions',
			icon: 'fa-solid fa-circle-exclamation',
			color: '#eab308'
		},
		findings: { label: 'findings', icon: 'fa-solid fa-search', color: '#f43f5e' },
		incidents: { label: 'incidents', icon: 'fa-solid fa-bug', color: '#dc2626' },
		entities: { label: 'entities', icon: 'fa-solid fa-building', color: '#0ea5e9' },
		'ebios-rm': { label: 'ebiosRM', icon: 'fa-solid fa-gopuram', color: '#d946ef' },
		'feared-events': { label: 'fearedEvents', icon: 'fa-solid fa-face-frown', color: '#f87171' },
		'strategic-scenarios': {
			label: 'strategicScenarios',
			icon: 'fa-solid fa-chess',
			color: '#7c3aed'
		},
		'attack-paths': { label: 'attackPaths', icon: 'fa-solid fa-route', color: '#e11d48' }
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

	// Sync searchInput when data changes (e.g. new search from command palette)
	$effect(() => {
		searchInput = data.query;
		activeTypeFilter = '';
	});

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

	function getModelColor(type: string): string {
		return MODEL_META[type]?.color ?? '#94a3b8';
	}

	function getScoreOpacity(score: number): number {
		return Math.max(0.3, score / 100);
	}
</script>

<div class="search-page max-w-4xl mx-auto">
	<!-- Search bar -->
	<form
		onsubmit={(e) => {
			e.preventDefault();
			submitSearch();
		}}
		class="search-bar-wrapper mb-8"
	>
		<div class="search-bar">
			<div class="search-icon-wrapper">
				<i class="fa-solid fa-magnifying-glass"></i>
			</div>
			<input
				type="text"
				bind:value={searchInput}
				placeholder={m.searchEllipsis()}
				class="search-input"
			/>
			<button type="submit" class="search-submit">
				{m.search()}
				<i class="fa-solid fa-arrow-right text-[10px] ml-1.5 opacity-70"></i>
			</button>
		</div>
	</form>

	{#if query}
		<!-- Results header -->
		<div class="results-header" style="--stagger: 0">
			<div class="results-count">
				<span class="count-number">{data.count}</span>
				<span class="count-label">
					{data.count === 1 ? m.searchResult() : m.searchResults()}
					{m.searchFor()}
				</span>
				<span class="count-query">"{query}"</span>
			</div>
		</div>

		<!-- Type filter chips -->
		{#if availableTypes.length > 1}
			<div class="filter-chips" style="--stagger: 1">
				<button
					class="filter-chip"
					class:active={activeTypeFilter === ''}
					onclick={() => (activeTypeFilter = '')}
				>
					<span class="chip-dot" style="background: linear-gradient(135deg, #8b5cf6, #ec4899)"
					></span>
					{m.all()}
				</button>
				{#each availableTypes as type}
					<button
						class="filter-chip"
						class:active={activeTypeFilter === type}
						onclick={() => toggleTypeFilter(type)}
					>
						<span class="chip-dot" style="background: {getModelColor(type)}"></span>
						{getModelLabel(type)}
						<span class="chip-count">
							{results.filter((r) => r.type === type).length}
						</span>
					</button>
				{/each}
			</div>
		{/if}

		<!-- Results grouped by type -->
		{#if Object.keys(groupedResults).length > 0}
			{#each Object.entries(groupedResults) as [type, items], groupIndex}
				<div class="result-group" style="--stagger: {groupIndex + 2}">
					<div class="group-header">
						<div class="group-accent" style="background: {getModelColor(type)}"></div>
						<i class="{getModelIcon(type)} group-icon" style="color: {getModelColor(type)}"></i>
						<h3 class="group-title">{getModelLabel(type)}</h3>
						<span class="group-count">{items.length}</span>
					</div>
					<div class="group-items">
						{#each items as result, resultIndex}
							<a
								href={result.url}
								class="result-item"
								style="--item-delay: {resultIndex * 30}ms; --accent: {getModelColor(result.type)}"
							>
								<div class="result-score-bar">
									<div
										class="score-fill"
										style="height: {result.score}%; opacity: {getScoreOpacity(result.score)}"
									></div>
								</div>
								<div class="result-body">
									<div class="result-top-row">
										<span class="result-name">{result.name}</span>
										{#if result.ref_id}
											<span class="result-ref">{result.ref_id}</span>
										{/if}
									</div>
									{#if result.description}
										<p class="result-description">{result.description}</p>
									{/if}
								</div>
								<div class="result-arrow">
									<i class="fa-solid fa-arrow-right"></i>
								</div>
							</a>
						{/each}
					</div>
				</div>
			{/each}
		{:else}
			<div class="empty-state" style="--stagger: 2">
				<div class="empty-icon">
					<i class="fa-solid fa-magnifying-glass"></i>
				</div>
				<span class="empty-text">{m.commandPaletteNoResults()}</span>
			</div>
		{/if}
	{:else}
		<!-- Empty state -->
		<div class="empty-state" style="--stagger: 1">
			<div class="empty-icon">
				<i class="fa-solid fa-magnifying-glass"></i>
			</div>
			<span class="empty-text">{m.searchPrompt()}</span>
			<div class="empty-hint">
				<kbd>{navigator?.platform?.toUpperCase().indexOf('MAC') >= 0 ? '⌘' : 'Ctrl'}</kbd>
				<span>+</span>
				<kbd>K</kbd>
			</div>
		</div>
	{/if}
</div>

<style>
	/* ---- Search bar ---- */
	.search-bar-wrapper {
		animation: slideDown 0.4s cubic-bezier(0.16, 1, 0.3, 1) both;
	}

	.search-bar {
		display: flex;
		align-items: center;
		gap: 0;
		background: white;
		border-radius: 14px;
		box-shadow:
			0 1px 3px rgba(0, 0, 0, 0.06),
			0 0 0 1px rgba(0, 0, 0, 0.04);
		overflow: hidden;
		transition: box-shadow 0.2s ease;
	}

	.search-bar:focus-within {
		box-shadow:
			0 4px 20px rgba(139, 92, 246, 0.1),
			0 0 0 2px rgba(139, 92, 246, 0.15);
	}

	.search-icon-wrapper {
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 0 0 0 16px;
		color: #a78bfa;
		font-size: 14px;
	}

	.search-input {
		flex: 1;
		padding: 14px 12px;
		font-size: 14px;
		color: #1e1b4b;
		background: transparent;
		border: none !important;
		outline: none !important;
		box-shadow: none !important;
		ring: none;
		font-weight: 450;
		letter-spacing: -0.01em;
	}

	.search-input:focus {
		border: none !important;
		outline: none !important;
		box-shadow: none !important;
	}

	.search-input::placeholder {
		color: #c4b5fd;
		font-weight: 400;
	}

	.search-submit {
		display: flex;
		align-items: center;
		margin: 6px 6px 6px 0;
		padding: 8px 18px;
		border-radius: 10px;
		font-size: 13px;
		font-weight: 600;
		color: white;
		background: linear-gradient(135deg, #7c3aed, #a855f7);
		border: none;
		cursor: pointer;
		transition: all 0.15s ease;
		letter-spacing: 0.01em;
	}

	.search-submit:hover {
		background: linear-gradient(135deg, #6d28d9, #9333ea);
		transform: translateY(-1px);
		box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3);
	}

	/* ---- Results header ---- */
	.results-header {
		margin-bottom: 20px;
		animation: fadeUp 0.35s cubic-bezier(0.16, 1, 0.3, 1) both;
		animation-delay: calc(var(--stagger) * 60ms + 100ms);
	}

	.results-count {
		display: flex;
		align-items: baseline;
		gap: 6px;
		flex-wrap: wrap;
	}

	.count-number {
		font-size: 28px;
		font-weight: 700;
		background: linear-gradient(135deg, #ec4899, #8b5cf6);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		background-clip: text;
		line-height: 1;
		letter-spacing: -0.03em;
	}

	.count-label {
		font-size: 14px;
		color: #64748b;
		font-weight: 450;
	}

	.count-query {
		font-size: 14px;
		font-weight: 600;
		color: #7c3aed;
	}

	/* ---- Filter chips ---- */
	.filter-chips {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
		margin-bottom: 24px;
		animation: fadeUp 0.35s cubic-bezier(0.16, 1, 0.3, 1) both;
		animation-delay: calc(var(--stagger) * 60ms + 100ms);
	}

	.filter-chip {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 5px 12px;
		border-radius: 100px;
		font-size: 12px;
		font-weight: 500;
		color: #64748b;
		background: white;
		border: 1px solid #e2e8f0;
		cursor: pointer;
		transition: all 0.15s ease;
	}

	.filter-chip:hover {
		border-color: #c4b5fd;
		color: #6d28d9;
		background: #faf5ff;
	}

	.filter-chip.active {
		background: #7c3aed;
		color: white;
		border-color: #7c3aed;
		box-shadow: 0 2px 8px rgba(124, 58, 237, 0.25);
	}

	.filter-chip.active .chip-dot {
		background: white !important;
	}

	.filter-chip.active .chip-count {
		background: rgba(255, 255, 255, 0.2);
		color: white;
	}

	.chip-dot {
		width: 7px;
		height: 7px;
		border-radius: 50%;
		flex-shrink: 0;
	}

	.chip-count {
		font-size: 10px;
		font-weight: 600;
		color: #94a3b8;
		background: #f1f5f9;
		padding: 1px 6px;
		border-radius: 100px;
		min-width: 18px;
		text-align: center;
	}

	/* ---- Result groups ---- */
	.result-group {
		margin-bottom: 28px;
		animation: fadeUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) both;
		animation-delay: calc(var(--stagger) * 60ms + 100ms);
	}

	.group-header {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 0 2px;
		margin-bottom: 8px;
	}

	.group-accent {
		width: 3px;
		height: 14px;
		border-radius: 3px;
	}

	.group-icon {
		font-size: 11px;
	}

	.group-title {
		font-size: 11px;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: #475569;
	}

	.group-count {
		font-size: 10px;
		font-weight: 600;
		color: #94a3b8;
		background: #f1f5f9;
		padding: 1px 7px;
		border-radius: 100px;
	}

	/* ---- Result items ---- */
	.group-items {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.result-item {
		display: flex;
		align-items: stretch;
		gap: 0;
		padding: 0;
		border-radius: 10px;
		background: white;
		border: 1px solid transparent;
		transition: all 0.15s ease;
		overflow: hidden;
		text-decoration: none;
		animation: fadeUp 0.3s cubic-bezier(0.16, 1, 0.3, 1) both;
		animation-delay: var(--item-delay);
	}

	.result-item:hover {
		border-color: color-mix(in srgb, var(--accent) 25%, transparent);
		box-shadow:
			0 2px 12px color-mix(in srgb, var(--accent) 8%, transparent),
			0 0 0 1px color-mix(in srgb, var(--accent) 10%, transparent);
		transform: translateX(3px);
	}

	.result-score-bar {
		width: 3px;
		min-height: 100%;
		background: #f1f5f9;
		display: flex;
		flex-direction: column;
		justify-content: flex-end;
		flex-shrink: 0;
		border-radius: 3px 0 0 3px;
		overflow: hidden;
	}

	.score-fill {
		width: 100%;
		background: var(--accent);
		border-radius: 3px;
		transition: height 0.5s cubic-bezier(0.16, 1, 0.3, 1);
	}

	.result-body {
		flex: 1;
		min-width: 0;
		padding: 10px 12px;
	}

	.result-top-row {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.result-name {
		font-size: 13.5px;
		font-weight: 550;
		color: #1e293b;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		letter-spacing: -0.01em;
	}

	.result-item:hover .result-name {
		color: var(--accent);
	}

	.result-ref {
		flex-shrink: 0;
		font-size: 10px;
		font-family: ui-monospace, 'SF Mono', 'Cascadia Code', Menlo, monospace;
		font-weight: 500;
		color: #94a3b8;
		background: #f8fafc;
		padding: 2px 7px;
		border-radius: 5px;
		border: 1px solid #e2e8f0;
		letter-spacing: 0.02em;
	}

	.result-description {
		font-size: 12px;
		color: #94a3b8;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		margin-top: 2px;
		line-height: 1.4;
	}

	.result-arrow {
		display: flex;
		align-items: center;
		padding: 0 14px;
		color: #cbd5e1;
		font-size: 11px;
		opacity: 0;
		transform: translateX(-4px);
		transition: all 0.15s ease;
	}

	.result-item:hover .result-arrow {
		opacity: 1;
		transform: translateX(0);
		color: var(--accent);
	}

	/* ---- Empty state ---- */
	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 64px 0;
		animation: fadeUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) both;
		animation-delay: calc(var(--stagger) * 60ms + 100ms);
	}

	.empty-icon {
		width: 56px;
		height: 56px;
		border-radius: 16px;
		background: white;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 20px;
		color: #c4b5fd;
		margin-bottom: 16px;
		box-shadow:
			0 1px 3px rgba(0, 0, 0, 0.04),
			0 0 0 1px rgba(0, 0, 0, 0.03);
	}

	.empty-text {
		font-size: 14px;
		color: #94a3b8;
		font-weight: 450;
	}

	.empty-hint {
		display: flex;
		align-items: center;
		gap: 4px;
		margin-top: 12px;
		color: #cbd5e1;
		font-size: 12px;
	}

	.empty-hint kbd {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		padding: 2px 7px;
		border-radius: 5px;
		background: white;
		border: 1px solid #e2e8f0;
		font-family: ui-monospace, 'SF Mono', 'Cascadia Code', Menlo, monospace;
		font-size: 11px;
		font-weight: 500;
		color: #94a3b8;
		box-shadow: 0 1px 0 #e2e8f0;
	}

	/* ---- Animations ---- */
	@keyframes slideDown {
		from {
			opacity: 0;
			transform: translateY(-12px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	@keyframes fadeUp {
		from {
			opacity: 0;
			transform: translateY(8px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}
</style>
