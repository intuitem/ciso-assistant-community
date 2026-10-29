<script lang="ts">
	import ModelForm from '$lib/components/Forms/ModelForm.svelte';
	import { RateLimitingSchema } from '$lib/utils/schemas';
	import { m } from '$paraglide/messages';

	let { data } = $props();
</script>

<div>
	<span class="text-surface-600-400 block mb-6">{m.rateLimitingDescription()}</span>
	<ModelForm
		form={data.rateLimitingForm}
		schema={RateLimitingSchema}
		model={data.rateLimitingModel}
		cancelButton={false}
		action="/settings?/rateLimiting"
	/>
</div>
