<script lang="ts">
	import Article from '$lib/components/DataViz/Article.svelte';
	import { pageTitle } from '$lib/utils/stores';
	import { m } from '$paraglide/messages';

	$pageTitle = 'Experimental';
</script>

<div class="bg-white grid grid-cols-2 p-4 gap-4 card">
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
		title={m.matrixEditor()}
		desc={m.matrixEditorDescription()}
		link="/experimental/matrix-editor"
		tags={['risk', 'matrix', 'editor']}
	/>
	<Article
		title="Framework Builder"
		desc="Create and edit compliance frameworks with a visual builder"
		link="/experimental/framework-builder"
		tags={['frameworks', 'builder', 'editor']}
	/>
	<Article
		title="Preset Editor"
		desc="Author presets — scaffolds and steps. Create from scratch or fork a library preset."
		link="/experimental/preset-editor"
		tags={['presets', 'journey', 'editor']}
	/>
</div>
