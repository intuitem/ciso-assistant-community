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

	const cBase = 'card bg-surface-50 p-4 w-modal shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';
	const cForm = 'p-4 space-y-4 rounded-container';

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
	type Group = { model: string; verbose_name?: string; objects: { id: string; name: string }[] };
	let cascadeInfo: {
		count: number;
		grouped_objects: Group[];
		second_order_info?: string[];
	} | null = $state(null);
	let loading = $state(true);
	let errorMsg = $state<string | null>(null);

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
			<div class="space-y-2" aria-busy="true">
				<div class="h-4 w-2/3 animate-pulse bg-surface-200 rounded"></div>
				<div class="h-3 w-full animate-pulse bg-surface-200 rounded"></div>
			</div>
		{:else if errorMsg}
			<div class="p-3 bg-error-50 border-l-3 border-error-500 rounded-md text-error-800">
				{errorMsg}
			</div>
		{:else if cascadeInfo && cascadeInfo.count > 0}
			<div
				class="p-3 bg-warning-50 dark:bg-warning-950/30 border-l-3 border-warning-500 rounded-md"
			>
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

				<div class="max-h-56 overflow-y-auto pr-1 space-y-2">
					{#each cascadeInfo.grouped_objects as group (group.model)}
						<details class="border rounded-md">
							<summary class="px-3 py-2 cursor-pointer hover:bg-surface-100">
								<span class="font-medium">{group.verbose_name ?? group.model}</span>
								<span class="ml-2 text-xs px-2 py-0.5 rounded-full bg-warning-100 text-warning-800">
									{group.objects.length}
								</span>
							</summary>
							<ul class="px-3 pb-2 text-sm space-y-1">
								{#each group.objects as o (o.id)}
									<li class="flex items-center gap-2">
										<span class="text-warning-600">•</span>
										<span class="truncate" title={o.name}>{o.name}</span>
									</li>
								{/each}
							</ul>
						</details>
					{/each}
				</div>
			</div>
		{/if}

		<p class="text-error-600 font-semibold mt-2">{m.confirmYes()}</p>
		<input
			type="text"
			data-testid="delete-prompt-confirm-textfield"
			bind:value={userInput}
			placeholder={m.confirmYesPlaceHolder()}
			class="w-full mt-2 p-2 border border-surface-300 rounded-sm focus:outline-none focus:ring"
			aria-label={m.confirmYes()}
		/>

		{#if sf}
			<form method="POST" action={formAction} use:formEnhance class="modal-form {cForm}">
				<footer class="modal-footer {parent.regionFooter}">
					<button type="button" class="btn {parent.buttonNeutral}" onclick={parent.onClose}>
						{m.cancel()}
					</button>
					<input type="hidden" name="urlmodel" value={URLModel} />
					<input type="hidden" name="id" value={id} />
					<button
						class="btn preset-filled-error-500"
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
			<footer class="modal-footer {parent.regionFooter}">
				<button type="button" class="btn {parent.buttonNeutral}" onclick={parent.onClose}>
					{m.cancel()}
				</button>
				<button
					class="btn preset-filled-error-500"
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
