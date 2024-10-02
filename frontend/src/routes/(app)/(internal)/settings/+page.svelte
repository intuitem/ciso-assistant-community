<script lang="ts">
	import ModelForm from '$lib/components/Forms/ModelForm.svelte';
	import * as m from '$paraglide/messages';
	import { TabGroup, Tab } from '@skeletonlabs/skeleton';

	let tabSet = 0;

	export let data;
</script>

<div class="card bg-white shadow flex">
	<TabGroup active="bg-primary-100 text-primary-800 border-b border-primary-800">
		<Tab bind:group={tabSet} name="ssoSettings" value={0}
			><i class="fa-solid fa-key" /> {m.sso()}</Tab
		>
	</TabGroup>
	<TabGroup active="bg-primary-100 text-primary-800 border-b border-primary-800">
		<Tab bind:group={tabSet} name="ssoSettings" value={1}
			><i class="fa-solid fa-cog" /> {m.generalSettings()}</Tab
		>
	</TabGroup>
</div>
{#if tabSet === 0}
	<div>
		<span class="text-gray-500">{m.ssoSettingsDescription()}</span>
		<ModelForm form={data.ssoForm} model={data.ssoModel} cancelButton={false} action="?/sso" />
	</div>
{:else if tabSet === 1}
	<div>
		<span class="text-gray-500">{m.ssoSettingsDescription()}</span>
		<ModelForm
			form={data.generalSettingForm}
			model={data.generalSettingModel}
			cancelButton={false}
			action="?/general"
		/>
	</div>
{/if}
