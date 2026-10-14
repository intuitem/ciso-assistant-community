<script lang="ts">
	// A new computed metric, in a modal: from the list, a selection, or an
	// instance's page. Its formula is edited later in a drawer beside it.
	import { goto } from '$app/navigation';
	import ComposeMetricEditor, {
		type Saved
	} from '$lib/components/Metrology/ComposeMetricEditor.svelte';
	import { getModalStore, type ModalStore } from './stores';

	interface Props {
		parent: any;
		instanceIds?: string[];
	}

	let { parent, instanceIds = [] }: Props = $props();
	const modalStore: ModalStore = getModalStore();

	async function created(saved: Saved) {
		modalStore.close();
		await goto(`/metric-instances/${saved.id}`);
	}
</script>

{#if $modalStore[0]}
	<ComposeMetricEditor {instanceIds} onClose={parent.onClose} onSaved={created} />
{/if}
