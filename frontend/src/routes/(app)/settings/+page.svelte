<script lang="ts">
	import ModelForm from '$lib/components/Forms/ModelForm.svelte';
	import { getModelInfo } from '$lib/utils/crud';
	import { IdentityProviderSchema } from '$lib/utils/schemas';

	export let data;
</script>

<ModelForm
	form={data.form}
	schema={IdentityProviderSchema}
	model={getModelInfo('identity-providers')}
/>
