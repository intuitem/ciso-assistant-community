<script lang="ts">
	import * as m from '$paraglide/messages';

	export let options: any[];
	export let value: string | undefined;
	export let defaultOptionName: string = "--";
	export let optionLabels: { [key: string]: string } = {};
	const hasOptionLabels = Object.keys(optionLabels).length > 0;

	let textInputNode: HTMLElement | null = null;
	let textInputMountedCount: number = 0;
	let inputFocused: boolean = false;

	$: if (textInputNode) {
		textInputMountedCount++;
		if (textInputMountedCount > 1)
			textInputNode.focus();
	}

	let searchText: string = "";
	$: filterApplied = Boolean(value);

	$: searchText = searchText.toLowerCase();
	// Make the search accent insensitive would be even better.
	$: matchingOptionsIndices = options.map(
		(option, optionIndex) => option ?
			[optionIndex, option.toLowerCase().indexOf(searchText)]
				: [null,-1]
	).filter(([_, matchIndex]) => matchIndex >= 0);

	/* if (options.some(x => x === "Domain 1")) { // Code to test the scroll
		for (let i=4;i<50;i++) {
			options.push(`Dom4in ${i}`);
		}
	} */
</script>

<svelte:document on:click={() => {
	searchText = "";
	inputFocused = false;
}}/>

{#if !hasOptionLabels}
	<!-- We should use class="m-0" instead of style="margin: 0;" but i didn't figure out to make tailwind add this class yet -->
	<!-- svelte-ignore a11y-click-events-have-key-events -->
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div class="relative" style="margin: 0;" on:click|stopPropagation>
		{#if !filterApplied}
			<input
				class="input bg-surface-50 max-w-2xl" 
				type="text"
				placeholder="{defaultOptionName} ({options.length})"
				bind:value={searchText}
				bind:this={textInputNode}
				on:focus={() => {inputFocused = true;}}
				on:blur={(event) => { // Add FocusEvent typing
					if (event?.relatedTarget?.tagName !== "BUTTON") {
						inputFocused = false;
					}
				}}
			/>
			{#if inputFocused}
				<div class="absolute z-10 w-max min-w-full left-0 overflow-y-auto max-h-64 border border-black">
					{#if matchingOptionsIndices.length == 0}
						<span class="block w-full py-1 px-0 pointer-events-none text-center border-2 border-black bg-white">{m.noResultFound()}</span>
					{/if}
					{#each matchingOptionsIndices as [optionIndex, matchIndex]}
						{@const option = options[optionIndex]}
						{@const splittedOption = [
							option.substring(0,matchIndex),
							option.substring(matchIndex,matchIndex+searchText.length),
							option.substring(matchIndex+searchText.length)
						]}
						<button
							on:click|stopPropagation={() => {value = option;}}
							class="block border [&:nth-first-child(1)]:border-t-2 [&:nth-last-child(1)]:border-b-2 border-l-2 border-r-2 border-black text-center bg-white py-1 px-2 w-full hover:underline rounded"
						>
							{splittedOption[0]}<b>{splittedOption[1]}</b>{splittedOption[2]}
						</button>
					{/each}
				</div>
			{/if}
		{:else}
			<input type="text" value={value} on:click={() => {
				value = "";
			}}/>
		{/if}
	</div>
{:else}
	<!-- We should use class="m-0" instead of style="margin: 0;" but i didn't figure out to make tailwind add this class yet -->
	{#if options.length > 0}
		<select placeholder="" bind:value style="margin: 0;">
			<option value={null} selected>{defaultOptionName}</option>
			{#each options as option}
				{#if option}
					{@const label = optionLabels[option] ?? option}
					<option value={option}>
						{label}
					</option>
				{/if}
			{/each}
		</select>
	{/if}
{/if}
