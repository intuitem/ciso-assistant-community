<script lang="ts">
	import { enhance } from '$app/forms';
	import { m } from '$paraglide/messages';
	import { getModalStore, type ModalSettings } from '$lib/components/Modals/stores';
	import { getToastStore } from '$lib/components/Toast/stores';
	import { superForm } from 'sveltekit-superforms';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import FolderTreeSelect from '$lib/components/Forms/FolderTreeSelect.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
	const modalStore = getModalStore();
	const toast = getToastStore();

	const createSuperform = superForm(data.createForm, {
		dataType: 'json',
		resetForm: true,
		invalidateAll: true,
		onUpdated: ({ form }) => {
			if (form.valid)
				toast.trigger({ message: m.saved(), background: 'preset-filled-success-500' });
		}
	});
	const { form: createData, enhance: createEnhance } = createSuperform;

	// Audits in the picked domain only.
	const auditOptions = $derived(
		(data.audits ?? [])
			.filter((a: any) => !$createData.folder || a.folder?.id === $createData.folder)
			.map((a: any) => ({ label: a.name, value: a.id }))
	);
	const selectedAudit = $derived(
		(data.audits ?? []).find((a: any) => a.id === $createData.source_audit)
	);
	// Implementation groups offered by the selected audit's framework.
	const igOptions = $derived(
		(selectedAudit?.framework?.implementation_groups_definition ?? []).map((ig: any) => ({
			label: ig.name ?? ig.ref_id,
			value: ig.ref_id
		}))
	);

	// Drop an audit that's no longer in the picked domain.
	$effect(() => {
		if ($createData.source_audit && !auditOptions.some((o) => o.value === $createData.source_audit))
			$createData.source_audit = undefined as any;
	});

	// Reset implementation groups whenever the chosen audit changes (different framework).
	let lastAudit: string | undefined = undefined;
	$effect(() => {
		const cur = $createData.source_audit as string | undefined;
		if (cur !== lastAudit) {
			lastAudit = cur;
			$createData.implementation_groups = [];
		}
	});

	// --- Edit (name + implementation groups + display mode) ---
	const DISPLAY_MODES = [
		{ value: 'both', label: () => m.displayScoreAndResult() },
		{ value: 'score', label: () => m.displayScoreOnly() },
		{ value: 'result', label: () => m.displayResultOnly() }
	];

	let editing = $state<any>(null);
	const editSuperform = superForm(data.editForm, {
		dataType: 'json',
		resetForm: false,
		invalidateAll: true,
		onUpdated: ({ form }) => {
			if (form.valid) {
				toast.trigger({ message: m.saved(), background: 'preset-filled-success-500' });
				editing = null;
			}
		}
	});
	const { form: editData, enhance: editEnhance } = editSuperform;

	const editIgOptions = $derived(
		(() => {
			const a = (data.audits ?? []).find((x: any) => x.id === editing?.source_audit?.id);
			return (a?.framework?.implementation_groups_definition ?? []).map((ig: any) => ({
				label: ig.name ?? ig.ref_id,
				value: ig.ref_id
			}));
		})()
	);

	function openEdit(snap: any) {
		editing = snap;
		editData.set({
			id: snap.id,
			name: snap.name,
			implementation_groups: snap.implementation_groups ?? [],
			display_mode: snap.display_mode ?? 'both'
		});
	}

	let diff = $state<any>(null);

	const previewEnhance =
		() =>
		async ({ result }: { result: any }) => {
			if (result.type === 'success' && result.data?.diff) diff = result.data.diff;
			else if (result.type === 'failure')
				toast.trigger({
					message: result.data?.error ?? m.error(),
					background: 'preset-filled-error-500'
				});
		};

	const applyEnhance =
		() =>
		async ({ result, update }: { result: any; update: any }) => {
			await update();
			if (result.type === 'success') {
				toast.trigger({ message: m.saved(), background: 'preset-filled-success-500' });
				diff = null;
			}
		};

	const METRICS = [
		{ key: 'compliant', label: () => m.compliant() },
		{ key: 'partially_compliant', label: () => m.partiallyCompliant() },
		{ key: 'non_compliant', label: () => m.nonCompliant() },
		{ key: 'not_applicable', label: () => m.notApplicable() },
		{ key: 'not_assessed', label: () => m.notAssessed() },
		{ key: 'requirement_count', label: () => m.requirements() },
		{ key: 'score', label: () => m.score() }
	];

	function delta(a: number | null | undefined, b: number | null | undefined) {
		const x = (b ?? 0) - (a ?? 0);
		if (x === 0) return '';
		return x > 0 ? `+${x}` : `${x}`;
	}

	function deltaClass(d: string) {
		if (d.startsWith('+')) return 'text-success-600';
		if (d.startsWith('-')) return 'text-error-600';
		return 'text-surface-400';
	}

	const diffRows = $derived.by(() => {
		if (!diff) return [];
		const rows = METRICS.map((mt) => ({
			label: mt.label(),
			current: diff.current[mt.key],
			next: diff.next[mt.key]
		}));
		rows.push({
			label: m.controlsCovered(),
			current: diff.controlsCurrent,
			next: diff.controlsNext
		});
		return rows;
	});

	function confirmDelete(e: MouseEvent, name: string) {
		const form = (e.currentTarget as HTMLElement).closest('form') as HTMLFormElement;
		const modal: ModalSettings = {
			type: 'confirm',
			title: m.delete(),
			body: m.deleteModalMessage({ name }),
			buttonTextConfirm: m.delete(),
			response: (confirmed: boolean) => {
				if (confirmed) form.requestSubmit();
			}
		};
		modalStore.trigger(modal);
	}
