<script lang="ts">
	import { getRequirementTitle } from '$lib/utils/helpers';
	import { getOptions } from '$lib/utils/crud';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';

	interface Props {
		ref_id: string;
		name: string;
		description: string;
		threats?: Record<string, unknown>[];
		reference_controls?: Record<string, unknown>[];
		children: Record<string, unknown>[];
		assessable: boolean;
		questions?: Record<string, { text: string }>;
		[key: string]: any;
	}

	let {
		ref_id,
		name,
		description,
		threats = [],
		reference_controls = [],
		children,
		assessable,
		questions = {},
		...rest
	}: Props = $props();

	const node = {
		ref_id,
		name,
		description,
		threats,
		reference_controls,
		children,
		assessable,
		questions,
		...rest
	};

	type TreeViewItemNode = typeof node;

	const getAssessableNodes = (
		startNode: TreeViewItemNode,
		assessableNodes: TreeViewItemNode[] = []
	) => {
		if (startNode.assessable) assessableNodes.push(startNode);
		if (startNode.children) {
			for (const value of Object.values(startNode.children) as TreeViewItemNode[]) {
				getAssessableNodes(value, assessableNodes);
			}
		}
		return assessableNodes;
	};

	const assessableNodes = getAssessableNodes(node);

	const title: string = getRequirementTitle(ref_id, name);

	let showInfo = $state(false);

	let classesShowInfo = $derived((show: boolean) => (!show ? 'hidden' : ''));
	let classesShowInfoText = $derived((show: boolean) => (show ? 'text-primary-500' : ''));
</script>

<div>
	<span class="whitespace-pre-line" style="font-weight: 300;">
		<span class="max-w-[80ch]">
			{#if title || description}
				{#if title}
					<span style="font-weight: 600;">{title}</span>
				{/if}
				{#if description}
					<MarkdownRenderer content={description} />
				{/if}
			{:else if node?.questions && Object.keys(node.questions).length > 0}
				<!-- This displays the first question's text -->
				{Object.entries(node?.questions)[0][1].text}
			{/if}
		</span>
	</span>
	{#if (threats && threats.length > 0) || (reference_controls && reference_controls.length > 0)}
		<div
			role="button"
			tabindex="0"
			class="underline text-sm hover:text-primary-400 {classesShowInfoText(showInfo)}"
			onclick={(e) => {
				e.preventDefault();
				showInfo = !showInfo;
			}}
			onkeydown={(e) => {
				if (e.key === 'Enter') {
					e.preventDefault();
					showInfo = !showInfo;
				}
			}}
		>
			<i class="text-xs fa-solid fa-info-circle"></i> Learn more
		</div>
		<div
			class="card p-2 preset-tonal-primary border border-primary-500 text-sm flex flex-row cursor-auto {classesShowInfo(
				showInfo
			)}"
		>
			<div class="flex-1">
				<p class="font-medium">
					<i class="fa-solid fa-gears"></i>
					Suggested reference controls
				</p>
				{#if reference_controls.length === 0}
					<p>--</p>
				{:else}
					<ul class="list-disc ml-4">
						{#each getOptions( { objects: reference_controls, extra_fields: [['folder', 'str']], label: 'auto' } ) as func}
							<li>
								<p>{func.label}</p>
							</li>
						{/each}
					</ul>
				{/if}
			</div>
			<div class="flex-1">
				<p class="font-medium">
					<i class="fa-solid fa-gears"></i>
					Threats covered
				</p>
				{#if threats.length === 0}
					<p>--</p>
				{:else}
					<ul class="list-disc ml-4">
						{#each threats as threat}
							<li>
								{#if threat.id}
									<a class="anchor" href="/threats/{threat.id}">
										{threat.name}
									</a>
								{:else}
									<p>{threat.name}</p>
								{/if}
							</li>
						{/each}
					</ul>
				{/if}
			</div>
		</div>
	{/if}
</div>
