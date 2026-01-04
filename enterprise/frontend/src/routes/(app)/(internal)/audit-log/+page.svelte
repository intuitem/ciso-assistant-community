<script lang="ts">
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';

	const ACTION_FILTER = {
		component: AutocompleteSelect,
		props: {
			label: 'action',
			options: [
				{ label: 'create', value: '0' },
				{ label: 'update', value: '1' },
				{ label: 'delete', value: '2' },
				{ label: 'access', value: '3' },
				{ label: 'loginFailed', value: '4' }
			],
			multiple: true
		}
	};
	const CONTENT_TYPE_FILTER = {
		component: AutocompleteSelect,
		props: {
			label: 'content_type',
			optionsEndpoint: 'content-types',
			optionsLabelField: 'label',
			optionsValueField: 'value',
			multiple: true
		}
	};
</script>

<main class="bg-white card p-4">
	<ModelTable
		source={{
			head: {
				actor: 'actor',
				action: 'action',
				content_type: 'content_type',
				timestamp: 'timestamp',
				folder: 'folder'
			},
			body: [],
			meta: [],
			filters: {
				action: ACTION_FILTER,
				content_type: CONTENT_TYPE_FILTER
			}
		}}
		URLModel="audit-log"
		baseEndpoint="/audit-log"
		fields={['actor', 'action', 'content_type', 'timestamp', 'folder']}
		thFilter={true}
		thFilterFields={['actor', 'folder']}
	/>
</main>
