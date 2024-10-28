<script lang="ts">
	import ModelForm from '$lib/components/Forms/ModelForm.svelte';
	import { SSOSettingsSchema, globalSettingsSchema } from '$lib/utils/schemas';
	import * as m from '$paraglide/messages';
	import { TabGroup, Tab } from '@skeletonlabs/skeleton';

	let tabSet = 0;

	export let data;
</script>

<TabGroup active="bg-primary-100 text-primary-800 border-b border-primary-800">
	<Tab bind:group={tabSet} name="instanceSettings" value={1}><i class="fa-solid fa-globe"></i> {m.global()}</Tab>
	<Tab bind:group={tabSet} name="ssoSettings" value={0}><i class="fa-solid fa-key" /> {m.sso()}</Tab
	>
</TabGroup>
{#if tabSet === 0}
	<div>
		<span class="text-gray-500">{m.ssoSettingsDescription()}</span>
		<ModelForm
			form={data.ssoForm}
			schema={SSOSettingsSchema}
			model={data.ssoModel}
			cancelButton={false}
		/>
	</div>
{:else if tabSet === 1}
<div>
	<span class="text-gray-500">{m.globalSettingsDescription()}</span>
	<!-- <ModelForm
		form={data.form}
		schema={globalSettingsSchema}
		model={data.model}
		cancelButton={false}
	/> -->
</div>
{/if}
