<script lang="ts">
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
  import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';

  const ACTOR_FILTER = {
    component: AutocompleteSelect,
    props: {
      label: 'actor',
      optionsEndpoint: 'users',
      optionsLabelField: 'email',
      multiple: true
    }
  }
  const ACTION_FILTER = {
    component: AutocompleteSelect,
    props: {
      label: 'action',
      options: [
        { label: 'Create', value: '0' },
        { label: 'Update', value: '1' },
        { label: 'Delete', value: '2' },
        { label: 'Access', value: '3' }
      ],
      multiple: true
    }
  }
  const DOMAIN_FILTER = {
    component: AutocompleteSelect,
    props: {
      optionsEndpoint: 'folders',
      label: 'folder',
      multiple: true,
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
        "actor": ACTOR_FILTER,
        "action": ACTION_FILTER,
      },
		}}
		URLModel="audit-log"
		baseEndpoint="/audit-log"
		fields={['actor', 'action', 'content_type', 'timestamp', 'folder']}
	/>
</main>
