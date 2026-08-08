<script lang="ts">
	import type { PageData } from './$types';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { deserialize, enhance } from '$app/forms';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { m } from '$paraglide/messages';
	import { postureResultTailwindColorMap } from '$lib/utils/constants';
	import { getModalStore, type ModalStore } from '$lib/components/Modals/stores';
	import { getToastStore } from '$lib/components/Toast/stores';
	import PromptConfirmModal from '$lib/components/Modals/PromptConfirmModal.svelte';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const modalStore: ModalStore = getModalStore();
	const toastStore = getToastStore();

	function toastError(message: string) {
		toastStore.trigger({ message, background: 'preset-filled-error-500' });
	}

	function confirmDeleteRun() {
		modalStore.trigger({
			type: 'component',
			title: m.deleteRun(),
			body: m.deleteRunConfirm({ count: data.run.checks }),
			component: { ref: PromptConfirmModal, props: { bodyComponent: undefined } },
			response: async (confirmed: boolean) => {
				if (!confirmed) return;
				const res = await fetch(`?/deleteRun`, {
					method: 'POST',
					body: new FormData(),
					headers: { 'x-sveltekit-action': 'true' }
				});
				const result = deserialize(await res.text());
				if (result.type === 'redirect') {
					goto(result.location);
				} else if (result.type === 'failure') {
					toastError((result.data as any)?.error ?? m.error());
				}
			}
		});
	}

	const RESULT_ORDER = ['pass', 'fail', 'error', 'not_applicable', 'not_checked'];
	const resultLabels: Record<string, string> = {
		pass: m.pass(),
		fail: m.fail(),
		not_applicable: m.notApplicable(),
		error: m.error(),
		not_checked: m.notChecked()
	};

	const byAsset = $derived.by(() => {
		const groups = new Map<string, { name: string; rows: any[] }>();
		for (const row of data.results) {
			const group = groups.get(row.asset.id) ?? { name: row.asset.str, rows: [] };
			group.rows.push(row);
			groups.set(row.asset.id, group);
		}
		return [...groups.entries()].map(([id, group]) => ({ id, ...group }));
	});

	function submitOnChange(event: Event) {
		const el = event.currentTarget as HTMLSelectElement | HTMLInputElement;
		if (el instanceof HTMLSelectElement && !el.value) return;
		el.form?.requestSubmit();
	}
</script>

