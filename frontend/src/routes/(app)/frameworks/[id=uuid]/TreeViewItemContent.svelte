<script lang="ts">
	export let name: string;
	export let description: string;
	export let leaf_content: string;
	export let threats: Record<string, unknown>[];
	export let reference_controls: Record<string, unknown>[];
	export let children: Record<string, unknown>[];

	const content: string = leaf_content
		? leaf_content
		: description
		? `${name} ${description}`
		: name;

	let showInfo = false;

	$: classesShowInfo = (show: boolean) => (!show ? 'hidden' : '');
	$: classesShowInfoText = (show: boolean) => (show ? 'text-primary-500' : '');

	$: hasChildren = children && Object.keys(children).length > 0;
</script>

<div>
	<span class="whitespace-pre-line" style="font-weight: {hasChildren ? 600 : 300};">
		<p class="max-w-[65ch]">
			{content}
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
						{#each reference_controls as func}
							<li>
								{#if func.id}
									<a class="anchor" href="/reference-controls/{func.id}">
										{func.name}
									</a>
								{:else}
									<p>{func.name}</p>
								{/if}
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
