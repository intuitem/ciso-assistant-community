<script lang="ts">
	import { getRequirementTitle } from '$lib/utils/helpers';
	import { getOptions } from '$lib/utils/crud';

	export let ref_id: string;
	export let name: string;
	export let description: string;
	export let threats: Record<string, unknown>[];
	export let reference_controls: Record<string, unknown>[];
	export let children: Record<string, unknown>[];
	export let assessable: boolean;

	const node = {
		ref_id,
		name,
		description,
		threats,
		reference_controls,
		children,
		assessable,
		...$$restProps
	} as const;

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

	let showInfo = false;

	$: classesShowInfo = (show: boolean) => (!show ? 'hidden' : '');
	$: classesShowInfoText = (show: boolean) => (show ? 'text-primary-500' : '');
</script>

<div>
	<span class="whitespace-pre-line" style="font-weight: 300;">
		<p class="max-w-[80ch]">
			{#if title}
				<span style="font-weight: 600;">
					{title}
				</span>
				{#if (assessableNodes.length > 1) || (!assessable && assessableNodes.length > 0)}
					<span class="badge variant-soft-primary">
						{assessableNodes.length}
					</span>
				{/if}
			{/if}
			{#if description}
				{description}
			{/if}
		</p>
	</span>
	{#if (threats && threats.length > 0) || (reference_controls && reference_controls.length > 0)}
		<div
			role="button"
			tabindex="0"
			class="underline text-sm hover:text-primary-400 {classesShowInfoText(showInfo)}"
			on:click={(e) => {
				e.preventDefault();
				showInfo = !showInfo;
			}}
			on:keydown={(e) => {
				if (e.key === 'Enter') {
					e.preventDefault();
					showInfo = !showInfo;
				}
			}}
		>
			<i class="text-xs fa-solid fa-info-circle" /> Learn more
		</div>
		<div
			class="card p-2 variant-ghost-primary text-sm flex flex-row cursor-auto {classesShowInfo(
				showInfo
			)}"
		>
			<div class="flex-1">
				<p class="font-medium">
					<i class="fa-solid fa-gears" />
					Suggested reference controls
				</p>
				{#if reference_controls.length === 0}
					<p>--</p>
				{:else}
					<ul class="list-disc ml-4">
						{#each getOptions( { objects: reference_controls, extra_fields: [['folder', 'str']], label: 'auto' } ) as func}
							// convention for automatic label calculation
							<li>
								<p>{func.label}</p>
							</li>
						{/each}
					</ul>
				{/if}
			</div>
			<div class="flex-1">
				<p class="font-medium">
					<i class="fa-solid fa-gears" />
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
