<script lang="ts">
	import { goto, preloadData, pushState } from '$app/navigation';
	import { page } from '$app/stores';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import * as m from '$paraglide/messages';
	import { TreeView, TreeViewItem } from '@skeletonlabs/skeleton';
	import AuditTableMode from '../../../(third-party)/compliance-assessments/[id=uuid]/table-mode/+page.svelte';
	import type { PageData, Actions } from './$types';

	export let data: PageData;
	export let form: Actions;

	import { breadcrumbObject } from '$lib/utils/stores';
	breadcrumbObject.set(data.data);

	const mailing = Boolean(data.data.compliance_assessment) && Boolean(data.data.authors.length);
</script>

<div class="flex flex-col space-y-4 whitespace-pre-line">
	<DetailView
		{data}
		{mailing}
		exclude={['criticality', 'penetration', 'dependency', 'maturity', 'trust']}
	/>
	{#if data.data.compliance_assessment}
		<div class="card px-6 py-4 bg-white flex flex-row justify-between shadow-lg w-full">
			<TreeView>
				<TreeViewItem
					on:toggle={async (e) => {
						e.preventDefault();
						const href = `/compliance-assessments/${data.data.compliance_assessment.id}/table-mode`;
						const result = await preloadData(href);
						if (result.type === 'loaded' && result.status === 200) {
							pushState('', { auditTableMode: result.data });
						} else {
							// Something went wrong, try navigating
							goto(href);
						}
					}}
				>
					<span class="font-semibold text-lg select-none">{m.questionnaire()}</span>
					<svelte:fragment slot="children">
						{#if Object.hasOwn($page.state, 'auditTableMode')}
							<div class="max-h-[48rem] overflow-y-scroll">
								<AuditTableMode
									{form}
									data={$page.state.auditTableMode}
									actionPath={`/compliance-assessments/${data.data.compliance_assessment.id}/table-mode`}
									shallow
									questionnaireOnly
									invalidateAll={false}
								/>
							</div>
						{/if}
					</svelte:fragment>
				</TreeViewItem>
			</TreeView>
		</div>
	{/if}
</div>
