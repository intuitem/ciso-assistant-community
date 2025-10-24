<script lang="ts">
	import ModelForm from '$lib/components/Forms/ModelForm.svelte';
	import { SSOSettingsSchema, GeneralSettingsSchema, FeatureFlagsSchema } from '$lib/utils/schemas';
	import { m } from '$paraglide/messages';
	import { Tabs } from '@skeletonlabs/skeleton-svelte';

	let group = $state('integrations');

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
		<Tabs.Control value="integrations"
			><i class="fa-solid fa-plug"></i> {m.integrations()}</Tabs.Control
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
		<Tabs.Panel value="integrations">
			<div>
				<span class="text-gray-500">{m.configureIntegrations()}</span>
				<div class="flow-root">
					<dl class="divide-y divide-surface-100 text-sm">
						<div class="grid grid-cols-1 gap-1 py-3 sm:grid-cols-3 sm:gap-4">
							<dt class="font-medium">{m.itsm()}</dt>
							<dd class="text-surface-900 sm:col-span-2">
								<div class="card p-4 bg-inherit flex flex-col space-y-3">
									<a class="unstyled" href="/settings/integrations/jira">
										<div class="flex flex-col space-y-2 hover:bg-primary-50 card p-4">
											<span class="flex flex-row justify-between text-xl">
												<i class="text-blue-700 fab fa-jira"></i>
												<i class="fa-solid fa-circle-check text-success-600-400"></i>
											</span>
											<span class="flex flex-row space-x-2">
												<h6 class="h6 base-font-color">{m.jira()}</h6>
											</span>
											<!-- <p class="text-sm text-surface-800 max-w-[50ch]"> -->
											<!-- 	{m.authenticatorAppDescription()} -->
											<!-- </p> -->
										</div>
									</a>
									<!-- <div class="flex flex-wrap justify-between gap-2"> -->
									<!-- 	<button class="btn preset-outlined-surface-500 w-fit">{m.disableTOTP()}</button> -->
									<!-- </div> -->
								</div>
								<hr />
							</dd>
						</div>
					</dl>
				</div>
			</div></Tabs.Panel
		>
	{/snippet}
</Tabs>
