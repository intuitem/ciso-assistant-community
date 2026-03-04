<script lang="ts">
	import type { PageData } from './$types';
	import { m } from '$paraglide/messages';
	import { goto } from '$app/navigation';
	import { getModalStore } from '$lib/components/Modals/stores';
	import ApplyPresetModal from '$lib/components/Modals/ApplyPresetModal.svelte';

	let { data }: { data: PageData } = $props();

	const modalStore = getModalStore();

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
					onApply: async (payload: { folder_name?: string; folder_id?: string }) => {
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
								goto(`/preset-journeys/${result.journey_id}`);
								return { ok: true };
							}
							const err = await response.json().catch(() => ({}));
							const raw = err.error ?? err;
							let message: string;
							if (typeof raw === 'string') {
								message = raw;
							} else if (typeof raw === 'object') {
								// e.g. {"name": ["msg"]} → flatten all values
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

	const OBJECT_TYPE_META: Record<string, { label: () => string; icon: string }> = {
		risk_assessment: { label: () => m.riskAssessment(), icon: 'fa-chart-line' },
		compliance_assessment: { label: () => m.complianceAssessment(), icon: 'fa-list-check' },
		task_template: { label: () => m.taskTemplate(), icon: 'fa-calendar-check' },
		organisation_objective: { label: () => m.organisationObjective(), icon: 'fa-bullseye' },
		organisation_issue: { label: () => m.organisationIssue(), icon: 'fa-triangle-exclamation' },
		perimeter: { label: () => m.perimeter(), icon: 'fa-draw-polygon' },
		processing: { label: () => m.processing(), icon: 'fa-gears' },
		entity: { label: () => m.entity(), icon: 'fa-building' },
		findings_assessment: { label: () => m.findingsAssessment(), icon: 'fa-binoculars' }
	};

	function getProgressPercent(journey: any): number {
		const steps = journey.steps || [];
		if (steps.length === 0) return 0;
		const completed = steps.filter(
			(s: any) => s.status === 'done' || s.status === 'skipped'
		).length;
		return Math.round((completed / steps.length) * 100);
	}
</script>

<div class="flex flex-col space-y-6 whitespace-pre-line p-2">
	<!-- Available Presets -->
	<section>
		<h2 class="text-xl font-semibold mb-4">{m.availablePresets()}</h2>
		{#if data.presets.length === 0}
			<div
				class="flex flex-col items-center justify-center rounded-lg border border-gray-200 bg-white p-10 text-gray-400 shadow-sm"
			>
				<i class="fa-solid fa-box-open text-4xl mb-3"></i>
				<p>{m.noPresetsAvailable()}</p>
			</div>
		{:else}
			<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
				{#each data.presets as preset}
					<div
						class="flex flex-col rounded-lg border border-gray-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow"
					>
						<div class="flex items-start justify-between gap-2 mb-2">
							<div class="min-w-0">
								<h3 class="font-semibold text-base truncate">{preset.name}</h3>
								{#if preset.provider}
									<span class="text-xs text-gray-400">{preset.provider}</span>
								{/if}
							</div>
						</div>
						{#if preset.description}
							<p class="text-sm text-gray-500 mb-3 line-clamp-3">{preset.description}</p>
						{/if}
						{#if preset.profile}
							<div class="flex flex-wrap gap-1 mb-3">
								{#each getProfileTags(preset.profile) as tag}
									<span
										class="inline-block rounded-full bg-violet-50 px-2 py-0.5 text-xs text-violet-700"
										>{tag}</span
									>
								{/each}
							</div>
						{/if}
						{#if preset.scaffolded_objects?.length}
							<div class="text-xs text-gray-500 mb-3 space-y-1">
								{#each preset.scaffolded_objects as obj}
									{@const meta = OBJECT_TYPE_META[obj.type]}
									{#if meta}
										<div class="flex items-center gap-1.5">
											<i class="fa-solid {meta.icon} w-3.5 text-center text-gray-400"></i>
											<span>{obj.count} {meta.label()}{obj.count > 1 ? 's' : ''}</span>
										</div>
									{/if}
								{/each}
							</div>
						{/if}
						<div class="mt-auto pt-2">
							<button
								type="button"
								class="btn preset-filled-primary-500 w-full"
								onclick={() => applyPreset(preset.id, preset.name)}
							>
								<i class="fa-solid fa-rocket mr-2"></i>
								{m.applyPreset()}
							</button>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</section>

	<!-- Active Journeys -->
	<section>
		<h2 class="text-xl font-semibold mb-4">{m.activeJourneys()}</h2>
		{#if data.journeys.length === 0}
			<div
				class="flex flex-col items-center justify-center rounded-lg border border-gray-200 bg-white p-10 text-gray-400 shadow-sm"
			>
				<i class="fa-solid fa-route text-4xl mb-3"></i>
				<p>{m.noActiveJourneys()}</p>
			</div>
		{:else}
			<div class="space-y-3">
				{#each data.journeys as journey}
					{@const progress = getProgressPercent(journey)}
					<a
						href="/preset-journeys/{journey.id}"
						class="flex items-center gap-4 rounded-lg border border-gray-200 bg-white p-4 shadow-sm hover:shadow-md hover:border-violet-200 transition-all"
					>
						<div class="flex-1 min-w-0">
							<h3 class="font-semibold truncate">{journey.name}</h3>
							{#if journey.description}
								<p class="text-sm text-gray-400 truncate">{journey.description}</p>
							{/if}
						</div>
						<div class="flex items-center gap-3 shrink-0 w-48">
							<div class="flex-1 h-2 rounded-full bg-gray-100 overflow-hidden">
								<div
									class="h-full rounded-full bg-violet-500 transition-all"
									style="width: {progress}%"
								></div>
							</div>
							<span class="text-sm font-mono text-gray-500 w-10 text-right">{progress}%</span>
						</div>
						<i class="fa-solid fa-chevron-right text-gray-300"></i>
					</a>
				{/each}
			</div>
		{/if}
	</section>
</div>
