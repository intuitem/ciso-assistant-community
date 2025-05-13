<script lang="ts">
	import { page } from '$app/stores';
	import ModelForm from '$lib/components/Forms/ModelForm.svelte';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

{#key data.form}
	<ModelForm
		form={data.form}
		action="?/updateStakeholder&next={$page.url.searchParams.get('next')}"
		object={data.object}
		selectOptions={data.selectOptions}
		model={data.model}
		context="edit"
	/>
{/key}
