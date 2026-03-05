<script lang="ts">
	import type { PageData } from './$types';
	import { m } from '$paraglide/messages';
	import { goto, invalidateAll } from '$app/navigation';
	import { page } from '$app/stores';
	import { getModalStore } from '$lib/components/Modals/stores';
	import PromptConfirmModal from '$lib/components/Modals/PromptConfirmModal.svelte';

	let { data }: { data: PageData } = $props();

	const modalStore = getModalStore();

	const STATUS_STYLES: Record<
		string,
		{ label: () => string; icon: string; bg: string; text: string }
	> = {
		not_started: {
			label: () => m.notStarted(),
			icon: 'fa-circle',
			bg: 'bg-gray-100',
			text: 'text-gray-500'
		},
		in_progress: {
			label: () => m.inProgress(),
			icon: 'fa-circle-half-stroke',
			bg: 'bg-amber-50',
			text: 'text-amber-600'
		},
		done: {
			label: () => m.done(),
			icon: 'fa-circle-check',
			bg: 'bg-green-50',
			text: 'text-green-600'
		},
		skipped: {
			label: () => m.skipped(),
			icon: 'fa-forward',
			bg: 'bg-gray-50',
			text: 'text-gray-400'
		}
	};

	async function updateStepStatus(stepId: string, newStatus: string) {
		await fetch(`/preset-journeys/${$page.params.id}/step/${stepId}`, {
			method: 'PATCH',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ status: newStatus })
		});
		invalidateAll();
	}

	function getStepLink(step: any): string | null {
		if (!step.target_model) return null;
		const folderId = data.journey?.folder?.id;
		if (step.target_ref) {
			return `/${step.target_model}/${step.target_ref}`;
		}
		if (folderId) {
			return `/${step.target_model}?folder=${folderId}`;
		}
		return `/${step.target_model}`;
	}

	// --- Edit mode for step links ---
	let editMode = $state(false);
	let choicesCache: Record<string, { id: string; str: string }[]> = $state({});
	// Track in-flight requests without $state to avoid mutation-in-template errors
	const _loadingChoices: Set<string> = new Set();

	async function fetchChoices(targetModel: string) {
		if (choicesCache[targetModel] || _loadingChoices.has(targetModel)) return;
		_loadingChoices.add(targetModel);
		try {
			const folderId = data.journey?.folder?.id;
			const url = folderId
				? `/${targetModel}?folder=${folderId}`
				: `/${targetModel}`;
			const resp = await fetch(url, { headers: { Accept: 'application/json' } });
			if (resp.ok) {
				const json = await resp.json();
				const results = json.results ?? json;
				choicesCache[targetModel] = Array.isArray(results)
					? results.map((r: any) => ({ id: r.id, str: r.str ?? r.name ?? r.id }))
					: [];
			}
		} catch (e) {
			console.error('Failed to fetch choices for', targetModel, e);
		} finally {
			_loadingChoices.delete(targetModel);
		}
	}

	// Prefetch choices when edit mode is toggled on
	$effect(() => {
		if (editMode && data.steps) {
			const models = new Set(
				data.steps.filter((s: any) => s.target_model).map((s: any) => s.target_model)
			);
			for (const model of models) {
				fetchChoices(model);
			}
		}
	});

	async function updateStepTargetRef(stepId: string, targetRef: string | null) {
		await fetch(`/preset-journeys/${$page.params.id}/step/${stepId}`, {
			method: 'PATCH',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ target_ref: targetRef })
		});
		invalidateAll();
	}

	let upgrading = $state(false);

	async function upgradeJourney() {
		upgrading = true;
		try {
			const response = await fetch(`/preset-journeys/${$page.params.id}/upgrade`, {
				method: 'POST'
			});
			if (response.ok) {
				invalidateAll();
			}
		} catch (e) {
			console.error('Failed to upgrade journey', e);
		} finally {
			upgrading = false;
		}
	}

	function deleteJourney() {
		modalStore.trigger({
			type: 'component',
			title: m.deleteJourney(),
			body: m.deleteJourneyConfirm(),
			component: {
				ref: PromptConfirmModal,
				props: {
					bodyComponent: undefined
				}
			},
			response: async (confirmed: boolean) => {
				if (!confirmed) return;
				const response = await fetch(`/preset-journeys/${$page.params.id}`, {
					method: 'DELETE'
				});
				if (response.ok) {
					goto('/presets');
				}
			}
		});
	}
