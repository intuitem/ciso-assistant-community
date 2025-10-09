<script lang="ts">
	import { m } from '$paraglide/messages';
	import type { PageData } from './$types';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import { page } from '$app/stores';
	import { safeTranslate } from '$lib/utils/i18n';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	// Filter applied controls that have name or description
	const appliedControls = data.applied_controls.filter(
		(control) => control.name || control.description
	);

	let currentIndex = $state(0);
	let currentAppliedControl = $derived(appliedControls[currentIndex]);

	// Static options like compliance assessment flash mode
	const statusOptions = [
		{ id: '--', label: '--' },
		{ id: 'to_do', label: m.toDo() },
		{ id: 'in_progress', label: m.inProgress() },
		{ id: 'on_hold', label: m.onHold() },
		{ id: 'active', label: m.active() },
		{ id: 'deprecated', label: m.deprecated() }
	];

	const effortOptions = [
		{ id: '--', label: '--', dbValue: null },
		{ id: 'Extra Small', label: m.extraSmall(), dbValue: 'XS' },
		{ id: 'Small', label: m.small(), dbValue: 'S' },
		{ id: 'Medium', label: m.medium(), dbValue: 'M' },
		{ id: 'Large', label: m.large(), dbValue: 'L' },
		{ id: 'Extra Large', label: 'Extra Large', dbValue: 'XL' }
	];

	const priorityOptions = [
		{ id: '--', label: '--', dbValue: null },
		{ id: 'P1', label: m.p1(), dbValue: 1 },
		{ id: 'P2', label: m.p2(), dbValue: 2 },
		{ id: 'P3', label: m.p3(), dbValue: 3 },
		{ id: 'P4', label: 'P4', dbValue: 4 }
	];

	const impactOptions = [
		{ id: '--', label: '--', dbValue: null },
		{ id: 'Very Low', label: m.veryLow(), dbValue: 1 },
		{ id: 'Low', label: m.low(), dbValue: 2 },
		{ id: 'Medium', label: m.medium(), dbValue: 3 },
		{ id: 'High', label: m.high(), dbValue: 4 },
		{ id: 'Very High', label: m.veryHigh(), dbValue: 5 }
	];

	const csfFunctionOptions = [
		{ id: '--', label: '--', dbValue: null },
		{ id: 'Govern', label: 'Govern', dbValue: 'govern' },
		{ id: 'Identify', label: 'Identify', dbValue: 'identify' },
		{ id: 'Protect', label: 'Protect', dbValue: 'protect' },
		{ id: 'Detect', label: 'Detect', dbValue: 'detect' },
		{ id: 'Respond', label: 'Respond', dbValue: 'respond' },
		{ id: 'Recover', label: 'Recover', dbValue: 'recover' }
	];

	// Helper to map server values to display IDs for select value binding
	function displayIdFromDb(value: unknown, options: { id: string; dbValue?: unknown }[]) {
		if (value === null || value === undefined || value === '') return '--';
		const match = options.find((o) => o.dbValue === value || o.id === value);
		return match ? String(match.id) : String(value);
	}

	// Navigation state
	let showNavigation = $state(false);
	let jumpToInput = $state('');

	// Function to handle the "Next" button click
	function nextItem() {
		if (currentIndex < appliedControls.length - 1) {
			currentIndex += 1;
		} else {
			currentIndex = 0;
		}
	}

	// Function to handle the "Back" button click
	function previousItem() {
		if (currentIndex > 0) {
			currentIndex -= 1;
		} else {
			currentIndex = appliedControls.length - 1;
		}
	}

	// Function to update a field of the current item
	async function updateField(field: string, newValue: string | number | null, options: any[] = []) {
		// Convert display value to database value if options provided
		let processedValue = newValue;
		if (newValue === '' || (newValue === '--' && field !== 'status')) {
			processedValue = null;
		} else if (options.length > 0) {
			// Find the option and get its dbValue
			const option = options.find((opt) => opt.id === newValue);
			if (option && option.dbValue !== undefined) {
				processedValue = option.dbValue;
			}
		}

		const formData = {
			id: currentAppliedControl.id,
			[field]: processedValue
		};

		try {
			const response = await fetch('?/updateAppliedControl', {
				method: 'POST',
				body: JSON.stringify(formData)
			});

			if (response.ok) {
				// Update the current control's field value with the display value for UI
				currentAppliedControl[field] = newValue === '--' ? null : newValue;
			}
		} catch (error) {
			console.error('Error updating field:', error);
		}
	}

	function jumpToItem(index: number) {
		if (index >= 0 && index < appliedControls.length) {
			currentIndex = index;
			showNavigation = false;
			jumpToInput = '';
		}
	}

	function handleJumpSubmit() {
		const targetIndex = parseInt(jumpToInput) - 1; // Convert to 0-based index
		jumpToItem(targetIndex);
	}

	function handleKeydown(event: KeyboardEvent) {
		const key = event.key.toLowerCase();
		const target = event.target as HTMLElement | null;
		const tag = target?.tagName?.toLowerCase();
		const isEditable = target?.isContentEditable;

		if (
			(tag === 'input' || tag === 'textarea' || tag === 'select' || isEditable) &&
			target?.id !== 'jumpInput'
		) {
			return;
		}

		if (key === 'n' || key === 'l') {
			event.preventDefault();
			nextItem();
		} else if (key === 'p' || key === 'h') {
			event.preventDefault();
			previousItem();
		} else if (event.key === 'g') {
			showNavigation = !showNavigation;
			if (showNavigation) {
				setTimeout(() => {
					document.getElementById('jumpInput')?.focus();
				}, 0);
			}
		} else if (key === 'escape') {
			showNavigation = false;
			jumpToInput = '';
		}
	}

	// Navigate to edit mode when clicking on name
	function navigateToEdit() {
		window.location.href = `/applied-controls/${currentAppliedControl.id}/edit`;
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="flex flex-col min-h-screen justify-center items-center">
	<div
		class="flex flex-col bg-white w-3/4 max-w-4xl h-3/4 min-h-[600px] rounded-xl shadow-xl p-4 border-4 border-primary-500"
	>
		{#if currentAppliedControl}
			<!-- Header -->
			<div class="flex justify-between items-center">
				<div class="">
					<a
						href={data.backUrl}
						class="flex items-center space-x-2 text-primary-800 hover:text-primary-600"
					>
						<i class="fa-solid fa-arrow-left"></i>
						<p class="">{data.backLabel}</p>
					</a>
				</div>
				<div class="relative">
					<button
						class="font-semibold hover:bg-gray-100 px-2 py-1 rounded cursor-pointer border border-transparent hover:border-gray-300 transition-colors flex items-center space-x-1"
						onclick={() => (showNavigation = !showNavigation)}
						title="Click to jump to specific item (or press G)"
					>
						<span>{currentIndex + 1}/{appliedControls.length}</span>
						<i class="fa-solid fa-chevron-down text-xs opacity-60"></i>
						<span class="text-xs opacity-60">(G)</span>
					</button>

					{#if showNavigation}
						<div
							class="absolute top-full right-0 mt-2 bg-white border border-gray-300 rounded-lg shadow-lg p-4 z-10 min-w-64"
						>
							<div class="flex flex-col space-y-3">
								<div class="text-sm font-medium">Jump to item:</div>
								<div class="flex space-x-2">
									<input
										id="jumpInput"
										bind:value={jumpToInput}
										type="number"
										min="1"
										max={appliedControls.length}
										placeholder="Item number"
										class="flex-1 px-2 py-1 border border-gray-300 rounded text-sm"
										onkeydown={(e) => {
											if (e.key === 'Enter') {
												e.preventDefault();
												handleJumpSubmit();
											}
										}}
									/>
									<button
										class="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
										onclick={handleJumpSubmit}
									>
										Go
									</button>
								</div>
								<div class="text-xs text-gray-500">
									Press G to toggle, Enter to jump, Esc to close
								</div>
							</div>
						</div>
					{/if}
				</div>
			</div>

			<!-- Main content area -->
			<div class="flex flex-col flex-1 justify-center overflow-hidden">
				<div class="flex flex-col items-center space-y-6 h-full">
					<div class="flex flex-col items-center space-y-2">
						<button
							onclick={navigateToEdit}
							class="font-semibold text-xl hover:text-primary-600 cursor-pointer flex-shrink-0 text-center"
							title="Click to edit this applied control"
						>
							{currentAppliedControl.name || 'Unnamed Applied Control'}
						</button>

						<div class="flex flex-col items-center space-y-1 text-sm text-gray-600">
							{#if currentAppliedControl.folder}
								<div class="flex items-center space-x-1">
									<i class="fa-solid fa-folder text-xs"></i>
									<span><strong>{m.folder()}</strong> {currentAppliedControl.folder.str}</span>
								</div>
							{/if}
							{#if currentAppliedControl.owner && currentAppliedControl.owner.length > 0}
								<div class="flex items-center space-x-1">
									<i class="fa-solid fa-user text-xs"></i>
									<span
										><strong>{m.owner()}</strong>
										{currentAppliedControl.owner.map((o) => o.str).join(', ')}</span
									>
								</div>
							{/if}
						</div>
					</div>

					<div class="flex flex-col space-y-4 overflow-y-auto flex-1 w-full max-w-4xl px-4">
						{#if currentAppliedControl.description}
							<div class="whitespace-pre-wrap leading-relaxed text-gray-700 text-left">
								<MarkdownRenderer content={currentAppliedControl.description} />
							</div>
						{/if}
					</div>
				</div>
			</div>

			<!-- Field controls -->
			<div class="flex flex-col space-y-6">
				<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
					<!-- Status -->
					{#key currentAppliedControl?.id}
						<div class="flex flex-col space-y-1">
							<label class="text-sm font-semibold" for="status">{m.status()}</label>
							<select
								id="status"
								value={currentAppliedControl?.status || '--'}
								onchange={(e) => updateField('status', e.target.value)}
								class="select select-bordered w-full"
							>
								{#each statusOptions as option}
									<option value={option.id}>{option.label}</option>
								{/each}
							</select>
						</div>
					{/key}

					<!-- Impact -->
					{#key currentAppliedControl?.id}
						<div class="flex flex-col space-y-1">
							<label class="text-sm font-semibold" for="control_impact">{m.controlImpact()}</label>
							<select
								id="control_impact"
								value={displayIdFromDb(currentAppliedControl?.control_impact, impactOptions)}
								onchange={(e) => updateField('control_impact', e.target.value, impactOptions)}
								class="select select-bordered w-full"
							>
								{#each impactOptions as option}
									<option value={option.id}>{option.label}</option>
								{/each}
							</select>
						</div>
					{/key}

					<!-- Effort -->
					{#key currentAppliedControl?.id}
						<div class="flex flex-col space-y-1">
							<label class="text-sm font-semibold" for="effort">{m.effort()}</label>
							<select
								id="effort"
								value={displayIdFromDb(currentAppliedControl?.effort, effortOptions)}
								onchange={(e) => updateField('effort', e.target.value, effortOptions)}
								class="select select-bordered w-full"
							>
								{#each effortOptions as option}
									<option value={option.id}>{option.label}</option>
								{/each}
							</select>
						</div>
					{/key}

					<!-- Priority -->
					{#key currentAppliedControl?.id}
						<div class="flex flex-col space-y-1">
							<label class="text-sm font-semibold" for="priority">{m.priority()}</label>
							<select
								id="priority"
								value={displayIdFromDb(currentAppliedControl?.priority, priorityOptions)}
								onchange={(e) => updateField('priority', e.target.value, priorityOptions)}
								class="select select-bordered w-full"
							>
								{#each priorityOptions as option}
									<option value={option.id}>{option.label}</option>
								{/each}
							</select>
						</div>
					{/key}

					<!-- CSF Function -->
					{#key currentAppliedControl?.id}
						<div class="flex flex-col space-y-1">
							<label class="text-sm font-semibold" for="csf_function">{m.csfFunction()}</label>
							<select
								id="csf_function"
								value={displayIdFromDb(currentAppliedControl?.csf_function, csfFunctionOptions)}
								onchange={(e) => updateField('csf_function', e.target.value, csfFunctionOptions)}
								class="select select-bordered w-full"
							>
								{#each csfFunctionOptions as option}
									<option value={option.id}>{option.label}</option>
								{/each}
							</select>
						</div>
					{/key}
				</div>

				<div class="flex justify-between">
					<button
						class="bg-gray-400 text-white px-4 py-2 rounded-sm flex items-center space-x-2"
						onclick={previousItem}
					>
						<span>{m.previous()}</span>
						<span class="text-xs opacity-75">(H)</span>
					</button>
					<button
						class="preset-filled-primary-500 px-4 py-2 rounded-sm flex items-center space-x-2"
						onclick={nextItem}
					>
						<span>{m.next()}</span>
						<span class="text-xs opacity-75">(L)</span>
					</button>
				</div>
			</div>
		{/if}
	</div>
</div>
