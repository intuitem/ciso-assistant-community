<script lang="ts">
	import type { PageData, ActionData } from './$types';
	import DetailView from '#lib/components/DetailView/DetailView.svelte';
	import MergeDefinitionModal from '#lib/components/Modals/MergeDefinitionModal.svelte';
	import { getModalStore } from '#lib/components/Modals/stores.js';
	import { m } from '#paraglide/messages.js';

	interface Props {
		data: PageData;
		form: ActionData;
	}
	let { data, form }: Props = $props();
	const definition = $derived(data.data);
	const modalStore = getModalStore();

	// A definition from a library or with a formula stays as it is: only
	// one somebody defined by hand can be merged away.
	const mergeable = $derived(!!definition?.id && !definition?.library && !definition?.is_derived);
	function openMerge() {
		modalStore.trigger({
			type: 'component',
			component: { ref: MergeDefinitionModal, props: { definition } }
		});
	}
</script>

<DetailView {data} {form}>
	{#snippet actions()}
		{#if mergeable}
			<button
				type="button"
				class="btn preset-tonal-primary h-fit"
				onclick={openMerge}
				data-testid="merge-definition-button"
			>
				<i class="fa-solid fa-code-merge mr-2" aria-hidden="true"></i>{m.mergeDefinitionAction()}
			</button>
		{/if}
	{/snippet}
</DetailView>