</script>

{#if !data.journey}
	<div class="flex flex-col items-center justify-center p-10">
		<p class="text-gray-400 mb-4">{m.journeyNotFound()}</p>
		<a href="/presets" class="btn preset-tonal-surface border border-surface-500">
			<i class="fa-solid fa-arrow-left mr-2"></i>
			{m.presets()}
		</a>
	</div>
{:else}
	<div class="flex flex-col lg:flex-row gap-6 p-2">
		<!-- Main content -->
		<div class="flex-1 min-w-0 space-y-4">
			<!-- Header -->
			<div class="flex items-center gap-3">
				<a href="/presets" class="btn-icon btn-icon-sm text-gray-400 hover:text-gray-600">
					<i class="fa-solid fa-arrow-left"></i>
				</a>
				<div class="flex-1 min-w-0">
					<h2 class="text-xl font-semibold">{data.journey.name}</h2>
					{#if data.journey.description}
						<p class="text-sm text-gray-400">{data.journey.description}</p>
					{/if}
				</div>
				{#if data.journey.latest_version && data.journey.latest_version > data.journey.version}
					<button
						type="button"
						class="btn btn-sm preset-filled-warning-500"
						onclick={upgradeJourney}
						disabled={upgrading}
					>
						<i class="fa-solid fa-arrow-up mr-1"></i>
						{m.upgradeAvailable()}
					</button>
				{/if}
				<button
					type="button"
					class="btn btn-sm preset-tonal-surface border border-surface-500"
					onclick={() => (editMode = !editMode)}
				>
					<i class="fa-solid {editMode ? 'fa-check' : 'fa-pen'} mr-1"></i>
					{editMode ? m.doneEditing() : m.editStepLinks()}
				</button>
				<button
					type="button"
					class="btn btn-sm preset-tonal-surface border border-red-300 text-red-600 hover:bg-red-50"
					onclick={deleteJourney}
				>
					<i class="fa-solid fa-trash-can mr-1"></i>
					{m.delete()}
				</button>
			</div>

			<!-- Progress bar -->
			<div class="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
				<div class="flex items-center justify-between mb-2">
					<span class="font-medium text-sm">{m.journeyProgress()}</span>
					<span class="text-sm font-mono text-gray-500">{data.stats.progress_percent ?? 0}%</span>
				</div>
				<div class="h-3 rounded-full bg-gray-100 overflow-hidden">
					<div
						class="h-full rounded-full bg-violet-500 transition-all duration-500"
						style="width: {data.stats.progress_percent ?? 0}%"
					></div>
				</div>
				<p class="text-xs text-gray-400 mt-1.5">
					{m.stepsCompleted({
						completed: String(data.stats.completed_steps ?? 0),
						total: String(data.stats.total_steps ?? 0)
					})}
				</p>
			</div>

			<!-- Steps -->
			<div class="space-y-2">
				{#each data.steps as step, i}
					{@const style = STATUS_STYLES[step.status] || STATUS_STYLES.not_started}
					{@const link = getStepLink(step)}
					<div class="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
						<div class="flex items-start gap-3">
							<!-- Step number & status -->
							<div class="flex flex-col items-center gap-1.5 pt-0.5" style="min-width: 2rem;">
								<span class="text-xs font-mono text-gray-300">{i + 1}</span>
								<span
									class="inline-flex items-center rounded-full px-2 py-0.5 text-xs {style.bg} {style.text}"
								>
									<i class="fa-solid {style.icon} mr-1"></i>
									{style.label()}
								</span>
							</div>

							<!-- Content -->
							<div class="flex-1 min-w-0">
								<h4 class="font-medium">{step.title}</h4>
								{#if step.description}
									<p class="text-sm text-gray-400 mt-0.5">{step.description}</p>
								{/if}
								{#if editMode && step.target_model && choicesCache[step.target_model]}
									<div class="mt-2">
										<select
											class="select select-sm text-sm max-w-xs"
											value={step.target_ref ?? ''}
											onchange={(e) => {
												const val = (e.target as HTMLSelectElement).value;
												updateStepTargetRef(step.id, val || null);
											}}
										>
											<option value="">{m.noLinkedObject()}</option>
											{#each choicesCache[step.target_model] ?? [] as choice}
												<option value={choice.id}>{choice.str}</option>
											{/each}
										</select>
									</div>
								{/if}
							</div>

							<!-- Actions -->
							<div class="flex items-center gap-2 shrink-0">
								{#if link}
									<a href={link} class="btn btn-sm preset-tonal-surface border border-surface-500">
										<i class="fa-solid fa-arrow-up-right-from-square mr-1"></i>
										{m.goToStep()}
									</a>
								{/if}
								{#if step.status === 'not_started'}
									<button
										type="button"
										class="btn btn-sm preset-filled-warning-500"
										onclick={() => updateStepStatus(step.id, 'in_progress')}
									>
										{m.startStep()}
									</button>
								{:else if step.status === 'in_progress'}
									<button
										type="button"
										class="btn btn-sm preset-filled-success-500"
										onclick={() => updateStepStatus(step.id, 'done')}
									>
										<i class="fa-solid fa-check mr-1"></i>
										{m.markAsDone()}
									</button>
									<button
										type="button"
										class="btn btn-sm preset-tonal-surface border border-surface-500"
										onclick={() => updateStepStatus(step.id, 'skipped')}
									>
										{m.markAsSkipped()}
									</button>
								{:else if step.status === 'done' || step.status === 'skipped'}
									<button
										type="button"
										class="btn btn-sm preset-tonal-surface border border-surface-500"
										onclick={() => updateStepStatus(step.id, 'not_started')}
									>
										<i class="fa-solid fa-rotate-left"></i>
									</button>
								{/if}
							</div>
						</div>
					</div>
				{/each}
			</div>
		</div>

		<!-- Stats sidebar -->
		<div class="lg:w-72 shrink-0 space-y-4">
			<div class="rounded-lg border border-gray-200 bg-white p-4 shadow-sm space-y-3">
				<h3 class="font-semibold text-sm">{m.stats()}</h3>
				<div class="space-y-2 text-sm">
					<div class="flex justify-between">
						<span class="text-gray-400">{m.assets()}</span>
						<span class="font-mono">{data.stats.assets ?? 0}</span>
					</div>
					<div class="flex justify-between">
						<span class="text-gray-400">{m.riskScenarios()}</span>
						<span class="font-mono">{data.stats.risk_scenarios ?? 0}</span>
					</div>
					<div class="flex justify-between">
						<span class="text-gray-400">{m.appliedControls()}</span>
						<span class="font-mono">{data.stats.applied_controls ?? 0}</span>
					</div>
				</div>
			</div>

			{#if data.stats.compliance && Object.keys(data.stats.compliance).length > 0}
				<div class="rounded-lg border border-gray-200 bg-white p-4 shadow-sm space-y-3">
					<h3 class="font-semibold text-sm">{m.compliance()}</h3>
					{#each Object.entries(data.stats.compliance) as [, info]}
						{@const compInfo = info as {
							name: string;
							total: number;
							assessed: number;
							percent: number;
						}}
						<div class="space-y-1">
							<div class="flex justify-between text-sm">
								<span class="text-gray-400 truncate mr-2">{compInfo.name}</span>
								<span class="font-mono shrink-0">{compInfo.percent}%</span>
							</div>
							<div class="h-1.5 rounded-full bg-gray-100 overflow-hidden">
								<div
									class="h-full rounded-full bg-sky-500"
									style="width: {compInfo.percent}%"
								></div>
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	</div>
{/if}
