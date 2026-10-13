<script lang="ts">
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import type { TableSource } from '$lib/components/ModelTable/types';
	import { tableSourceMapper } from '$lib/utils/table';
	import { m } from '$paraglide/messages';

	// Every DPIA, whatever form it was filled from: responses whose form records
	// the processing's DPIA when accepted.
	const head = {
		ref_id: 'refId',
		name: 'name',
		subject: 'processing',
		quick_form: 'quickForm',
		status: 'status',
		resolution: 'resolution',
		updated_at: 'updatedAt',
		folder: 'domain'
	};
	const source: TableSource = {
		head,
		body: tableSourceMapper([], Object.keys(head)),
		meta: []
	};
</script>

<div class="flex flex-col gap-4 bg-surface-50-950 p-4 shadow-sm rounded-lg">
	<div>
		<p class="text-xl font-extrabold">{m.dpias()}</p>
		<p class="text-sm text-surface-600-400">{m.dpiasListHelpText()}</p>
	</div>
	<ModelTable
		URLModel="quick-form-responses"
		{source}
		search={true}
		rowsPerPage={true}
		orderBy={{ identifier: 'updated_at', direction: 'desc' }}
		baseEndpoint="/quick-form-responses?target=processing.dpia"
		fields={Object.keys(head)}
	/>
</div>
