<script lang="ts">
	import type { PageData } from './$types';
	import ModelForm from '$lib/components/Forms/ModelForm.svelte';
	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

<div class="card p-4 bg-white shadow-lg">
	<ModelForm
		customNameDescription
		form={data.form}
		object={data.object}
		selectOptions={data.selectOptions}
		model={data.model}
		context="edit"
	/>
</div>
