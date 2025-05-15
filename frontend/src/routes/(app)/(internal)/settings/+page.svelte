<script lang="ts">
	import ModelForm from '$lib/components/Forms/ModelForm.svelte';
	import { SSOSettingsSchema, GeneralSettingsSchema, FeatureFlagsSchema } from '$lib/utils/schemas';
	import { m } from '$paraglide/messages';
	import { Tabs } from '@skeletonlabs/skeleton-svelte';

	let group = $state('instance');

	let { data } = $props();
</script>

<Tabs
	value={group}
	onValueChange={(e) => {
		group = e.value;
	}}
	active="bg-primary-100 text-primary-800 border-b border-primary-800"
>
	{#snippet list()}
		<Tabs.Control value="instance"><i class="fa-solid fa-globe"></i> {m.general()}</Tabs.Control>
		<Tabs.Control value="sso"><i class="fa-solid fa-key"></i> {m.sso()}</Tabs.Control>
		<Tabs.Control value="featureFlags"
			><i class="fa-solid fa-flag"></i> {m.featureFlags()}</Tabs.Control
		>
	{/snippet}
	{#snippet content()}
		<Tabs.Panel value="instance">
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
		<Tabs.Panel value="sso">
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
		<Tabs.Panel value="featureFlags">
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
	{/snippet}
</Tabs>
