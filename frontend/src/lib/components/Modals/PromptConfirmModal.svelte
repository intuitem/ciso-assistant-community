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

	const cBase = 'card bg-white p-6 w-modal space-y-6';
	const cHeader = 'text-xl font-medium text-gray-900';
	const cForm = 'space-y-4';

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
		<header class={cHeader}>{$modalStore[0].title ?? '(title missing)'}</header>
		<article>{$modalStore[0].body ?? '(body missing)'}</article>

		{#if loading}
			<div class="text-sm text-gray-500">Loading...</div>
		{:else if errorMsg}
			<div class="p-4 bg-red-50 text-red-900 text-sm">
				{errorMsg}
			</div>
		{:else if cascadeInfo}
			{#if cascadeInfo.deleted?.count > 0}
				<div class="p-4 bg-orange-50 border-l-2 border-orange-400">
					<div class="text-sm font-medium text-gray-900 mb-3">
						{m.cascadeDeleteWarning({ count: cascadeInfo.deleted.count })}
					</div>

					<div class="max-h-64 overflow-y-auto space-y-1">
						{#each cascadeInfo.deleted.grouped_objects as group (group.model)}
							<section class="border-t border-gray-200">
								<button
									type="button"
									class="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-gray-50 text-sm"
									aria-controls={`del-${group.model}`}
									aria-expanded={expanded.has(keyFor('deleted', group.model))}
									onclick={() => toggle('deleted', group.model)}
								>
									<span class="font-medium text-gray-900">{group.verbose_name ?? group.model}</span>
									<span class="text-xs text-gray-600">
										{group.objects.length}
									</span>
								</button>

								{#if expanded.has(keyFor('deleted', group.model))}
									<ul id={`del-${group.model}`} class="px-3 pb-2 text-sm space-y-0.5 bg-gray-50">
										{#each group.objects as o (o.id)}
											<li class="flex items-center justify-between py-1">
												<span class="truncate text-gray-700" title={o.name}>{o.name}</span>
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
				<div class="p-4 bg-blue-50 border-l-2 border-blue-400">
					<div class="text-sm font-medium text-gray-900 mb-1">
						{m.cascadeAffectedNotice({ count: cascadeInfo.affected.count })}
					</div>
					<p class="text-xs text-gray-600 mb-3">
						{m.cascadeAffectedHint()}
					</p>

					<div class="max-h-64 overflow-y-auto space-y-1">
						{#each cascadeInfo.affected.grouped_objects as group (group.model)}
							<section class="border-t border-gray-200">
								<button
									type="button"
									class="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-gray-50 text-sm"
									aria-controls={`aff-${group.model}`}
									aria-expanded={expanded.has(keyFor('affected', group.model))}
									onclick={() => toggle('affected', group.model)}
								>
									<span class="font-medium text-gray-900">{group.verbose_name ?? group.model}</span>
									<span class="text-xs text-gray-600">
										{group.objects.length}
									</span>
								</button>

								{#if expanded.has(keyFor('affected', group.model))}
									<ul id={`aff-${group.model}`} class="px-3 pb-2 text-sm space-y-0.5 bg-gray-50">
										{#each group.objects as o (o.id)}
											<li class="flex items-center justify-between py-1">
												<span class="truncate text-gray-700" title={o.name}>{o.name}</span>
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

		<div>
			<p class="text-sm font-medium text-red-600 mb-2">{m.confirmYes()}</p>
			<input
				type="text"
				data-testid="delete-prompt-confirm-textfield"
				bind:value={userInput}
				placeholder={m.confirmYesPlaceHolder()}
				class="w-full px-3 py-2 text-sm border border-surface-300 focus:outline-none focus:ring"
				aria-label={m.confirmYes()}
			/>
		</div>

		{#if sf}
			<form method="POST" action={formAction} use:formEnhance class="modal-form {cForm}">
				<footer class="flex gap-3 justify-end pt-4 border-t border-gray-200">
					<button
						type="button"
						class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50"
						onclick={parent.onClose}
					>
						{m.cancel()}
					</button>
					<input type="hidden" name="urlmodel" value={URLModel} />
					<input type="hidden" name="id" value={id} />
					<button
						class="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
						type="submit"
						data-testid="delete-prompt-confirm-button"
						onclick={parent.onConfirm}
						disabled={!canConfirm}
					>
						{m.submit()}
					</button>
				</footer>
			</form>
			{#if debug === true}
				<SuperDebug data={sf?.form} />
			{/if}
		{:else}
			<footer class="flex gap-3 justify-end pt-4 border-t border-gray-200">
				<button
					type="button"
					class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50"
					onclick={parent.onClose}
				>
					{m.cancel()}
				</button>
				<button
					class="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
					type="button"
					onclick={parent.onConfirm}
					disabled={!canConfirm}
				>
					{m.submit()}
				</button>
			</footer>
		{/if}
	</div>
{/if}
