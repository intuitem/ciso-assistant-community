<script lang="ts">
	import type { urlModel } from '$lib/utils/types';
	import { m } from '$paraglide/messages';
	import { onMount } from 'svelte';
	import { superForm } from 'sveltekit-superforms';
	import SuperDebug from 'sveltekit-superforms';
	import type { ComponentType } from 'svelte';
	import { enhance } from '$app/forms';
	import { getModalStore, type ModalStore } from './stores';

	const modalStore: ModalStore = getModalStore();

	const cBase = 'card bg-surface-50-950 p-4 w-fit max-w-4xl shadow-xl space-y-4';
	const cHeaderRow = 'flex items-center justify-between';
	const cHeader = 'text-2xl font-bold whitespace-pre-line';

	const cForm = 'flex flex-col space-y-3';

	interface Props {
		parent: any;
		_form?: any;
		URLModel?: urlModel | '';
		id?: string;
		formAction?: string;
		bodyComponent: ComponentType | undefined;
		bodyProps?: Record<string, unknown>;
		debug?: boolean;
	}

	let {
		parent,
		_form = {},
		URLModel = '',
		id = '',
		formAction = '',
		bodyComponent,
		bodyProps = {},
		debug = false
	}: Props = $props();

	const sf =
		_form && Object.keys(_form).length
			? superForm(_form, { dataType: 'json', id: `confirm-modal-form-${crypto.randomUUID()}` })
			: null;

	const formEnhance = sf ? enhance : undefined;

	let userInput = $state('');
	type Obj = { id: string; name: string };
	type Group = { model: string; verbose_name?: string; objects: Obj[] };
	type Bucket = {
		count: number;
		grouped_objects: Group[];
		related_objects?: Obj[];
		message?: string;
		level?: string;
	};

	let cascadeInfo: { deleted: Bucket; affected: Bucket } | null = $state(null);
	let loading = $state(true);
	let errorMsg = $state<string | null>(null);

	// expand/collapse state per-group (deleted/affected buckets share keys, so prefix)
	let expanded = $state<Set<string>>(new Set());
	function keyFor(bucket: 'deleted' | 'affected', groupKey: string) {
		return `${bucket}:${groupKey}`;
	}
	function toggle(bucket: 'deleted' | 'affected', groupKey: string) {
		const k = keyFor(bucket, groupKey);
		if (expanded.has(k)) expanded.delete(k);
		else expanded.add(k);
		expanded = new Set(expanded); // trigger reactivity
	}

	onMount(async () => {
		if (!URLModel || !id) {
			loading = false;
			return;
		}
		try {
			const res = await fetch(`/fe-api/cascade-info/${URLModel}/${id}`);
			if (!res.ok) throw new Error(`HTTP ${res.status}`);
			cascadeInfo = await res.json();
		} catch (e) {
			errorMsg = m.errorFetching();
			console.error(e);
		} finally {
			loading = false;
		}
	});

	const yes = m.yes().toLowerCase();
	const canConfirm = $derived(!!userInput && userInput.trim().toLowerCase() === yes);
</script>

