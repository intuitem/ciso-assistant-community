<script lang="ts">
	import { page } from '$app/stores';
	import ModelForm from '$lib/components/Forms/ModelForm.svelte';
	import type { PageData } from './$types';

	export let data: PageData;
</script>

{#key data.form}
	<ModelForm
		form={data.form}
		action="?/updateStakeholder&next={$page.url.searchParams.get('next')}"
		object={data.object}
		selectOptions={data.selectOptions}
		foreignKeys={data.foreignKeys}
		model={data.model}
		context="edit"
	/>
{/key}
