<script lang="ts">
	import { page } from '$app/stores';
	import ModelForm from '$lib/components/Forms/ModelForm.svelte';
	import { SSOSettingsSchema, GeneralSettingsSchema } from '$lib/utils/schemas';
	import * as m from '$paraglide/messages';
	import { Tab, TabGroup } from '@skeletonlabs/skeleton';
	import ClientSettings from './client-settings/+page.svelte';
	import { goto, preloadData, pushState } from '$app/navigation';

	let tabSet = 0;

	export let data;
</script>

<TabGroup active="bg-primary-100 text-primary-800 border-b border-primary-800">
	<Tab bind:group={tabSet} name="instanceSettings" value={0}
		><i class="fa-solid fa-globe"></i> {m.general()}</Tab
	>
	<Tab bind:group={tabSet} name="ssoSettings" value={1}><i class="fa-solid fa-key" /> {m.sso()}</Tab
	>
	<Tab
		bind:group={tabSet}
		name="clientSettings"
		value={2}
		on:change={async (e) => {
			e.preventDefault();
			const href = '/settings/client-settings';
			const result = await preloadData(href);
			if (result.type === 'loaded' && result.status === 200) {
				pushState('', { clientSettings: result.data });
			} else {
				// Something went wrong, try navigating
				goto(href);
			}
		}}><i class="fa-solid fa-key" /> {m.clientSettings()}</Tab
	>
</TabGroup>
{#if tabSet === 1}
	<div>
		<span class="text-gray-500">{m.ssoSettingsDescription()}</span>
		<ModelForm
			form={data.ssoForm}
			schema={SSOSettingsSchema}
			model={data.ssoModel}
			cancelButton={false}
			action="?/sso"
		/>
	</div>
{:else if tabSet === 0}
	<div>
		<span class="text-gray-500">{m.generalSettingsDescription()}</span>
		<ModelForm
			form={data.generalSettingForm}
			schema={GeneralSettingsSchema}
			model={data.generalSettingModel}
			cancelButton={false}
			action="?/general"
		/>
	</div>
{:else if tabSet === 2}
	<ClientSettings data={$page.state.clientSettings} />
{/if}
