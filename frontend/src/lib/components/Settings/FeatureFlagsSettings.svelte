<script lang="ts">
	import ModelForm from '$lib/components/Forms/ModelForm.svelte';
	import { FeatureFlagsSchema } from '$lib/utils/schemas';
	import { m } from '$paraglide/messages';

	let { data } = $props();
</script>

<div>
	<span class="text-surface-600-400 block mb-6">{m.configureFeatureFlags()}</span>
	<ModelForm
		form={data.featureFlagForm}
		schema={FeatureFlagsSchema}
		model={data.featureFlagModel}
		cancelButton={false}
		action="/settings?/featureFlags"
	/>
</div>
