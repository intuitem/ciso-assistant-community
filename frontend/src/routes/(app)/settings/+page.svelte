<script lang="ts">
	import ModelForm from '$lib/components/Forms/ModelForm.svelte';
	import { IdentityProviderSchema } from '$lib/utils/schemas';
	import * as m from '$paraglide/messages';
	import { TabGroup, Tab } from '@skeletonlabs/skeleton';

	let tabSet = 0;

	export let data;
</script>

<TabGroup active="bg-primary-100 text-primary-800 border-b border-primary-800">
	<Tab bind:group={tabSet} name="ssoSettings" value={0}><i class="fa-solid fa-key" /> {m.sso()}</Tab
	>
</TabGroup>
{#if tabSet === 0}
	<div>
		<span class="text-gray-500">{m.ssoSettingsDescription()}</span>
		<ModelForm
			form={data.form}
			schema={IdentityProviderSchema}
			model={data.model}
			cancelButton={false}
		/>
	</div>
{/if}
