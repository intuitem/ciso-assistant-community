<script lang="ts">
	import { page } from '$app/state';
	import * as m from '$paraglide/messages';
	import { Tabs } from '@skeletonlabs/skeleton-svelte';
	import ClientSettings from './client-settings/+page.svelte';
	import { goto, preloadData, pushState } from '$app/navigation';
	import GeneralSettings from '$lib/components/Settings/GeneralSettings.svelte';
	import SSOSettings from '$lib/components/Settings/SSOSettings.svelte';
	import FeatureFlagsSettings from '$lib/components/Settings/FeatureFlagsSettings.svelte';
	import WebhooksSettings from '$lib/components/Settings/WebhooksSettings.svelte';

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
		if (newValue === 'clientSettings' && !page.state.clientSettings) {
			const href = '/settings/client-settings';
			const result = await preloadData(href);

			if (result.type === 'loaded' && result.status === 200) {
				// Use pushState to update the page store without a full navigation.
				// This keeps the UI fast and responsive.
				pushState(href, { ...page.state, clientSettings: result.data });
			} else {
				// Fallback to a full navigation if preloading fails for any reason.
				goto(href);
			}
		} else {
			const href = `/settings`;
			goto(href);
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
		{#if page.data?.featureflags?.outgoing_webhooks}
			<Tabs.Control value="webhooks"
				><span class="flex flex-row gap-2 items-center ml-0"
					><svg width="20px" height="20px" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
						<title>webhook</title>
						<rect width="24" height="24" fill="none" />
						<path
							d="M10.46,19a4.59,4.59,0,0,1-6.37,1.15,4.63,4.63,0,0,1,2.49-8.38l0,1.43a3.17,3.17,0,0,0-2.36,1.36A3.13,3.13,0,0,0,5,18.91a3.11,3.11,0,0,0,4.31-.84,3.33,3.33,0,0,0,.56-1.44v-1l5.58,0,.07-.11a1.88,1.88,0,1,1,.67,2.59,1.77,1.77,0,0,1-.83-1l-4.07,0A5,5,0,0,1,10.46,19m7.28-7.14a4.55,4.55,0,1,1-1.12,9,4.63,4.63,0,0,1-3.43-2.21L14.43,18a3.22,3.22,0,0,0,2.32,1.45,3.05,3.05,0,1,0,.75-6.06,3.39,3.39,0,0,0-1.53.18l-.85.44L12.54,9.2h-.22a1.88,1.88,0,1,1,.13-3.76A1.93,1.93,0,0,1,14.3,7.39a1.88,1.88,0,0,1-.46,1.15l1.9,3.51a4.75,4.75,0,0,1,2-.19M8.25,9.14A4.54,4.54,0,1,1,16.62,5.6a4.61,4.61,0,0,1-.2,4.07L15.18,9a3.17,3.17,0,0,0,.09-2.73A3.05,3.05,0,1,0,9.65,8.6,3.21,3.21,0,0,0,11,10.11l.39.21-3.07,5a1.09,1.09,0,0,1,.1.19,1.88,1.88,0,1,1-2.56-.83,1.77,1.77,0,0,1,1.23-.17l2.31-3.77A4.41,4.41,0,0,1,8.25,9.14Z"
						/>
					</svg>
					{m.webhooks()}</span
				></Tabs.Control
			>
		{/if}
		<Tabs.Control value="integrations"
			><i class="fa-solid fa-plug"></i> {m.integrations()}</Tabs.Control
		>
		<Tabs.Control value="clientSettings"
			><i class="fa-solid fa-key"></i> {m.clientSettings()}</Tabs.Control
		>
	{/snippet}

	{#snippet content()}
		<Tabs.Panel value="general">
			<GeneralSettings {data} />
		</Tabs.Panel>
		<Tabs.Panel value="sso">
			<SSOSettings {data} />
		</Tabs.Panel>
		<Tabs.Panel value="featureFlags">
			<FeatureFlagsSettings {data} />
		</Tabs.Panel>
		<Tabs.Panel value="webhooks">
			<WebhooksSettings {data} allowMultiple />
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
												{#if page.data.settings?.enabled_integrations?.some((integration: Record<string, any>) => integration.name === 'jira' && integration.configurations?.length)}
													<i class="fa-solid fa-circle-check text-success-600-400"></i>
												{/if}
											</span>
											<span class="flex flex-row space-x-2">
												<h6 class="h6 base-font-color">{m.jira()}</h6>
											</span>
										</div>
									</a>
								</div>
								<div class="card p-4 bg-inherit flex flex-col space-y-3">
									<a class="unstyled" href="/settings/integrations/servicenow">
										<div class="flex flex-col space-y-2 hover:bg-primary-50 card p-4">
											<span class="flex flex-row justify-between text-xl">
												<i class="text-green-700 fa-solid fa-o"></i>
												{#if page.data.settings?.enabled_integrations?.some((integration: Record<string, any>) => integration.name === 'servicenow' && integration.configurations?.length)}
													<i class="fa-solid fa-circle-check text-success-600-400"></i>
												{/if}
											</span>
											<span class="flex flex-row space-x-2">
												<h6 class="h6 base-font-color">{m.serviceNow()}</h6>
											</span>
										</div>
									</a>
								</div>

								<hr />
							</dd>
						</div>
					</dl>
				</div>
			</div></Tabs.Panel
		>
		<Tabs.Panel value="clientSettings" class="p-4">
			{#if page.state.clientSettings}
				<ClientSettings data={page.state.clientSettings} />
			{:else}
				<p>Loading client settings...</p>
			{/if}
		</Tabs.Panel>
	{/snippet}
</Tabs>
