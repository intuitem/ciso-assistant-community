<script lang="ts">
	import Article from '$lib/components/DataViz/Article.svelte';
	import { pageTitle } from '$lib/utils/stores';
	import { m } from '$paraglide/messages';

	$pageTitle = 'Experimental';
</script>

<div class="bg-white grid grid-cols-2 p-4 gap-4">
	<Article
		title={m.frameworksMapping()}
		desc={m.visualizeAppliedMapping()}
		link="/experimental/mapping"
		tags={['analysis', 'mapping']}
	/>
	<Article
		title={m.assetsExplorer()}
		desc={m.visualizeAssetsRelationships()}
		link="/assets/graph"
		tags={['analysis', 'assets']}
	/>
	<Article
		title={m.requirementsExplorer()}
		desc={m.visualizeRequirements()}
		link="/requirement-assessments"
		tags={['analysis', 'assets']}
	/>
</div>
