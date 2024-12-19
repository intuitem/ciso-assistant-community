<script lang="ts">
	import type { PageData } from './$types';
	import ModelForm from '$lib/components/Forms/ModelForm.svelte';
	export let data: PageData;
</script>

<div class="card p-4 bg-white shadow-lg">
	<ModelForm
		customNameDescription
		form={data.form}
		object={data.object}
		selectOptions={data.selectOptions}
		foreignKeys={data.foreignKeys}
		model={data.model}
		context="ebiosRmStudy"
	/>
</div>
