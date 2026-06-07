<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import { getFlash } from 'sveltekit-flash-message';
	import type { PageData } from './$types';

	const flash = getFlash(page);

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const preview = data.previewData;
	const currentResults = preview.current_results;
	const projectedResults = preview.projected_results;
	const assessableCount = preview.assessable_requirements_count;

	const RESULT_KEYS = [
		'compliant',
		'non_compliant',
		'partially_compliant',
		'not_applicable',
		'not_assessed'
	] as const;

	const resultColors: Record<string, string> = {
		compliant: '#86efac',
		non_compliant: '#f87171',
		partially_compliant: '#fde047',
		not_applicable: '#000000',
		not_assessed: '#d1d5db'
	};

	const resultTextColors: Record<string, string> = {
		compliant: 'black',
		non_compliant: 'black',
		partially_compliant: 'black',
		not_applicable: 'white',
		not_assessed: 'black'
	};

	function getPercentage(results: Record<string, number>, key: string): number {
		if (!assessableCount) return 0;
		return ((results[key] || 0) / assessableCount) * 100;
	}

	// Group the source requirements by framework so the (long) framework name is
	// shown once per group instead of repeated on every requirement.
	function groupSources(sources: any[] = []): { framework: string; items: any[] }[] {
		const groups = new Map<string, any[]>();
		for (const s of sources ?? []) {
			const key = s.framework ?? '';
			if (!groups.has(key)) groups.set(key, []);
			groups.get(key)!.push(s);
		}
		return [...groups.entries()].map(([framework, items]) => ({ framework, items }));
	}

	let isEnriching = $state(false);

	async function confirmEnrich() {
		isEnriching = true;
		try {
			const response = await fetch(`/compliance-assessments/${data.targetId}/enrich`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ source_audit_id: data.sourceId })
			});

			if (response.ok) {
				const result = await response.json();
				flash.set({
					type: 'success',
					message: `${m.enrichFromSourceSuccess()} (${result.enriched_count} ${m.requirementsEnriched()})`
				});
				goto(`/compliance-assessments/${data.targetId}`);
			} else {
				const err = await response.json();
				flash.set({
					type: 'error',
					message: err.error || m.enrichFromSourceError()
				});
			}
		} catch {
			flash.set({ type: 'error', message: m.enrichFromSourceError() });
		} finally {
			isEnriching = false;
		}
	}
</script>

