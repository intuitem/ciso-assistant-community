<script lang="ts">
	import type { urlModel } from '$lib/utils/types';

	// Props
	/** Exposes parent props to this component. */
	export let parent: any;

	// Stores
	import { getModalStore } from '@skeletonlabs/skeleton';
	import type { ModalStore } from '@skeletonlabs/skeleton';

	import * as m from '$paraglide/messages';
	import { Accordion, AccordionItem } from '@skeletonlabs/skeleton';
	import { safeTranslate } from '$lib/utils/i18n';
	const modalStore: ModalStore = getModalStore();

	export let _form = {};
	export let URLModel: urlModel | '' = '';
	export let id: string = '';
	export let formAction: string;
	export let bodyComponent: ComponentType | undefined;
	export let bodyProps: Record<string, unknown> = {};

	import { superForm } from 'sveltekit-superforms';

	import SuperForm from '$lib/components/Forms/Form.svelte';

	const { form } = superForm(_form, {
		dataType: 'json',
		id: `confirm-modal-form-${crypto.randomUUID()}`
	});

	// Base Classes
	const cBase = 'card p-4 w-modal shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';
	const cForm = 'p-4 space-y-4 rounded-container-token';

	import SuperDebug from 'sveltekit-superforms';
	import type { ComponentType } from 'svelte';
	export let debug = false;

	export let outOfScopeObjects: Record<string, Array<{ name: string; description?: string }>> = {};
</script>

{#if $modalStore[0]}
	<div class="modal-example-form {cBase}">
		<header class={cHeader}>{$modalStore[0].title ?? '(title missing)'}</header>
		<article class="max-h-[60vh] overflow-y-auto">
			{#if bodyComponent}
				<div class="prose prose-sm dark:prose-invert max-w-none">
					<svelte:component this={bodyComponent} {...bodyProps} />
				</div>
			{:else}
				<div class="prose prose-sm dark:prose-invert max-w-none whitespace-pre-line">
					{$modalStore[0].body ?? '(body missing)'}
				</div>
			{/if}
			<div class="card p-4 bg-surface-100-800-token mt-4">
				<h3 class="font-semibold text-lg mb-4">{m.detailedListOfOutOfScopeObjects()}</h3>
				<Accordion>
					{#each Object.entries(outOfScopeObjects) as [type, objects]}
						<AccordionItem>
							<div slot="summary" class="flex items-center gap-2">
								<span class="font-medium">{safeTranslate(type)}</span>
								<span class="badge variant-filled-warning">{objects.length}</span>
							</div>
							<div slot="content">
								<ul class="list-disc pl-6 space-y-1">
									{#each objects as obj}
										<li>
											<span class="font-medium">{obj.name}</span>
											{#if obj.description}
												<span class="text-surface-600-400-token">({obj.description})</span>
											{/if}
										</li>
									{/each}
								</ul>
							</div>
						</AccordionItem>
					{/each}
				</Accordion>
			</div>
		</article>
		<!-- Enable for debugging: -->
		<SuperForm dataType="json" action={formAction} data={_form} class="modal-form {cForm}">
			<!-- prettier-ignore -->
			<footer class="modal-footer {parent.regionFooter}">
				<button type="button" class="btn {parent.buttonNeutral}" on:click={parent.onClose}>{m.cancel()}</button>
				<input type="hidden" name="urlmodel" value={URLModel} />
				<input type="hidden" name="id" value={id} />
				<button class="btn variant-filled-error" type="submit" on:click={parent.onConfirm}>{m.submit()}</button>
			</footer>
		</SuperForm>
		{#if debug === true}
			<SuperDebug data={$form} />
		{/if}
	</div>
{/if}
