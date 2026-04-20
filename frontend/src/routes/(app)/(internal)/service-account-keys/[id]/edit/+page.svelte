<script lang="ts">
	import ModelForm from '$lib/components/Forms/ModelForm.svelte';
	import { ServiceAccountKeyUpdateSchema } from '$lib/utils/schemas';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

<div class="card bg-white shadow-sm p-4">
	<ModelForm form={data.form} schema={ServiceAccountKeyUpdateSchema} model={data.model} />
</div>
