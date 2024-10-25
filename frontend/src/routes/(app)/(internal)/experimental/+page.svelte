<script lang="ts">
	import Article from '$lib/components/DataViz/Article.svelte';
</script>

<div class="bg-white grid p-8 grid-cols-2 space-x-8">
	<Article
		title="Controls Graph"
		desc="Visualize dependencies and the impact of controls"
		link="experimental/graph"
		tags={['priority', 'controls']}
	></Article>
	<Article
		title="Controls Timeline"
		desc="Visualize applied controls as a timeline if start date and ETA are provided"
		link="experimental/timeline"
		tags={['schedule', 'controls']}
	/>
</div>
