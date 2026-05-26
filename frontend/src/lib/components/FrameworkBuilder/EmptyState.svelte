<script lang="ts">
	import { get } from 'svelte/store';
	import { getBuilderContext } from './builder-state';
	import { m } from '$paraglide/messages';

	const builder = getBuilderContext();

	function seedFlat() {
		// Three top-level assessable requirements.
		for (let i = 0; i < 3; i++) {
			builder.addNode({ parent: null, preset: 'requirement' });
		}
	}

	function seedGrouped() {
		// One non-assessable section containing three assessable requirements.
		builder.addNode({ parent: null, preset: 'group' });
		const group = get(builder.rootNodes)[0].node.id;
		for (let i = 0; i < 3; i++) {
			builder.addNode({ parent: group, preset: 'requirement' });
		}
	}

	function seedHierarchy() {
		// One non-assessable top-level group, one non-assessable mid-level group,
		// two assessable leaves at the deepest level.
		builder.addNode({ parent: null, preset: 'group' });
		const top = get(builder.rootNodes)[0].node.id;
		builder.addNode({ parent: top, preset: 'group' });
		const mid = get(builder.rootNodes)[0].children[0].node.id;
		builder.addNode({ parent: mid, preset: 'requirement' });
		builder.addNode({ parent: mid, preset: 'requirement' });
	}

	function seedBlank() {
		builder.addNode({ parent: null, preset: 'blank' });
	}
</script>

<div class="max-w-3xl mx-auto py-16 px-6">
	<h2 class="text-xl font-semibold text-gray-800 mb-2">
		{m.builderEmptyStateTitle()}
	</h2>
	<p class="text-sm text-gray-500 mb-8">
		{m.builderEmptyStateSubtitle()}
	</p>

	<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
		<button
			type="button"
			class="text-left p-4 border border-gray-200 rounded-lg bg-white hover:border-blue-400 hover:shadow-sm transition"
			onclick={seedFlat}
		>
			<div class="text-3xl mb-2 text-gray-400">≡</div>
			<div class="text-sm font-medium text-gray-800">{m.builderEmptyFlat()}</div>
			<p class="text-xs text-gray-500 mt-1">
				{m.builderEmptyFlatHint()}
			</p>
		</button>

		<button
			type="button"
			class="text-left p-4 border border-gray-200 rounded-lg bg-white hover:border-blue-400 hover:shadow-sm transition"
			onclick={seedGrouped}
		>
			<div class="text-3xl mb-2 text-gray-400">□</div>
			<div class="text-sm font-medium text-gray-800">{m.builderEmptyGrouped()}</div>
			<p class="text-xs text-gray-500 mt-1">
				{m.builderEmptyGroupedHint()}
			</p>
		</button>

		<button
			type="button"
			class="text-left p-4 border border-gray-200 rounded-lg bg-white hover:border-blue-400 hover:shadow-sm transition"
			onclick={seedHierarchy}
		>
			<div class="text-3xl mb-2 text-gray-400">▼</div>
			<div class="text-sm font-medium text-gray-800">{m.builderEmptyHierarchy()}</div>
			<p class="text-xs text-gray-500 mt-1">
				{m.builderEmptyHierarchyHint()}
			</p>
		</button>

		<button
			type="button"
			class="text-left p-4 border border-gray-200 rounded-lg bg-white hover:border-gray-400 hover:shadow-sm transition"
			onclick={seedBlank}
		>
			<div class="text-3xl mb-2 text-gray-400">○</div>
			<div class="text-sm font-medium text-gray-800">{m.builderEmptyBlank()}</div>
			<p class="text-xs text-gray-500 mt-1">{m.builderEmptyBlankHint()}</p>
		</button>
	</div>
</div>
