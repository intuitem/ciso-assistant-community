<script lang="ts">
	import ModelForm from '$lib/components/Forms/ModelForm.svelte';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	// NOTE: duplicates `customNameDescription` in crud.ts, which this route ignores.
	// `$derived`, not `const`: this route is shared by every model, so a client-side
	// navigation between two edit pages swaps `data` without remounting.
	const customNameDescription = $derived(
		['operational-scenarios', 'terminologies', 'asset-class', 'quick-form-publications'].includes(
			data.model.urlModel
		)
	);
</script>

<ModelForm
	form={data.form}
	object={data.object}
	selectOptions={data.selectOptions}
	model={data.model}
	{customNameDescription}
	context="edit"
	supportedModels={data.supportedModels}
/>
