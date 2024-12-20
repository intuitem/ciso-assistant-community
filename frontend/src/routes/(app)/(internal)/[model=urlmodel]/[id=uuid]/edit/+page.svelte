<script lang="ts">
	import ModelForm from '$lib/components/Forms/ModelForm.svelte';
	import type { PageData } from './$types';

	export let data: PageData;

	const customNameDescription = ['operational-scenarios'].includes(data.model.urlModel);
</script>

<ModelForm
	form={data.form}
	object={data.object}
	selectOptions={data.selectOptions}
	foreignKeys={data.foreignKeys}
	model={data.model}
	{customNameDescription}
	context="edit"
/>
