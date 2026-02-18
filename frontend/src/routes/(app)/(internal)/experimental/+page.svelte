<script lang="ts">
	import Article from '$lib/components/DataViz/Article.svelte';
	import { pageTitle } from '$lib/utils/stores';
	import { m } from '$paraglide/messages';

	$pageTitle = 'Experimental';
</script>

<div class="bg-surface-50-950 grid grid-cols-2 p-4 gap-4 card">
	<Article
		title={m.requirementsExplorer()}
		desc={m.visualizeRequirements()}
		link="/requirement-assessments"
		tags={['analysis', 'audit']}
	/>
	<Article
		title={m.findings()}
		desc={m.findingsExplorer()}
		link="/findings"
		tags={['analysis', 'findings']}
	/>
	<Article
		title="Batch Creation"
		desc="Create multiple assets, entities, or feared events at once from a simple text list"
		link="/experimental/batch-create"
		tags={['assets', 'entities', 'ebios-rm', 'bulk']}
	/>
	<Article
		title="Yearly Tasks Review"
		desc="Review all recurrent tasks grouped by folder for yearly planning"
		link="/experimental/yearly-tasks-review"
		tags={['tasks', 'planning', 'review', 'PRO']}
	/>
</div>
