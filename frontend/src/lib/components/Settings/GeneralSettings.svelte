<script lang="ts">
	import ModelForm from '$lib/components/Forms/ModelForm.svelte';
	import { GeneralSettingsSchema } from '$lib/utils/schemas';
	import { m } from '$paraglide/messages';

	let { data } = $props();
</script>

<div>
	<span class="text-surface-600-400 block mb-6">{m.generalSettingsDescription()}</span>
	<ModelForm
		form={data.generalSettingForm}
		schema={GeneralSettingsSchema}
		model={data.generalSettingModel}
		cancelButton={false}
		action="/settings?/general"
	/>
</div>
