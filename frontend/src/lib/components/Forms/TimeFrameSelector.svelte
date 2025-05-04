<!-- TimeFrameSelector.svelte -->
<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import Select from './Select.svelte';
	import { m } from '$paraglide/messages';

	export let form: any;
	export let field: string = 'time_frames';
	export let cacheLock: any = null;
	export let cachedValue: any[] = [];
	export let label: string = m.timeFrames ? m.timeFrames() : 'Impact escalation points';
	export let helpText: string = '';
	export let hidden: boolean = false;

	const dispatch = createEventDispatcher();

	// Default empty time frame
	const emptyTimeFrame = { value: '', unit: 'minutes' };

	// Time unit options
	const unitOptions = [
		{ value: 'minutes', label: m.minutes ? m.minutes() : 'Minutes' },
		{ value: 'hours', label: m.hours ? m.hours() : 'Hours' },
		{ value: 'days', label: m.days ? m.days() : 'Days' }
	];

	// Initialize with at least one empty time frame if none exists
	$: {
		if (!cachedValue || !Array.isArray(cachedValue) || cachedValue.length === 0) {
			cachedValue = [{ ...emptyTimeFrame }];
		}
	}

	// Add a new time frame
	const addTimeFrame = () => {
		cachedValue = [...cachedValue, { ...emptyTimeFrame }];
		dispatch('change', cachedValue);
	};

	// Remove a time frame
	const removeTimeFrame = (index: number) => {
		cachedValue = cachedValue.filter((_, i) => i !== index);
		if (cachedValue.length === 0) {
			cachedValue = [{ ...emptyTimeFrame }]; // Always keep at least one
		}
		dispatch('change', cachedValue);
	};

	// Update a time frame
	const updateTimeFrame = (
		index: number,
		property: 'value' | 'unit',
		newValue: string | number
	) => {
		const updated = [...cachedValue];
		updated[index] = {
			...updated[index],
			[property]: property === 'value' ? Number(newValue) || 0 : newValue
		};
		cachedValue = updated;
		dispatch('change', cachedValue);
	};

	// Sort time frames by total minutes
	const sortTimeFrames = () => {
		const calculateMinutes = (tf: any) => {
			const value = Number(tf.value) || 0;
			switch (tf.unit) {
				case 'minutes':
					return value;
				case 'hours':
					return value * 60;
				case 'days':
					return value * 24 * 60;
				default:
					return value;
			}
		};

		cachedValue = [...cachedValue].sort((a, b) => calculateMinutes(a) - calculateMinutes(b));
		dispatch('change', cachedValue);
	};
</script>

{#if !hidden}
	<div class="time-frames-container">
		<div class="time-frames-header">
			<label for={field}>{label}</label>
			{#if helpText}
				<div class="help-text">{helpText}</div>
			{/if}
		</div>

		{#each cachedValue as timeFrame, index}
			<div class="time-frame-row">
				<div class="time-value">
					<input
						type="number"
						min="0"
						value={timeFrame.value}
						on:input={(e) => updateTimeFrame(index, 'value', e.target.value)}
						disabled={cacheLock?.[field]}
					/>
				</div>

				<div class="time-unit">
					<select
						value={timeFrame.unit}
						on:change={(e) => updateTimeFrame(index, 'unit', e.target.value)}
						disabled={cacheLock?.[field]}
					>
						{#each unitOptions as option}
							<option value={option.value}>{option.label}</option>
						{/each}
					</select>
				</div>

				<div class="time-actions">
					{#if cachedValue.length > 1}
						<button
							type="button"
							class="remove-button"
							on:click={() => removeTimeFrame(index)}
							disabled={cacheLock?.[field]}
						>
							-
						</button>
					{/if}
				</div>
			</div>
		{/each}

		<div class="time-frame-actions">
			<button
				type="button"
				class="add-button"
				on:click={addTimeFrame}
				disabled={cacheLock?.[field]}
			>
				+ {m.addTimeFrame ? m.addTimeFrame() : 'Add Time Frame'}
			</button>

			<button
				type="button"
				class="sort-button"
				on:click={sortTimeFrames}
				disabled={cacheLock?.[field] || cachedValue.length <= 1}
			>
				{m.sortTimeFrames ? m.sortTimeFrames() : 'Sort'}
			</button>
		</div>

		{#if form?.errors?.[field]}
			<div class="error">{form.errors[field]}</div>
		{/if}
	</div>
{/if}

<style>
	.time-frames-container {
		margin-bottom: 1rem;
	}

	.time-frames-header {
		margin-bottom: 0.5rem;
	}

	.help-text {
		font-size: 0.875rem;
		color: #666;
		margin-top: 0.25rem;
	}

	.time-frame-row {
		display: flex;
		gap: 0.5rem;
		margin-bottom: 0.5rem;
		align-items: center;
	}

	.time-value {
		flex: 0 0 4rem;
	}

	.time-unit {
		flex: 1;
	}

	.time-actions {
		flex: 0 0 2rem;
		display: flex;
		justify-content: center;
	}

	button {
		padding: 0.25rem 0.5rem;
		background-color: #f0f0f0;
		border: 1px solid #ccc;
		border-radius: 0.25rem;
		cursor: pointer;
	}

	button:hover:not(:disabled) {
		background-color: #e0e0e0;
	}

	button:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.time-frame-actions {
		display: flex;
		gap: 0.5rem;
		margin-top: 0.5rem;
	}

	.error {
		color: red;
		font-size: 0.875rem;
		margin-top: 0.25rem;
	}

	input,
	select {
		width: 100%;
		padding: 0.375rem 0.5rem;
		border: 1px solid #ccc;
		border-radius: 0.25rem;
	}
</style>
