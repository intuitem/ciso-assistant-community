<script lang="ts">
	import type { urlModel } from '$lib/utils/types';
	import { m } from '$paraglide/messages';
	import SuperDebug from 'sveltekit-superforms';
	import { getModalStore, type ModalStore } from './stores';
	import { superForm } from 'sveltekit-superforms';

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

	let cascadeInfo: any = $state(null);
	let loading = $state(true);

	async function fetchCascadeInfo() {
		try {
			const response = await fetch(`/fe-api/cascade-info/${URLModel}/${id}`);
			if (response.ok) {
				cascadeInfo = await response.json();
			}
		} catch (error) {
			console.error('Failed to fetch cascade info:', error);
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		fetchCascadeInfo();
	});
</script>

{#if $modalStore[0]}
	<div class="modal-example-form {cBase}">
		<header class={cHeader} data-testid="modal-title">
			{$modalStore[0].title ?? '(title missing)'}
		</header>
		<article>{$modalStore[0].body ?? '(body missing)'}</article>

		{#if loading}
			<div class="flex items-center gap-2 text-sm text-surface-600">
				<span class="animate-spin">⏳</span>
				<span>{m.loading()}</span>
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
						<ul
							class="text-sm space-y-1 text-warning-800 dark:text-warning-200 max-h-48 overflow-y-auto"
						>
							{#each cascadeInfo.related_objects as obj}
								<li class="flex items-center gap-2">
									<span class="text-warning-600">•</span>
									<span class="font-medium">{obj.model}:</span>
									<span>{obj.name}</span>
								</li>
							{/each}
						</ul>
					</div>
				</div>
			</div>
		{/if}

		<form method="POST" action={formAction} use:enhance class="modal-form {cForm}">
			<footer class="modal-footer {parent.regionFooter}">
				<button
					type="button"
					class="btn {parent.buttonNeutral}"
					data-testid="delete-cancel-button"
					onclick={parent.onClose}>{m.cancel()}</button
				>
				<input type="hidden" name="urlmodel" value={URLModel} />
				<input type="hidden" name="id" value={id} />
				<button
					class="btn preset-filled-error-500"
					data-testid="delete-confirm-button"
					type="submit"
					onclick={parent.onClose}>{m.submit()}</button
				>
			</footer>
		</form>
		{#if debug === true}
			<SuperDebug data={$form} />
		{/if}
	</div>
{/if}
