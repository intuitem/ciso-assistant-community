<script lang="ts">
	import FlippableCard from './FlippableCard.svelte';
	import VendorPosture from './VendorPosture.svelte';
	import TierBadge from '#lib/components/ModelTable/field/TierBadge.svelte';
	import type { PageData } from './$types';
	import { safeTranslate } from '#lib/utils/i18n.js';
	import { m } from '#paraglide/messages.js';
	import { Tabs } from '@skeletonlabs/skeleton-svelte';
	import { page } from '$app/state';
	import { replaceState } from '$app/navigation';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const NO_TIER = 'none';

	// Kept in the URL so a reload or a shared link opens the same tab.
	let tab = $derived(
		page.url.searchParams.get('tab') === 'assessments' ? 'assessments' : 'posture'
	);
	function setTab(value: string) {
		tab = value;
		const url = new URL(page.url.href);
		url.searchParams.set('tab', value);
		replaceState(url, {});
	}

	const assessments = $derived((data.data ?? []) as any[]);
	const tiers = $derived((data.tiers ?? []) as any[]);

	// Toggled tiers (ids, or NO_TIER); none toggled shows every card.
	let selectedTiers = $state<string[]>([]);
	let query = $state('');

	const fold = (text: string) => (text ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

	const tierOf = (assessment: any) => assessment.tier?.id ?? NO_TIER;

	const visible = $derived(
		assessments.filter((assessment) => {
			if (selectedTiers.length && !selectedTiers.includes(tierOf(assessment))) return false;
			const needle = fold(query.trim());
			return (
				!needle ||
				fold(assessment.provider).includes(needle) ||
				fold(assessment.folder_name).includes(needle)
			);
		})
	);

	// Vendors behind the cards, per tier: the pills count what they filter.
	const vendorsPerTier = $derived(
		assessments.reduce((counts: Record<string, Set<string>>, assessment) => {
			(counts[tierOf(assessment)] ??= new Set()).add(assessment.entity_id);
			return counts;
		}, {})
	);
	const pills = $derived([
		// A hidden tier only while some vendor still has it.
		...tiers
			.filter((tier) => tier.is_visible || vendorsPerTier[tier.id]?.size)
			.map((tier) => ({
				key: tier.id,
				tier,
				count: vendorsPerTier[tier.id]?.size ?? 0
			})),
		{ key: NO_TIER, tier: null, count: vendorsPerTier[NO_TIER]?.size ?? 0 }
	]);

	// One key for every card's compliance bar, limited to the statuses on screen.
	const complianceLegend = $derived.by(() => {
		const statuses = new Map<string, { localName: string; color: string }>();
		for (const assessment of visible) {
			const overview = assessment.compliance_overview;
			if (!overview?.show_result) continue;
			for (const slice of overview.donut.values) {
				if (slice.value > 0 && !statuses.has(slice.name)) {
					statuses.set(slice.name, {
						localName: slice.localName,
						color: slice.itemStyle.color
					});
				}
			}
		}
		return [...statuses.values()];
	});

	function toggle(key: string) {
		selectedTiers = selectedTiers.includes(key)
			? selectedTiers.filter((k) => k !== key)
			: [...selectedTiers, key];
	}

	const groupedData = $derived.by(() => {
		const grouped = new Map<
			string,
			{ folder_id: string; folder_name: string; assessments: any[] }
		>();
		for (const assessment of visible) {
			const folderId = assessment.folder_id || 'no-folder';
			if (!grouped.has(folderId)) {
				grouped.set(folderId, {
					folder_id: folderId,
					folder_name: assessment.folder_name || 'No Domain',
					assessments: []
				});
			}
			grouped.get(folderId)!.assessments.push(assessment);
		}
		return Array.from(grouped.values());
	});
</script>

{#if assessments.length}
	<Tabs value={tab} onValueChange={(e) => setTab(e.value)}>
		<Tabs.List class="px-6 pt-4">
			<Tabs.Trigger value="posture" data-testid="tab-posture">{m.vendorPosture()}</Tabs.Trigger>
			<Tabs.Trigger value="assessments" data-testid="tab-assessments">
				{m.entityAssessments()}
				<span class="badge preset-tonal-surface ml-2">{assessments.length}</span>
			</Tabs.Trigger>
			<Tabs.Indicator />
		</Tabs.List>
		<Tabs.Content value="posture">
			<VendorPosture
				{assessments}
				{tiers}
				noTier={NO_TIER}
				onSelectTier={(key) => {
					selectedTiers = [key];
					setTab('assessments');
				}}
			/>
		</Tabs.Content>
		<Tabs.Content value="assessments">
			<div
				class="px-6 pt-6 flex flex-wrap items-end justify-between gap-4"
				data-testid="tprm-filters"
			>
				{#if tiers.length}
					<div data-testid="entities-by-tier">
						<h2 class="text-sm font-semibold uppercase tracking-wider text-surface-500 mb-2">
							{m.entitiesByTier()}
						</h2>
						<div class="flex flex-wrap gap-2">
							{#each pills as pill (pill.key)}
								{@const active = selectedTiers.includes(pill.key)}
								<button
									type="button"
									class="card flex items-center gap-2 px-3 py-2 bg-surface-50-950 border-2 transition-colors {active
										? 'border-primary-500'
										: 'border-surface-200-800 hover:border-primary-300'}"
									aria-pressed={active}
									onclick={() => toggle(pill.key)}
									data-testid="tier-pill"
								>
									{#if pill.tier}
										<TierBadge cell={pill.tier} />
									{:else}
										<span class="text-sm text-surface-500">{m.untiered()}</span>
									{/if}
									<span class="font-mono font-semibold">{pill.count}</span>
								</button>
							{/each}
							{#if selectedTiers.length}
								<button
									type="button"
									class="btn btn-sm preset-tonal self-center"
									onclick={() => (selectedTiers = [])}>{m.clearFilters()}</button
								>
							{/if}
						</div>
					</div>
				{/if}
				<label class="w-full sm:w-96">
					<span class="sr-only">{m.search()}</span>
					<input
						type="search"
						class="input"
						placeholder={m.searchVendorOrDomain()}
						bind:value={query}
						data-testid="tprm-search"
					/>
				</label>
			</div>

			{#if complianceLegend.length}
				<div
					class="px-6 pt-4 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-surface-600-400"
					data-testid="compliance-legend"
				>
					<span class="text-xs font-semibold uppercase tracking-wider text-surface-500">
						{m.compliance()}
					</span>
					{#each complianceLegend as status (status.localName)}
						<span class="flex items-center gap-1.5">
							<span
								class="size-2.5 shrink-0 rounded-full ring-1 ring-surface-400-600"
								style="background-color: {status.color}"
							></span>
							{safeTranslate(status.localName)}
						</span>
					{/each}
				</div>
			{/if}

			{#if groupedData.length > 0}
				<div class="p-6 bg-surface-50-950 bg-opacity-95 space-y-8">
					{#each groupedData as group (group.folder_id)}
						<div>
							<div class="flex items-center gap-3 mb-4">
								{#if group.folder_id && group.folder_id !== 'no-folder'}
									<a
										href="/folders/{group.folder_id}"
										class="text-xl font-bold text-surface-950-50 hover:text-primary-600 hover:underline"
									>
										{group.folder_name}
									</a>
								{:else}
									<span class="text-xl font-bold text-surface-950-50">{group.folder_name}</span>
								{/if}
								<span class="badge preset-tonal-secondary">{group.assessments.length}</span>
							</div>
							<div
								class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
								role="list"
								data-testid="cards-list"
							>
								{#each group.assessments as entity_assessment (entity_assessment.entity_assessment_id)}
									<FlippableCard {entity_assessment} />
								{/each}
							</div>
						</div>
					{/each}
				</div>
			{:else}
				<div class="p-6 text-sm text-surface-500" data-testid="no-match">
					{m.noAssessmentMatchesFilters()}
				</div>
			{/if}
		</Tabs.Content>
	</Tabs>
{:else}
	<div class="p-4" data-testid="no-data-available">{m.noDataAvailable()}</div>
{/if}
