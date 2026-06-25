<script lang="ts">
	import { enhance } from '$app/forms';
	import { m } from '$paraglide/messages';
	import { getModalStore, type ModalSettings } from '$lib/components/Modals/stores';
	import { getToastStore } from '$lib/components/Toast/stores';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
	const modalStore = getModalStore();
	const toast = getToastStore();

	const toastEnhance =
		() =>
		async ({ result, update }: { result: { type: string }; update: () => Promise<void> }) => {
			await update();
			if (result.type === 'success')
				toast.trigger({ message: m.saved(), background: 'preset-filled-success-500' });
		};

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
		<form
			method="POST"
			action="?/create"
			use:enhance={toastEnhance}
			class="flex flex-wrap items-end gap-3"
		>
			<label class="text-xs text-surface-500">
				<span class="block">{m.name()}</span>
				<input name="name" required class="input rounded-md text-sm" />
			</label>
			<label class="text-xs text-surface-500">
				<span class="block">{m.audit()}</span>
				<select name="source_audit" required class="select rounded-md text-sm">
					<option value="">—</option>
					{#each data.audits as a}<option value={a.id}>{a.name}</option>{/each}
				</select>
			</label>
			<label class="text-xs text-surface-500">
				<span class="block">{m.domain()}</span>
				<select name="folder" class="select rounded-md text-sm">
					{#each data.folders as f}<option value={f.id}>{f.name}</option>{/each}
				</select>
			</label>
			<label class="text-xs text-surface-500">
				<span class="block">{m.implementationGroups()}</span>
				<input
					name="implementation_groups"
					placeholder={m.implementationGroupsPlaceholder()}
					class="input rounded-md text-sm"
				/>
			</label>
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
					{#each METRICS as metric}
						{@const d = delta(diff.current[metric.key], diff.next[metric.key])}
						<tr class="border-b border-surface-100-900">
							<td class="py-1.5">{metric.label()}</td>
							<td class="py-1.5 text-right text-surface-500">{diff.current[metric.key] ?? '—'}</td>
							<td class="py-1.5 text-right font-medium">{diff.next[metric.key] ?? '—'}</td>
							<td
								class="py-1.5 text-right {d.startsWith('+')
									? 'text-success-600'
									: d.startsWith('-')
										? 'text-error-600'
										: 'text-surface-400'}">{d || '·'}</td
							>
						</tr>
					{/each}
					{@const dc = delta(diff.controlsCurrent, diff.controlsNext)}
					<tr>
						<td class="py-1.5">{m.controlsCovered()}</td>
						<td class="py-1.5 text-right text-surface-500">{diff.controlsCurrent}</td>
						<td class="py-1.5 text-right font-medium">{diff.controlsNext}</td>
						<td
							class="py-1.5 text-right {dc.startsWith('+')
								? 'text-success-600'
								: dc.startsWith('-')
									? 'text-error-600'
									: 'text-surface-400'}">{dc || '·'}</td
						>
					</tr>
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