<div class="flex flex-col space-y-4">
	<div class="card p-4 bg-surface-50-950 shadow-xs flex items-center gap-4 flex-wrap">
		<Anchor
			href="/posture-assessments/{page.params.id}"
			class="anchor whitespace-nowrap"
			label={data.assessment.name}
		>
			<i class="fa-solid fa-arrow-left mr-2"></i>{data.assessment.name}
		</Anchor>
		<h3 class="text-lg font-semibold grow">{m.runDetail()}</h3>
		<div class="flex items-center gap-4 text-sm text-surface-600-400 flex-wrap">
			<span
				><i class="fa-solid fa-calendar mr-1"></i>
				{new Date(data.run.started_at).toLocaleString()}</span
			>
			<span><i class="fa-solid fa-wrench mr-1"></i>{data.run.tool || '--'}</span>
			<span class="badge preset-tonal-secondary">{data.run.source}</span>
			<span class="text-green-600 dark:text-green-400">{m.pass()}: {data.run.passed}</span>
			<span class={data.run.failed ? 'text-red-600 dark:text-red-400' : ''}>
				{m.fail()}: {data.run.failed}
			</span>
			<button
				type="button"
				class="btn btn-sm preset-tonal text-red-600 dark:text-red-400"
				onclick={confirmDeleteRun}
				data-testid="delete-run"
			>
				<i class="fa-solid fa-trash mr-1"></i>{m.deleteRun()}
			</button>
		</div>
	</div>

	<div class="card p-4 bg-surface-50-950 shadow-xs space-y-3">
		<form
			method="POST"
			action="?/updateRun"
			enctype="multipart/form-data"
			use:enhance={() =>
				async ({ result, update }) => {
					if (result.type === 'failure') {
						toastError((result.data as any)?.error ?? m.error());
					} else if (result.type === 'success') {
						toastStore.trigger({
							message: m.saved(),
							background: 'preset-filled-success-500'
						});
					}
					await update();
				}}
			class="space-y-3"
		>
			<div>
				<label class="text-sm font-semibold" for="run-observation">{m.runObservation()}</label>
				<textarea
					id="run-observation"
					name="observation"
					class="textarea w-full mt-1"
					rows="2"
					value={data.run.observation ?? ''}></textarea>
			</div>
			<div class="flex items-center gap-3 flex-wrap">
				{#if data.run.attachment}
					<a href="{page.url.pathname}/attachment" class="anchor text-sm" download>
						<i class="fa-solid fa-paperclip mr-1"></i>{data.run.attachment}
					</a>
					<label class="text-sm flex items-center gap-1 cursor-pointer">
						<input type="checkbox" name="remove_attachment" value="true" class="checkbox" />
						{m.removeAttachment()}
					</label>
				{/if}
				<label class="text-sm flex items-center gap-2">
					<i class="fa-solid fa-paperclip"></i>{data.run.attachment
						? m.replaceAttachment()
						: m.attachment()}
					<input type="file" name="attachment" class="input text-sm py-1" />
				</label>
				<button type="submit" class="btn btn-sm preset-filled-primary-500 ml-auto">
					<i class="fa-solid fa-floppy-disk mr-1"></i>{m.save()}
				</button>
			</div>
		</form>
	</div>

	<p class="text-sm text-surface-600-400 px-2">{m.runEditHelp()}</p>

	{#each byAsset as group (group.id)}
		<div class="card p-4 bg-surface-50-950 shadow-xs space-y-2">
			<div class="flex items-center justify-between">
				<h4 class="font-semibold">{group.name}</h4>
				<Anchor
					href="/posture-assessments/{page.params.id}/runs/new?from={page.params
						.rid}&asset={group.id}"
					class="btn btn-sm preset-filled-primary-500"
					label={m.cloneAsNewRun()}
				>
					<i class="fa-solid fa-copy mr-1"></i>{m.cloneAsNewRun()}
				</Anchor>
			</div>
			<div class="space-y-0.5">
				{#each group.rows as row (row.id)}
					<div class="flex items-center gap-2 px-2 py-1 rounded hover:bg-surface-100-900">
						<span class="font-medium whitespace-nowrap">{row.requirement.ref_id}</span>
						<span class="grow truncate text-surface-700-300" title={row.requirement.name}>
							{row.requirement.name ?? ''}
						</span>
						{#if row.actual || row.expected}
							<span
								class="text-xs text-surface-500 truncate max-w-64"
								title={[row.actual, row.expected].filter(Boolean).join(' — ')}
							>
								{row.actual || row.expected}
							</span>
						{/if}
						<span
							class="inline-block w-2.5 h-2.5 rounded-sm shrink-0 {postureResultTailwindColorMap[
								row.result
							]}"
						></span>
						<form
							method="POST"
							action="?/setResult"
							use:enhance={() =>
								async ({ result, update }) => {
									if (result.type === 'failure') {
										toastError((result.data as any)?.error ?? m.error());
									}
									await update();
								}}
							class="flex items-center gap-2"
						>
							<input type="hidden" name="ref_id" value={row.requirement.ref_id} />
							<input type="hidden" name="asset" value={group.id} />
							<input type="hidden" name="actual" value={row.actual ?? ''} />
							<input type="hidden" name="expected" value={row.expected ?? ''} />
							<input
								type="text"
								name="message"
								class="input w-56 py-0.5 text-sm"
								placeholder={m.comment()}
								value={row.message ?? ''}
								aria-label="{row.requirement.ref_id} — {m.comment()}"
								onchange={submitOnChange}
							/>
							<select
								name="result"
								class="select w-36 py-0.5 text-sm"
								value={row.result}
								aria-label="{row.requirement.ref_id} — {m.result()}"
								onchange={submitOnChange}
							>
								{#each RESULT_ORDER as key}
									<option value={key}>{resultLabels[key]}</option>
								{/each}
							</select>
						</form>
					</div>
				{/each}
			</div>
		</div>
	{/each}
</div>
