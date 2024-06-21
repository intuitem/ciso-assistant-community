<script lang="ts">
	import ModelForm from '$lib/components/Forms/ModelForm.svelte';
	import { IdentityProviderSchema } from '$lib/utils/schemas';
	import SettingsLayout from './SettingsLayout.svelte';
	import * as m from '$paraglide/messages';

	export let data;
</script>

<SettingsLayout>
	<div class="p-4" slot="sso">
		<span class="text-gray-500">{m.ssoSettingsDescription()}</span>
		<ModelForm
			form={data.form}
			schema={IdentityProviderSchema}
			model={data.model}
			cancelButton={false}
		/>
	</div>
</SettingsLayout>