<div class="flex flex-col space-y-4">
	<!-- Header -->
	<div class="card p-4 bg-white shadow-lg">
		<div class="flex items-center justify-between mb-4">
			<div class="flex flex-col">
				<div class="h4 font-bold">
					<i class="fa-solid fa-arrow-right-to-bracket mr-2"></i>
					{m.enrichPreview()}
				</div>
				<div class="text-sm text-gray-600 mt-1">
					<span class="font-medium">{m.source()}:</span>
					{preview.source_audit.name} ({preview.source_audit.framework})
					<span class="mx-2">→</span>
					<span class="font-medium">{m.target()}:</span>
					{preview.target_audit.name} ({preview.target_audit.framework})
				</div>
			</div>
			<div class="flex gap-2">
				<Anchor
					href="/compliance-assessments/{data.targetId}"
					class="btn preset-filled-surface-500"
				>
					<i class="fa-solid fa-arrow-left mr-2"></i>
					{m.cancel()}
				</Anchor>
				<button
					class="btn preset-filled-primary-500"
					onclick={confirmEnrich}
					disabled={isEnriching || preview.enriched_count === 0}
				>
					{#if isEnriching}
						<i class="fa-solid fa-spinner fa-spin mr-2"></i>
					{:else}
						<i class="fa-solid fa-check mr-2"></i>
					{/if}
					{m.confirmEnrichment()}
				</button>
			</div>
		</div>

		<!-- Summary -->
		<div class="text-sm text-gray-700">
			<span class="font-semibold">{preview.enriched_count}</span>
			{m.requirementsEnriched()}
		</div>
	</div>

	<!-- Compliance Distribution Comparison -->
	<div class="card bg-white shadow-lg">
		<div class="px-6 py-4 border-b border-gray-200">
			<h2 class="h4 font-bold">
				<i class="fa-solid fa-chart-pie mr-2"></i>
				{m.compliance()}
			</h2>
		</div>
		<div class="grid grid-cols-2 divide-x divide-gray-200">
			<!-- Current State -->
			<div class="p-6">
				<h3 class="h5 font-bold text-primary-500 mb-4">{m.currentState()}</h3>
				<div class="flex grow bg-gray-200 rounded-md overflow-hidden h-6">
					{#each RESULT_KEYS as key}
						{@const pct = getPercentage(currentResults, key)}
						{#if pct > 0}
							<div
								class="flex flex-col justify-center overflow-hidden text-xs text-center"
								style="width: {pct}%; background-color: {resultColors[
									key
								]}; color: {resultTextColors[key]}"
							>
								{pct.toFixed(0)}%
							</div>
						{/if}
					{/each}
				</div>
				<div class="mt-3 space-y-1">
					{#each RESULT_KEYS as key}
						{@const count = currentResults[key] || 0}
						{#if count > 0}
							<div class="flex items-center gap-2 text-sm">
								<span
									class="inline-block w-3 h-3 rounded-sm"
									style="background-color: {resultColors[key]}"
								></span>
								<span>{safeTranslate(key)}: {count}</span>
							</div>
						{/if}
					{/each}
				</div>
			</div>

			<!-- Projected State -->
			<div class="p-6">
				<h3 class="h5 font-bold text-secondary-500 mb-4">{m.projectedState()}</h3>
				<div class="flex grow bg-gray-200 rounded-md overflow-hidden h-6">
					{#each RESULT_KEYS as key}
						{@const pct = getPercentage(projectedResults, key)}
						{#if pct > 0}
							<div
								class="flex flex-col justify-center overflow-hidden text-xs text-center"
								style="width: {pct}%; background-color: {resultColors[
									key
								]}; color: {resultTextColors[key]}"
							>
								{pct.toFixed(0)}%
							</div>
						{/if}
					{/each}
				</div>
				<div class="mt-3 space-y-1">
					{#each RESULT_KEYS as key}
						{@const count = projectedResults[key] || 0}
						{#if count > 0}
							<div class="flex items-center gap-2 text-sm">
								<span
									class="inline-block w-3 h-3 rounded-sm"
									style="background-color: {resultColors[key]}"
								></span>
								<span>{safeTranslate(key)}: {count}</span>
							</div>
						{/if}
					{/each}
				</div>
			</div>
		</div>
	</div>

	<!-- Differences Table -->
	{#if preview.differences && preview.differences.length > 0}
		<div class="card bg-white shadow-lg">
			<div class="px-6 py-4 border-b border-gray-200">
				<h2 class="h4 font-bold">
					<i class="fa-solid fa-code-compare mr-2"></i>
					{m.requirementDifferences()}
				</h2>
				<p class="text-sm text-gray-600 mt-1">
					{preview.differences.length}
					{preview.differences.length === 1 ? m.requirement() : m.requirements()}
					{m.withDifferences()}
				</p>
			</div>
			<div class="overflow-x-auto">
				<table class="table-auto w-full">
					<thead>
						<tr class="bg-gray-50">
							<th
								class="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider"
							>
								{m.requirement()}
							</th>
							<th
								class="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider"
							>
								{m.sourceRequirement()}
							</th>
							<th
								class="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider"
							>
								{m.currentState()}
							</th>
							<th
								class="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider"
							>
								{m.projectedState()}
							</th>
						</tr>
					</thead>
					<tbody class="divide-y divide-gray-200">
						{#each preview.differences as diff}
							<tr class="hover:bg-gray-50">
								<td class="px-6 py-4">
									<div class="flex flex-col">
										{#if diff.requirement.ref_id}
											<span class="font-semibold text-sm">{diff.requirement.ref_id}</span>
										{/if}
										{#if diff.requirement.name}
											<span class="text-sm text-gray-900">{diff.requirement.name}</span>
										{/if}
										<span
											class="text-xs mt-1"
											class:text-emerald-600={diff.coverage === 'full'}
											class:text-amber-600={diff.coverage === 'partial'}
										>
											{diff.coverage === 'full' ? m.fullCoverage() : m.partialCoverage()}
										</span>
									</div>
								</td>
								<td class="px-6 py-4">
									<div class="flex flex-col space-y-2">
										{#each groupSources(diff.sources) as group}
											<div class="flex flex-col gap-1">
												{#if group.framework}
													<span class="text-xs text-gray-400">{group.framework}</span>
												{/if}
												<div class="flex flex-wrap gap-1">
													{#each group.items as source}
														<span class="badge preset-tonal text-xs" title={source.name}>
															{source.ref_id ?? source.name}
														</span>
													{/each}
												</div>
											</div>
										{/each}
									</div>
								</td>
								<td class="px-6 py-4">
									<div class="flex flex-col space-y-1">
										{#if diff.base.result !== undefined}
											<div class="flex items-center space-x-2">
												<span class="text-xs text-gray-500">{m.result()}:</span>
												<span
													class="badge text-xs"
													style="background-color: {resultColors[diff.base.result] ||
														'#d1d5db'}; color: {resultTextColors[diff.base.result] || 'black'};"
												>
													{safeTranslate(diff.base.result)}
												</span>
											</div>
										{/if}
										{#if diff.base.score !== null && diff.base.score !== undefined}
											<div class="flex items-center space-x-2">
												<span class="text-xs text-gray-500">{m.score()}:</span>
												<span class="text-xs font-medium">{diff.base.score}</span>
											</div>
										{/if}
									</div>
								</td>
								<td class="px-6 py-4">
									<div class="flex flex-col space-y-1">
										{#if diff.compare.result !== undefined}
											<div class="flex items-center space-x-2">
												<span class="text-xs text-gray-500">{m.result()}:</span>
												<span
													class="badge text-xs"
													style="background-color: {resultColors[diff.compare.result] ||
														'#d1d5db'}; color: {resultTextColors[diff.compare.result] || 'black'};"
												>
													{safeTranslate(diff.compare.result)}
												</span>
											</div>
										{/if}
										{#if diff.compare.score !== null && diff.compare.score !== undefined}
											<div class="flex items-center space-x-2">
												<span class="text-xs text-gray-500">{m.score()}:</span>
												<span class="text-xs font-medium">{diff.compare.score}</span>
											</div>
										{/if}
										{#if diff.compare.observation !== undefined}
											<div class="flex items-center space-x-2">
												<i class="fa-solid fa-pen-to-square text-xs text-gray-400"></i>
												<span class="text-xs text-gray-500">{m.observation()}</span>
											</div>
										{/if}
										{#if diff.m2m_added?.applied_controls}
											<span class="badge preset-tonal-primary text-xs">
												+{diff.m2m_added.applied_controls}
												{m.appliedControls()}
											</span>
										{/if}
										{#if diff.m2m_added?.evidences}
											<span class="badge preset-tonal-secondary text-xs">
												+{diff.m2m_added.evidences}
												{m.evidences()}
											</span>
										{/if}
										{#if diff.m2m_added?.security_exceptions}
											<span class="badge preset-tonal-warning text-xs">
												+{diff.m2m_added.security_exceptions}
												{m.securityExceptions()}
											</span>
										{/if}
									</div>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	{:else}
		<div class="card bg-white shadow-lg p-6 text-center text-gray-500">
			<i class="fa-solid fa-circle-info text-2xl mb-2"></i>
			<p>{m.enrichNoChanges()}</p>
		</div>
	{/if}
</div>
