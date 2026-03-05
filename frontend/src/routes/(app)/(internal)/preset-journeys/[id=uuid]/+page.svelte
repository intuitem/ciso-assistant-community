<script lang="ts">
	import type { PageData } from './$types';
	import { m } from '$paraglide/messages';
	import { goto, invalidateAll } from '$app/navigation';
	import { page } from '$app/stores';
	import { getModalStore } from '$lib/components/Modals/stores';
	import PromptConfirmModal from '$lib/components/Modals/PromptConfirmModal.svelte';

	let { data }: { data: PageData } = $props();

	const modalStore = getModalStore();

	// Four-state progress counts
	const stepTotal = $derived(data.steps.length || 1);
	const stepCounts = $derived({
		done: data.steps.filter((s: any) => s.status === 'done').length,
		in_progress: data.steps.filter((s: any) => s.status === 'in_progress').length,
		skipped: data.steps.filter((s: any) => s.status === 'skipped').length,
		not_started: data.steps.filter((s: any) => s.status === 'not_started').length
	});

	const STATUS_STYLES: Record<
		string,
		{ label: () => string; icon: string; bg: string; text: string; dot: string }
	> = {
		not_started: {
			label: () => m.notStarted(),
			icon: 'fa-circle',
			bg: 'bg-gray-100',
			text: 'text-gray-500',
			dot: 'bg-gray-300 border-gray-300'
		},
		in_progress: {
			label: () => m.inProgress(),
			icon: 'fa-circle-half-stroke',
			bg: 'bg-amber-50',
			text: 'text-amber-600',
			dot: 'bg-amber-400 border-amber-400'
		},
		done: {
			label: () => m.done(),
			icon: 'fa-circle-check',
			bg: 'bg-green-50',
			text: 'text-green-600',
			dot: 'bg-green-500 border-green-500'
		},
		skipped: {
			label: () => m.skipped(),
			icon: 'fa-forward',
			bg: 'bg-gray-50',
			text: 'text-gray-400',
			dot: 'bg-gray-200 border-gray-300'
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
	let choicesCache: Record<string, { id: string; str: string; folder: string }[]> = $state({});
	// Track in-flight requests without $state to avoid mutation-in-template errors
	const _loadingChoices: Set<string> = new Set();

	async function fetchChoices(targetModel: string) {
		if (choicesCache[targetModel] || _loadingChoices.has(targetModel)) return;
		_loadingChoices.add(targetModel);
		try {
			const resp = await fetch(`/${targetModel}`, { headers: { Accept: 'application/json' } });
			if (resp.ok) {
				const json = await resp.json();
				const results = json.results ?? json;
				choicesCache[targetModel] = Array.isArray(results)
					? results.map((r: any) => ({
							id: r.id,
							str: r.str ?? r.name ?? r.id,
							folder: r.folder?.str ?? r.folder?.name ?? ''
						}))
					: [];
			}
		} catch (e) {
			console.error('Failed to fetch choices for', targetModel, e);
		} finally {
			_loadingChoices.delete(targetModel);
		}
	}

	// Prefetch choices when edit mode is toggled on — only for direct-link steps
	$effect(() => {
		if (editMode && data.steps) {
			const models = new Set(
				data.steps
					.filter((s: any) => s.target_model && s.target_ref != null)
					.map((s: any) => s.target_model)
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

	let compactMode = $state(false);
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
		<p class="text-gray-500 mb-4">{m.journeyNotFound()}</p>
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
			<div class="rounded-lg border border-gray-200 bg-white shadow-sm overflow-hidden">
				<div class="bg-gradient-to-r from-violet-600 to-indigo-600 px-4 py-3">
					<div class="flex items-start gap-3">
						<a
							href="/presets"
							class="mt-0.5 flex items-center justify-center w-8 h-8 rounded-md text-violet-200 hover:text-white hover:bg-white/10 transition-colors"
						>
							<i class="fa-solid fa-arrow-left"></i>
						</a>
						<div class="flex-1 min-w-0">
							<h2 class="text-lg font-semibold text-white">{data.journey.name}</h2>
							{#if data.journey.description}
								<p class="text-sm text-violet-100 mt-0.5">{data.journey.description}</p>
							{/if}
						</div>
					</div>
				</div>
				<!-- Toolbar -->
				<div class="flex items-center gap-2 px-4 py-2.5">
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
						onclick={() => (compactMode = !compactMode)}
						title={compactMode ? m.showDescriptions() : m.hideDescriptions()}
					>
						<i class="fa-solid {compactMode ? 'fa-expand' : 'fa-compress'} mr-1"></i>
						{compactMode ? m.showDescriptions() : m.hideDescriptions()}
					</button>
					<button
						type="button"
						class="btn btn-sm preset-tonal-surface border border-surface-500"
						onclick={() => (editMode = !editMode)}
					>
						<i class="fa-solid {editMode ? 'fa-check' : 'fa-pen'} mr-1"></i>
						{editMode ? m.doneEditing() : m.editStepLinks()}
					</button>
					<div class="flex-1"></div>
					<button
						type="button"
						class="btn btn-sm preset-tonal-surface border border-red-200 text-red-500 hover:bg-red-50 hover:border-red-300"
						onclick={deleteJourney}
					>
						<i class="fa-solid fa-trash-can mr-1"></i>
						{m.delete()}
					</button>
				</div>
			</div>

			<!-- Progress bar (four-state) -->
			<div class="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
				<div class="flex items-center justify-between mb-2">
					<span class="font-medium text-sm text-gray-800">{m.journeyProgress()}</span>
					<span class="text-sm font-mono text-gray-500">{data.stats.progress_percent ?? 0}%</span>
				</div>
				<div class="flex h-2.5 rounded-full bg-gray-100 overflow-hidden">
					{#if stepCounts.done}
						<div
							class="h-full bg-green-500 transition-all duration-500"
							style="width: {(stepCounts.done / stepTotal) * 100}%"
						></div>
					{/if}
					{#if stepCounts.in_progress}
						<div
							class="h-full bg-amber-400 transition-all duration-500"
							style="width: {(stepCounts.in_progress / stepTotal) * 100}%"
						></div>
					{/if}
					{#if stepCounts.skipped}
						<div
							class="h-full bg-gray-300 transition-all duration-500"
							style="width: {(stepCounts.skipped / stepTotal) * 100}%"
						></div>
					{/if}
				</div>
				<div class="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-xs text-gray-600">
					<span class="flex items-center gap-1.5">
						<span class="inline-block w-2 h-2 rounded-full bg-green-500"></span>
						{m.done()}
						{stepCounts.done}
					</span>
					<span class="flex items-center gap-1.5">
						<span class="inline-block w-2 h-2 rounded-full bg-amber-400"></span>
						{m.inProgress()}
						{stepCounts.in_progress}
					</span>
					<span class="flex items-center gap-1.5">
						<span class="inline-block w-2 h-2 rounded-full bg-gray-300"></span>
						{m.skipped()}
						{stepCounts.skipped}
					</span>
					<span class="flex items-center gap-1.5">
						<span class="inline-block w-2 h-2 rounded-full bg-gray-100 border border-gray-300"
						></span>
						{m.notStarted()}
						{stepCounts.not_started}
					</span>
				</div>
			</div>

			<!-- Steps with timeline -->
			<div class="relative">
				{#each data.steps as step, i}
					{@const style = STATUS_STYLES[step.status] || STATUS_STYLES.not_started}
					{@const link = getStepLink(step)}
					{@const isLast = i === data.steps.length - 1}
					<div class="relative flex gap-4 {isLast ? '' : 'pb-3'}">
						<!-- Timeline connector (spans full row height including padding) -->
						{#if !isLast}
							<div
								class="absolute left-[0.8125rem] top-[1.75rem] bottom-0 w-0.5 {step.status ===
								'done'
									? 'bg-green-500'
									: 'bg-gray-400'}"
							></div>
						{/if}
						<!-- Timeline dot -->
						<div class="relative flex flex-col items-center" style="min-width: 2rem;">
							<div
								class="w-7 h-7 rounded-full border-2 flex items-center justify-center text-xs font-semibold {style.dot} {step.status ===
								'done'
									? 'text-white'
									: step.status === 'in_progress'
										? 'text-white'
										: 'text-gray-500 bg-white'}"
							>
								{#if step.status === 'done'}
									<i class="fa-solid fa-check text-[10px]"></i>
								{:else if step.status === 'skipped'}
									<i class="fa-solid fa-forward text-[9px] text-gray-400"></i>
								{:else}
									{i + 1}
								{/if}
							</div>
						</div>

						<!-- Step card -->
						<div
							class="flex-1 min-w-0 rounded-lg border bg-white shadow-sm {step.status ===
							'in_progress'
								? 'border-amber-200'
								: step.status === 'done'
									? 'border-green-200'
									: 'border-gray-200'} p-3.5"
						>
							<div class="flex items-start gap-3">
								<div class="flex-1 min-w-0">
									<div class="flex items-center gap-2">
										{#if link}
											<a
												href={link}
												class="font-medium text-gray-800 hover:text-violet-600 transition-colors"
											>
												{step.title}
												<i
													class="fa-solid fa-arrow-up-right-from-square text-[10px] ml-1 opacity-40"
												></i>
											</a>
										{:else}
											<h4 class="font-medium text-gray-800">{step.title}</h4>
										{/if}
										<span
											class="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] leading-tight {style.bg} {style.text}"
										>
											{style.label()}
										</span>
									</div>
									{#if step.description && !compactMode}
										<p class="text-sm text-gray-500 mt-1">{step.description}</p>
									{/if}
									{#if editMode && step.target_ref != null && step.target_model && choicesCache[step.target_model]}
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
													<option value={choice.id}>
														{choice.str}{choice.folder ? ` — ${choice.folder}` : ''}
													</option>
												{/each}
											</select>
										</div>
									{/if}
								</div>

								<!-- Actions -->
								<div class="flex items-center gap-1.5 shrink-0">
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
											title={m.notStarted()}
										>
											<i class="fa-solid fa-rotate-left"></i>
										</button>
									{/if}
								</div>
							</div>
						</div>
					</div>
				{/each}
			</div>
		</div>

		<!-- Stats sidebar -->
		<div class="lg:w-72 shrink-0 space-y-4">
			<div class="rounded-lg border border-gray-200 bg-white p-4 shadow-sm space-y-3">
				<h3 class="font-semibold text-sm text-gray-800">{m.stats()}</h3>
				<div class="space-y-2 text-sm">
					<div class="flex justify-between">
						<span class="text-gray-600">{m.assets()}</span>
						<span class="font-mono text-gray-800">{data.stats.assets ?? 0}</span>
					</div>
					<div class="flex justify-between">
						<span class="text-gray-600">{m.riskScenarios()}</span>
						<span class="font-mono text-gray-800">{data.stats.risk_scenarios ?? 0}</span>
					</div>
					<div class="flex justify-between">
						<span class="text-gray-600">{m.appliedControls()}</span>
						<span class="font-mono text-gray-800">{data.stats.applied_controls ?? 0}</span>
					</div>
				</div>
			</div>

			{#if data.stats.compliance && Object.keys(data.stats.compliance).length > 0}
				<div class="rounded-lg border border-gray-200 bg-white p-4 shadow-sm space-y-3">
					<h3 class="font-semibold text-sm text-gray-800">{m.compliance()}</h3>
					{#each Object.entries(data.stats.compliance) as [, info]}
						{@const compInfo = info as {
							name: string;
							total: number;
							assessed: number;
							percent: number;
						}}
						<div class="space-y-1">
							<div class="flex justify-between text-sm">
								<span class="text-gray-600 truncate mr-2">{compInfo.name}</span>
								<span class="font-mono shrink-0 text-gray-800">{compInfo.percent}%</span>
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
