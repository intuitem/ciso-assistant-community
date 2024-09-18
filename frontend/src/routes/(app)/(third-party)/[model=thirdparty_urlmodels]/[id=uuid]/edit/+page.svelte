<script lang="ts">
	import type { PageData } from './$types';
	import ModelForm from '$lib/components/Forms/ModelForm.svelte';
	import { breadcrumbObject } from '$lib/utils/stores';

	export let data: PageData;

	breadcrumbObject.set(data.data);
</script>

<ModelForm
	form={data.form}
	object={data.object}
	selectOptions={data.selectOptions}
	foreignKeys={data.foreignKeys}
	model={data.model}
	context="edit"
/>
