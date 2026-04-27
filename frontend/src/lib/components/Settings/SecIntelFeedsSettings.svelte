<script lang="ts">
	import ModelForm from '$lib/components/Forms/ModelForm.svelte';
	import { SecIntelFeedsSchema } from '$lib/utils/schemas';
	import { m } from '$paraglide/messages';

	let { data } = $props();
</script>

<div>
	<span class="text-gray-500 block mb-6">{m.secIntelFeedsDescription()}</span>
	<ModelForm
		form={data.secIntelFeedsForm}
		schema={SecIntelFeedsSchema}
		model={data.secIntelFeedsModel}
		cancelButton={false}
		action="/settings?/secIntelFeeds"
	/>
</div>
