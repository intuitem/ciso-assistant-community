<script lang="ts">
	import { getModalStore } from '$lib/components/Modals/stores';
	import { m } from '$paraglide/messages';
	import WorkflowGraphPreview from './WorkflowGraphPreview.svelte';

	interface Props {
		// The LOADED library whose stored workflow documents we preview.
		loadedLibraryId: string;
	}
	let { loadedLibraryId }: Props = $props();

	const modalStore = getModalStore();

	let loading = $state(true);
	let error = $state('');
	let workflows = $state<any[]>([]);
	let selected = $state(0);

	const current = $derived(workflows[selected]);
	const requiredSecrets = $derived<string[]>(current?.requires?.secrets ?? []);

	async function load() {
		try {
			const res = await fetch(`/loaded-libraries/${loadedLibraryId}/preview-workflows`);
			const body = await res.json().catch(() => ({}));
			if (!res.ok) {
				// Some endpoints answer with a bare JSON string, others with
				// {error: ...} — mirror InstantiateWorkflows.
				error = String(typeof body === 'string' ? body : (body.error ?? res.statusText));
				return;
			}
			workflows = body.workflows ?? [];
			if (!workflows.length) error = m.noWorkflowsToPreview();
		} catch (e) {
			error = String(e);
		} finally {
			loading = false;
		}
	}
	load();
</script>

<div class="card bg-surface-50-950 p-4 w-[min(90vw,1000px)] space-y-3 shadow-xl">
	<header class="flex items-center justify-between">
		<h2 class="text-lg font-semibold">{m.previewWorkflow()}</h2>
		<button
			type="button"
			class="btn-icon preset-tonal"
			aria-label={m.cancel()}
			onclick={() => modalStore.close()}
		>
			<i class="fa-solid fa-xmark"></i>
		</button>
	</header>

	{#if loading}
		<p class="p-6 text-center text-sm text-surface-500">
			<i class="fa-solid fa-spinner fa-spin mr-1"></i>
		</p>
	{:else if error}
		<p class="p-6 text-center text-sm text-error-500">{error}</p>
	{:else}
		{#if workflows.length > 1}
			<div class="flex flex-wrap gap-1" data-testid="preview-workflow-tabs">
				{#each workflows as wf, i (wf.ref_id || i)}
					<button
						type="button"
						class="btn btn-sm {i === selected ? 'preset-filled-primary-500' : 'preset-tonal'}"
						onclick={() => (selected = i)}
					>
						{wf.name}
					</button>
				{/each}
			</div>
		{:else}
			<p class="font-medium">{current?.name}</p>
		{/if}

		{#key selected}
			<WorkflowGraphPreview graph={current?.graph ?? {}} />
		{/key}

		{#if requiredSecrets.length}
			<div class="space-y-1" data-testid="preview-required-secrets">
				<p class="text-sm font-medium text-surface-900-100">
					<i class="fa-solid fa-lock mr-1 text-surface-500"></i>{m.requiredSecrets()}
				</p>
				<p class="text-xs text-surface-600-400">{m.previewSecretsHint()}</p>
				<div class="flex flex-wrap gap-1">
					{#each requiredSecrets as name (name)}
						<span class="badge preset-tonal-surface font-mono text-xs">{name}</span>
					{/each}
				</div>
			</div>
		{/if}
	{/if}
</div>
