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
		title="Batch Asset Creation"
		desc="Create multiple assets at once from a simple text list"
		link="/experimental/batch-assets"
		tags={['assets', 'bulk']}
	/>
</div>
