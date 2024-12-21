<script lang="ts">
	import ModelForm from '$lib/components/Forms/ModelForm.svelte';
	import type { PageData } from './$types';

	export let data: PageData;
</script>

<ModelForm
	form={data.form}
	action="?/updateStakeholder"
	object={data.object}
	selectOptions={data.selectOptions}
	foreignKeys={data.foreignKeys}
	model={data.model}
	context="edit"
/>
