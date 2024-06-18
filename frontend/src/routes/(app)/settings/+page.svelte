<script lang="ts">
	import ModelForm from '$lib/components/Forms/ModelForm.svelte';
	import { IdentityProviderSchema } from '$lib/utils/schemas';

	export let data;
</script>

<ModelForm form={data.form} schema={IdentityProviderSchema} model={data.model} />
