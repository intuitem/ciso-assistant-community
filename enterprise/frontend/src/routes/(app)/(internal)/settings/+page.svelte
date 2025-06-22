<script lang="ts">
	import { page } from '$app/stores';
	import ModelForm from '$lib/components/Forms/ModelForm.svelte';
	import { SSOSettingsSchema, GeneralSettingsSchema, FeatureFlagsSchema } from '$lib/utils/schemas';
	import * as m from '$paraglide/messages';
	import { Tabs } from '@skeletonlabs/skeleton-svelte';
	import ClientSettings from './client-settings/+page.svelte';
	import { goto, preloadData, pushState } from '$app/navigation';

	// Use string-based state for the active tab for better readability and maintenance.
	// Defaulting to 'general' which corresponds to the original tabSet = 0.
	let group = $state('general');

	let { data } = $props();

	// Centralized handler for tab changes.
	async function handleTabChange(newValue: string) {
		group = newValue;

		// Preserve the special data-loading logic for the Client Settings tab.
		// This now triggers when the tab with value 'clientSettings' is selected.
		// We also check if data already exists to prevent redundant network requests.
		if (newValue === 'clientSettings' && !$page.state.clientSettings) {
			const href = '/settings/client-settings';
			const result = await preloadData(href);

			if (result.type === 'loaded' && result.status === 200) {
				// Use pushState to update the $page store without a full navigation.
				// This keeps the UI fast and responsive.
				pushState(href, { ...$page.state, clientSettings: result.data });
			} else {
				// Fallback to a full navigation if preloading fails for any reason.
				goto(href);
			}
		}
	}
</script>

<Tabs
	value={group}
	onValueChange={(e) => handleTabChange(e.value)}
	active="bg-primary-100 text-primary-800 border-b border-primary-800"
>
	{#snippet list()}
		<Tabs.Control value="general"><i class="fa-solid fa-globe"></i> {m.general()}</Tabs.Control>
		<Tabs.Control value="sso"><i class="fa-solid fa-key"></i> {m.sso()}</Tabs.Control>
		<Tabs.Control value="featureFlags"
			><i class="fa-solid fa-flag"></i> {m.featureFlags()}</Tabs.Control
		>
		<Tabs.Control value="clientSettings"
			><i class="fa-solid fa-key"></i> {m.clientSettings()}</Tabs.Control
		>
	{/snippet}

	{#snippet content()}
		<Tabs.Panel value="general" class="p-4">
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
		</Tabs.Panel>
		<Tabs.Panel value="sso" class="p-4">
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
		</Tabs.Panel>
		<Tabs.Panel value="featureFlags" class="p-4">
			<div>
				<span class="text-gray-500">{m.configureFeatureFlags()}</span>
				<ModelForm
					form={data.featureFlagForm}
					schema={FeatureFlagsSchema}
					model={data.featureFlagModel}
					cancelButton={false}
					action="?/featureFlags"
				/>
			</div>
		</Tabs.Panel>
		<Tabs.Panel value="clientSettings" class="p-4">
			{#if $page.state.clientSettings}
				<ClientSettings data={$page.state.clientSettings} />
			{:else}
				<p>Loading client settings...</p>
			{/if}
		</Tabs.Panel>
	{/snippet}
</Tabs>
