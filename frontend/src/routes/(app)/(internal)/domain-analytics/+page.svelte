<script lang="ts">
	import type { PageData } from './$types';
	export let data: PageData;
	import TreeView from './TreeView.svelte';
	const tree = {
		name: 'USA',
		uuid: 'abc',
		children: [
			{
				name: 'Florida',
				uuid: 'xyz',
				children: [
					{ name: 'Jacksonville' },
					{
						name: 'Orlando',
						children: [
							{ name: 'Disney World', uuid: 'toto' },
							{ name: 'Universal Studio' },
							{ name: 'Sea World' }
						]
					},
					{ name: 'Miami' }
				]
			},
			{
				name: 'California',
				children: [{ name: 'San Francisco' }, { name: 'Los Angeles' }, { name: 'Sacramento' }]
			}
		]
	};
</script>

{JSON.stringify(data.data, null, 2)}
<main class="bg-white card p-4">
	<TreeView tree={data.data} />
</main>
