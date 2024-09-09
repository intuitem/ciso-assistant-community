<script lang="ts">
	import type { PageData } from './$types';

	export let data: PageData;

	import { breadcrumbObject } from '$lib/utils/stores';
	breadcrumbObject.set(data.data);

	import AuditTableMode from '../../compliance-assessments/[id=uuid]/table-mode/+page.svelte';
	import { TreeView, TreeViewItem } from '@skeletonlabs/skeleton';

	import { page } from '$app/stores';
	import { goto, preloadData, pushState } from '$app/navigation';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
</script>

<div class="flex flex-col space-y-4 whitespace-pre-line">
	<DetailView
		{data}
		exclude={['criticality', 'penetration', 'dependency', 'maturity', 'trust', 'evidence']}
	/>
	<div class="card px-6 py-4 bg-white flex flex-row justify-between shadow-lg w-full">
		<TreeView>
			<TreeViewItem
				on:toggle={async (e) => {
					e.preventDefault();
					const href = `/compliance-assessments/${data.data.compliance_assessment.id}/table-mode`;
					const result = await preloadData(href);
					if (result.type === 'loaded' && result.status === 200) {
						pushState(href, { auditTableMode: result.data });
					} else {
						// Something went wrong, try navigating
						goto(href);
					}
				}}
				>(audit table mode)
				<svelte:fragment slot="children">
					{#if Object.hasOwn($page.state, 'auditTableMode')}
						<AuditTableMode data={$page.state.auditTableMode} />
					{/if}
				</svelte:fragment>
			</TreeViewItem>
		</TreeView>
	</div>
</div>
