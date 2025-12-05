<script lang="ts">
	import Article from '$lib/components/DataViz/Article.svelte';
	import { pageTitle } from '$lib/utils/stores';
	import { m } from '$paraglide/messages';

	$pageTitle = 'Experimental';
</script>

<div class="bg-white grid grid-cols-2 p-4 gap-4">
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
	<Article
		title="Gantt Diagram"
		desc="Visualize applied controls on a timeline with milestones, tasks, and control implementations"
		link="/experimental/gantt"
		tags={['visualization', 'timeline', 'controls', 'planning']}
  />

</div>