</script>

<div class="space-y-6">
	<div class="flex items-center gap-3">
		<a href="/portal-editor" class="text-surface-500 hover:text-primary-500">
			<i class="fa-solid fa-arrow-left"></i>
		</a>
		<h1 class="text-lg font-bold">{m.frameworkSnapshots()}</h1>
	</div>
	<p class="text-sm text-surface-500">{m.frameworkSnapshotsHelp()}</p>

	<section class="card bg-surface-50-950 p-6">
		<form method="POST" action="?/create" use:createEnhance class="space-y-3">
			<div class="grid gap-3 sm:grid-cols-2">
				<label class="text-xs text-surface-500">
					<span class="block">{m.name()}</span>
					<input bind:value={$createData.name} required class="input w-full rounded-md text-sm" />
				</label>
				<FolderTreeSelect form={createSuperform} field="folder" nullable label={m.domain()} />
			</div>
			{#key $createData.folder}
				<AutocompleteSelect
					form={createSuperform}
					field="source_audit"
					options={auditOptions}
					label={m.audit()}
				/>
			{/key}
			{#key $createData.source_audit}
				<AutocompleteSelect
					form={createSuperform}
					field="implementation_groups"
					multiple
					options={igOptions}
					disabled={!selectedAudit}
					label={m.implementationGroups()}
					helpText={m.implementationGroupsAllHelp()}
				/>
			{/key}
			<button class="btn btn-sm preset-filled-primary-500">
				<i class="fa-solid fa-plus mr-1"></i>{m.add()}
			</button>
		</form>
	</section>

	<section class="card bg-surface-50-950 p-6">
		<div class="divide-y divide-surface-200-800">
			{#each data.snapshots as s}
				<div class="flex items-center justify-between py-2">
					<div class="flex items-center gap-3">
						<i class="fa-solid fa-chart-pie text-surface-400"></i>
						<span class="font-medium">{s.name}</span>
						<span class="text-xs text-surface-400">{s.framework_name}</span>
						{#if s.summary?.requirement_count != null}
							<span class="text-xs text-surface-400"
								>· {s.summary.requirement_count} {m.requirements()}</span
							>
						{/if}
						{#if s.synced_at}
							<span class="text-[10px] text-surface-400"
								>{m.lastSynced()}: {new Date(s.synced_at).toLocaleDateString()}</span
							>
						{/if}
					</div>
					<div class="flex items-center gap-2">
						<button
							type="button"
							onclick={() => openEdit(s)}
							class="btn btn-sm preset-tonal"
							title={m.edit()}
							aria-label={m.edit()}><i class="fa-solid fa-pen"></i></button
						>
						<form method="POST" action="?/preview" use:enhance={previewEnhance}>
							<input type="hidden" name="id" value={s.id} />
							<button class="btn btn-sm preset-tonal" title={m.sync()} aria-label={m.sync()}>
								<i class="fa-solid fa-rotate mr-1"></i>{m.sync()}
							</button>
						</form>
						<form method="POST" action="?/delete" use:enhance>
							<input type="hidden" name="id" value={s.id} />
							<button
								type="button"
								onclick={(e) => confirmDelete(e, s.name)}
								class="btn btn-sm preset-tonal-error"
								aria-label={m.delete()}
								title={m.delete()}><i class="fa-solid fa-trash"></i></button
							>
						</form>
					</div>
				</div>
			{:else}
				<p class="py-2 text-sm text-surface-500">{m.noFrameworkSnapshots()}</p>
			{/each}
		</div>
	</section>
</div>

{#if diff}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
		role="presentation"
		onclick={(e) => {
			if (e.target === e.currentTarget) diff = null;
		}}
	>
		<div class="w-full max-w-lg rounded-2xl bg-surface-50-950 p-6 shadow-xl space-y-4">
			<div class="flex items-center justify-between">
				<h2 class="text-lg font-bold">{m.reviewChanges()}</h2>
				<button
					onclick={() => (diff = null)}
					class="text-surface-400 hover:text-surface-700"
					aria-label={m.close()}
				>
					<i class="fa-solid fa-xmark"></i>
				</button>
			</div>
			<p class="text-sm text-surface-500">{diff.name}</p>
			<table class="w-full text-sm">
				<thead>
					<tr class="border-b border-surface-200-800 text-left text-surface-500">
						<th class="py-1.5 font-medium"></th>
						<th class="py-1.5 text-right font-medium">{m.currentValue()}</th>
						<th class="py-1.5 text-right font-medium">{m.proposedValue()}</th>
						<th class="py-1.5 text-right font-medium">Δ</th>
					</tr>
				</thead>
				<tbody>
					{#each diffRows as row}
						{@const d = delta(row.current, row.next)}
						<tr class="border-b border-surface-100-900">
							<td class="py-1.5">{row.label}</td>
							<td class="py-1.5 text-right text-surface-500">{row.current ?? '—'}</td>
							<td class="py-1.5 text-right font-medium">{row.next ?? '—'}</td>
							<td class="py-1.5 text-right {deltaClass(d)}">{d || '·'}</td>
						</tr>
					{/each}
				</tbody>
			</table>
			<div class="flex justify-end gap-2">
				<button onclick={() => (diff = null)} class="btn btn-sm preset-tonal">{m.cancel()}</button>
				<form method="POST" action="?/sync" use:enhance={applyEnhance}>
					<input type="hidden" name="id" value={diff.id} />
					<button class="btn btn-sm preset-filled-primary-500">
						<i class="fa-solid fa-rotate mr-1"></i>{m.applySync()}
					</button>
				</form>
			</div>
		</div>
	</div>
{/if}

{#if editing}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
		role="presentation"
		onclick={(e) => {
			if (e.target === e.currentTarget) editing = null;
		}}
	>
		<div class="w-full max-w-lg rounded-2xl bg-surface-50-950 p-6 shadow-xl space-y-4">
			<div class="flex items-center justify-between">
				<h2 class="text-lg font-bold">{m.edit()} — {editing.framework_name || editing.name}</h2>
				<button
					onclick={() => (editing = null)}
					class="text-surface-400 hover:text-surface-700"
					aria-label={m.close()}><i class="fa-solid fa-xmark"></i></button
				>
			</div>
			<form method="POST" action="?/update" use:editEnhance class="space-y-3">
				<label class="block text-xs text-surface-500">
					<span class="block">{m.name()}</span>
					<input bind:value={$editData.name} required class="input w-full rounded-md text-sm" />
				</label>
				{#key editing.id}
					<AutocompleteSelect
						form={editSuperform}
						field="implementation_groups"
						multiple
						options={editIgOptions}
						label={m.implementationGroups()}
						helpText={m.implementationGroupsAllHelp()}
					/>
				{/key}
				<label class="block text-xs text-surface-500">
					<span class="block">{m.report()}</span>
					<select bind:value={$editData.display_mode} class="select w-full rounded-md text-sm">
						{#each DISPLAY_MODES as mode}<option value={mode.value}>{mode.label()}</option>{/each}
					</select>
				</label>
				<p class="text-xs text-surface-500">{m.snapshotEditResyncHelp()}</p>
				<div class="flex justify-end gap-2">
					<button type="button" onclick={() => (editing = null)} class="btn btn-sm preset-tonal"
						>{m.cancel()}</button
					>
					<button class="btn btn-sm preset-filled-primary-500">{m.save()}</button>
				</div>
			</form>
		</div>
	</div>
{/if}
