<script lang="ts">
	import ModelForm from '$lib/components/Forms/ModelForm.svelte';
	import { SSOSettingsSchema } from '$lib/utils/schemas';
	import { m } from '$paraglide/messages';

	let { data } = $props();
</script>

<div>
	<span class="text-gray-500 block mb-6">{m.ssoSettingsDescription()}</span>
	<ModelForm
		form={data.ssoForm}
		schema={SSOSettingsSchema}
		model={data.ssoModel}
		cancelButton={false}
		action="/settings?/sso"
	/>
</div>
