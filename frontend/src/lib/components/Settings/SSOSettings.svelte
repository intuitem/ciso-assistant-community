<script lang="ts">
	import ModelForm from '#lib/components/Forms/ModelForm.svelte';
	import { SSOSettingsSchema } from '#lib/utils/schemas.js';
	import { m } from '#paraglide/messages.js';

	let { data } = $props();
</script>

<div>
	<span class="text-surface-600-400 block mb-6">{m.ssoSettingsDescription()}</span>
	<ModelForm
		form={data.ssoForm}
		schema={SSOSettingsSchema}
		model={data.ssoModel}
		cancelButton={false}
		action="/settings?/sso"
	/>
</div>