{#if $modalStore[0]}
	<div class="modal-example-form {cBase}" role="dialog" aria-modal="true">
		<div class={cHeaderRow}>
			<header class={cHeader} data-testid="modal-title">
				{$modalStore[0].title ?? '(title missing)'}
			</header>

			<div
				role="button"
				tabindex="0"
				class="flex items-center hover:text-primary-500 cursor-pointer"
				aria-label="Close"
				onclick={parent.onClose}
				onkeydown={(e) => (e.key === 'Enter' || e.key === ' ') && parent.onClose()}
			>
				<i class="fa-solid fa-xmark"></i>
			</div>
		</div>

		<article class="text-sm text-surface-700-300 whitespace-pre-line">
			{$modalStore[0].body ?? '(body missing)'}
		</article>

		{#if loading}
			<div class="text-sm text-surface-600-400">Loading...</div>
		{:else if errorMsg}
			<div class="p-3 rounded-md bg-red-50 text-red-900 text-sm border border-red-200">
				{errorMsg}
			</div>
		{:else if cascadeInfo}
			{#if cascadeInfo.deleted?.count > 0}
				<div class="p-3 rounded-md bg-orange-50 border border-orange-200 space-y-2">
					<div class="text-sm font-semibold text-surface-950-50">
						{m.cascadeDeleteWarning({ count: cascadeInfo.deleted.count })}
					</div>

					<div class="max-h-64 overflow-y-auto space-y-2">
						{#each cascadeInfo.deleted.grouped_objects as group (group.model)}
							<section
								class="rounded-md border border-surface-300-700 bg-surface-50-950 overflow-hidden"
							>
								<button
									type="button"
									class="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-surface-100-900 text-sm"
									aria-controls={`del-${group.model}`}
									aria-expanded={expanded.has(keyFor('deleted', group.model))}
									onclick={() => toggle('deleted', group.model)}
								>
									<span class="font-medium text-surface-950-50"
										>{group.verbose_name ?? group.model}</span
									>
									<span class="text-xs text-surface-600-400">
										{group.objects.length}
									</span>
								</button>

								{#if expanded.has(keyFor('deleted', group.model))}
									<ul
										id={`del-${group.model}`}
										class="px-3 pb-2 text-sm space-y-1 bg-surface-50-950 border-t border-surface-300-700"
									>
										{#each group.objects as o (o.id)}
											<li class="truncate text-surface-700-300" title={o.name}>
												{o.name}
											</li>
										{/each}
									</ul>
								{/if}
							</section>
						{/each}
					</div>
				</div>
			{/if}

			{#if cascadeInfo.affected?.count > 0}
				<div class="p-3 rounded-md bg-blue-50 border border-blue-200 space-y-2">
					<div class="text-sm font-semibold text-surface-950-50">
						{m.cascadeAffectedNotice({ count: cascadeInfo.affected.count })}
					</div>
					<p class="text-xs text-surface-600-400">
						{m.cascadeAffectedHint()}
					</p>

					<div class="max-h-64 overflow-y-auto space-y-2">
						{#each cascadeInfo.affected.grouped_objects as group (group.model)}
							<section
								class="rounded-md border border-surface-300-700 bg-surface-50-950 overflow-hidden"
							>
								<button
									type="button"
									class="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-surface-100-900 text-sm"
									aria-controls={`aff-${group.model}`}
									aria-expanded={expanded.has(keyFor('affected', group.model))}
									onclick={() => toggle('affected', group.model)}
								>
									<span class="font-medium text-surface-950-50"
										>{group.verbose_name ?? group.model}</span
									>
									<span class="text-xs text-surface-600-400">
										{group.objects.length}
									</span>
								</button>

								{#if expanded.has(keyFor('affected', group.model))}
									<ul
										id={`aff-${group.model}`}
										class="px-3 pb-2 text-sm space-y-1 bg-surface-50-950 border-t border-surface-300-700"
									>
										{#each group.objects as o (o.id)}
											<li class="truncate text-surface-700-300" title={o.name}>
												{o.name}
											</li>
										{/each}
									</ul>
								{/if}
							</section>
						{/each}
					</div>
				</div>
			{/if}
		{/if}

		<div class="space-y-2">
			<p class="text-sm font-medium text-red-600">{m.confirmYes()}</p>
			<input
				type="text"
				data-testid="delete-prompt-confirm-textfield"
				bind:value={userInput}
				placeholder={m.confirmYesPlaceHolder()}
				class="input w-full"
				aria-label={m.confirmYes()}
			/>
		</div>

		{#if sf}
			<form method="POST" action={formAction} use:formEnhance class={cForm}>
				<input type="hidden" name="urlmodel" value={URLModel} />
				<input type="hidden" name="id" value={id} />

				<div class="flex flex-row justify-between space-x-4">
					<button
						type="button"
						class="btn bg-surface-400-600 text-white font-semibold w-full"
						onclick={parent.onClose}
					>
						{m.cancel()}
					</button>

					<button
						type="submit"
						data-testid="delete-prompt-confirm-button"
						class="btn bg-red-600 hover:bg-red-700 text-white font-semibold w-full disabled:opacity-50 disabled:cursor-not-allowed"
						onclick={parent.onConfirm}
						disabled={!canConfirm}
					>
						{m.submit()}
					</button>
				</div>
			</form>

			{#if debug === true}
				<SuperDebug data={sf?.form} />
			{/if}
		{:else}
			<div class="flex flex-row justify-between space-x-4">
				<button
					type="button"
					class="btn bg-surface-400-600 text-white font-semibold w-full"
					onclick={parent.onClose}
				>
					{m.cancel()}
				</button>

				<button
					class="btn bg-red-600 hover:bg-red-700 text-white font-semibold w-full disabled:opacity-50 disabled:cursor-not-allowed"
					type="button"
					onclick={parent.onConfirm}
					disabled={!canConfirm}
				>
					{m.submit()}
				</button>
			</div>
		{/if}
	</div>
{/if}
