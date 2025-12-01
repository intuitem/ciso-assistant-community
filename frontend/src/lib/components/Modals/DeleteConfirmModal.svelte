<script lang="ts">
	import type { urlModel } from '$lib/utils/types';
	import { m } from '$paraglide/messages';
	import SuperDebug from 'sveltekit-superforms';
	import { getModalStore, type ModalStore } from './stores';
	import { superForm } from 'sveltekit-superforms';
	import { onMount } from 'svelte';

	const modalStore: ModalStore = getModalStore();

	const cBase = 'card bg-surface-50 p-4 w-modal shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';
	const cForm = 'p-4 space-y-4 rounded-container';

	interface Props {
		parent: any;
		_form: any;
		URLModel: urlModel;
		formAction?: string;
		invalidateAll?: boolean;
		id: string;
		debug?: boolean;
	}

	let {
		parent,
		_form,
		URLModel,
		formAction = '?/delete',
		invalidateAll = true,
		id,
		debug = false
	}: Props = $props();

	const { form, enhance } = superForm(_form, { invalidateAll });

	type Group = { model: string; verbose_name?: string; objects: { id: string; name: string }[] };
	let cascadeInfo: {
		count: number;
		grouped_objects: Group[];
		second_order_info?: string[];
	} | null = $state(null);
	let loading = $state(true);
	let errorMsg = $state<string | null>(null);

	let expanded = $state<Set<string>>(new Set());

	function toggle(key: string) {
		if (expanded.has(key)) expanded.delete(key);
		else expanded.add(key);
		expanded = new Set(expanded); // trigger reactivity
	}

	onMount(async () => {
		try {
			const res = await fetch(`/fe-api/cascade-info/${URLModel}/${id}`);
			if (!res.ok) throw new Error(`HTTP ${res.status}`);
			cascadeInfo = await res.json();
			// Auto-expand small groups
			cascadeInfo.grouped_objects?.forEach((g) => {
				if (g.objects.length <= 5) expanded.add(g.model);
			});
			expanded = new Set(expanded);
		} catch (e) {
			errorMsg = m.errorFetching();
			console.error(e);
		} finally {
			loading = false;
		}
	});
</script>

{#if $modalStore[0]}
	<div
		class="modal-example-form {cBase}"
		role="dialog"
		aria-modal="true"
		aria-labelledby="modal-title"
	>
		<header id="modal-title" class={cHeader} data-testid="modal-title">
			{$modalStore[0].title ?? '(title missing)'}
		</header>
		<article>{$modalStore[0].body ?? '(body missing)'}</article>

		{#if loading}
			<!-- Skeleton -->
			<div class="space-y-2" aria-busy="true">
				<div class="h-4 w-2/3 animate-pulse bg-surface-200 rounded"></div>
				<div class="h-3 w-full animate-pulse bg-surface-200 rounded"></div>
				<div class="h-3 w-5/6 animate-pulse bg-surface-200 rounded"></div>
			</div>
		{:else if errorMsg}
			<div class="p-3 bg-error-50 border-l-3 border-error-500 rounded-md text-error-800">
				{errorMsg}
			</div>
		{:else if cascadeInfo && cascadeInfo.count > 0}
			<div
				class="p-3 bg-warning-50 dark:bg-warning-950/30 border-l-3 border-warning-500 rounded-md"
			>
				<div class="flex items-start gap-2">
					<svg
						class="w-5 h-5 text-warning-600 dark:text-warning-400 flex-shrink-0 mt-0.5"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
						aria-hidden="true"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
						></path>
					</svg>
					<div class="flex-1">
						<div class="font-semibold text-warning-900 dark:text-warning-100 mb-2">
							{m.cascadeDeleteWarning({ count: cascadeInfo.count })}
						</div>
						{#if cascadeInfo.second_order_info}
							<ul class="mb-3 text-sm text-warning-900 dark:text-warning-200 list-disc list-inside">
								{#each cascadeInfo.second_order_info as info}
									<li>{info}</li>
								{/each}
							</ul>
						{/if}
						<!-- Grouped accordion -->
						<div class="max-h-64 overflow-y-auto pr-1 space-y-2">
							{#each cascadeInfo.grouped_objects as group (group.model)}
								<section class="border rounded-md">
									<button
										type="button"
										class="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-surface-100 focus:outline-none focus:ring"
										aria-controls={`grp-${group.model}`}
										aria-expanded={expanded.has(group.model)}
										on:click={() => toggle(group.model)}
									>
										<span class="font-medium">
											{group.verbose_name ?? group.model}
										</span>
										<span
											class="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-warning-100 text-warning-800"
										>
											{group.objects.length}
										</span>
									</button>

									{#if expanded.has(group.model)}
										<ul id={`grp-${group.model}`} class="px-3 pb-2 text-sm space-y-1">
											{#each group.objects as o (o.id)}
												<li class="flex items-center gap-2">
													<span class="text-warning-600">•</span>
													<span class="truncate" title={o.name}>{o.name}</span>
												</li>
											{/each}
										</ul>
									{/if}
								</section>
							{/each}
						</div>
					</div>
				</div>
			</div>
		{:else}
			<div class="p-3 bg-surface-100 rounded-md text-surface-700">
				{m.nothingToDelete()}
			</div>
		{/if}

		<form method="POST" action={formAction} use:enhance class="modal-form {cForm}">
			<footer class="modal-footer {parent.regionFooter}">
				<button
					type="button"
					class="btn {parent.buttonNeutral}"
					data-testid="delete-cancel-button"
					on:click={parent.onClose}
				>
					{m.cancel()}
				</button>
				<input type="hidden" name="urlmodel" value={URLModel} />
				<input type="hidden" name="id" value={id} />
				<button
					class="btn preset-filled-error-500"
					data-testid="delete-confirm-button"
					type="submit"
					on:click={parent.onClose}
				>
					{m.submit()}
				</button>
			</footer>
		</form>

		{#if debug === true}
			<SuperDebug data={$form} />
		{/if}
	</div>
{/if}
