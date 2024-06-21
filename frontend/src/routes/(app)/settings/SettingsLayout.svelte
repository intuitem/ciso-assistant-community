<script>
	import { TabGroup, Tab } from '@skeletonlabs/skeleton';
	import * as m from '$paraglide/messages';

	let tabSet = 0;
</script>

<div class="card bg-white shadow-lg p-4">
	<TabGroup active="bg-primary-100 text-primary-800 border-b border-primary-800">
		<Tab bind:group={tabSet} name="ssoSettings" value={0}><i class="fa-solid fa-key"></i> {m.sso()}</Tab>
	</TabGroup>
	{#if tabSet === 0}
		<slot name="sso" />
	{/if}
</div>
