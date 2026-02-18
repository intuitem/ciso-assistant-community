<script lang="ts">
	import { formFieldProxy, type SuperForm } from 'sveltekit-superforms';
	import { safeTranslate } from '$lib/utils/i18n';
	import { isQuestionVisible } from '$lib/utils/helpers';
	import * as m from '$paraglide/messages';
	import { Tooltip } from '@skeletonlabs/skeleton-svelte';

	interface Props {
		class?: string;
		label?: string;
		shallow?: boolean;
		form?: SuperForm<Record<string, any>>;
		initialValue?: any;
		questions?: any;
		field: string;
		helpText?: string;
		onChange?: (urn: string, newAnswer: any) => void;
		disabled?: boolean;
	}

	let {
		class: _class = 'w-fit',
		label,
		shallow = false,
		form,
		questions = {},
		initialValue = {},
		field,
		helpText,
		onChange = () => {},
		disabled = false
	}: Props = $props();

	const { value } = form ? formFieldProxy(form, field) : {};

	let internalAnswers = $state(value ? $value : initialValue);
	let questionBuffers = $state<Record<string, string>>({});

	// Initialize buffers for text questions
	$effect(() => {
		Object.entries(questions).forEach(([urn, question]) => {
			if (question.type === 'text' && !(urn in questionBuffers)) {
				questionBuffers[urn] = internalAnswers[urn] || '';
			}
		});
	});

	$effect(() => {
		if (value) {
			$value = internalAnswers;
		}
	});

	function toggleSelection(urn: string, optionUrn: string) {
		if (!Array.isArray(internalAnswers[urn])) {
			internalAnswers[urn] = [];
		}
		if (internalAnswers[urn].includes(optionUrn)) {
			internalAnswers[urn] = internalAnswers[urn].filter((val) => val !== optionUrn);
		} else {
			internalAnswers[urn] = [...internalAnswers[urn], optionUrn];
		}
		onChange(urn, internalAnswers[urn]);
	}

	function saveTextAnswer(urn: string) {
		internalAnswers[urn] = questionBuffers[urn];
		onChange(urn, internalAnswers[urn]);
	}

	function resetTextAnswer(urn: string) {
		questionBuffers[urn] = internalAnswers[urn] || '';
	}

	function sanitizeColor(color: string): string {
		// Only allow hex colors, rgb(), rgba(), or named colors
		const validColorRegex = /^(#[0-9A-Fa-f]{3,6}|rgb\(|rgba\(|[a-z]+)$/;
		return validColorRegex.test(color) ? color : '';
	}
</script>

<div>
	{#if label}
		<label class="text-sm font-semibold" for={field}>{label}</label>
	{/if}

	<div class="control whitespace-pre-line">
		{#each Object.entries(questions) as [urn, question]}
			<!-- Only render if visible according to depends_on -->
			{#if isQuestionVisible(question, internalAnswers)}
				<li class="flex flex-col justify-between border rounded-xl px-2 pb-2">
					<p class="font-semibold p-2">{question.text} ({safeTranslate(question.type)})</p>

					{#if shallow}
						{#if Array.isArray(internalAnswers[urn]) && internalAnswers[urn].length > 0}
							{#each internalAnswers[urn] as answerUrn}
								{#if question.choices.find((choice) => choice.urn === answerUrn)}
									<p class="text-primary-500 font-semibold">
										{question.choices.find((choice) => choice.urn === answerUrn).value}
									</p>
								{:else}
									<p class="text-primary-500 font-semibold">{answerUrn}</p>
								{/if}
							{/each}
						{:else if question.choices?.find((choice) => choice.urn === internalAnswers[urn])}
							<p class="text-primary-500 font-semibold">
								{question.choices.find((choice) => choice.urn === internalAnswers[urn]).value}
							</p>
						{:else}
							<p class="text-surface-400-600 italic">{m.noAnswer()}</p>
						{/if}
					{:else if question.type === 'unique_choice'}
						<div class="flex flex-col gap-1 p-1 border border-surface-500 rounded-base">
							{#each question.choices as option}
								{@const selected = internalAnswers[urn] === option.urn}
								<button
									type="button"
									name="question"
									{disabled}
									class="shadow-sm p-1 rounded-base border border-surface-300-700 transition-all duration-150
										{selected ? 'preset-filled-primary-500 rounded-base' : 'bg-surface-100-900 rounded-base hover:bg-surface-300-700'}
										{disabled ? 'opacity-50 cursor-not-allowed' : ''}"
									style={selected
										? `background-color: ${sanitizeColor(option.color) ?? ''}; color: white;`
										: ''}
									onclick={() => {
										if (internalAnswers[urn] === option.urn) {
											internalAnswers[urn] = null;
											onChange(urn, null);
										} else {
											internalAnswers[urn] = option.urn;
											onChange(urn, option.urn);
										}
									}}
								>
									{option.value}
									{#if option.description}
										<Tooltip
											positioning={{ placement: 'top' }}
											triggerBase="underline"
											contentBase="card preset-filled p-4"
											openDelay={50}
										>
											{#snippet trigger()}<i class="ml-2 fa-solid fa-circle-info"></i>{/snippet}
											{#snippet content()}{option.description}{/snippet}
										</Tooltip>
									{/if}
								</button>
							{/each}
						</div>
					{:else if question.type === 'multiple_choice'}
						<div class="flex flex-col gap-1 p-1 border border-surface-500 rounded-base">
							{#each question.choices as option}
								{@const selected =
									Array.isArray(internalAnswers[urn]) && internalAnswers[urn].includes(option.urn)}
								<button
									type="button"
									name="question"
									{disabled}
									class="shadow-sm p-1 rounded-base border border-surface-300-700 transition-all duration-150
										{selected ? 'preset-filled-primary-500 rounded-base' : 'bg-surface-100-900 rounded-base hover:bg-surface-300-700'}
										{disabled ? 'opacity-50 cursor-not-allowed' : ''}"
									style={selected
										? `background-color: ${sanitizeColor(option.color) ?? ''}; color: white;`
										: ''}
									onclick={() => toggleSelection(urn, option.urn)}
								>
									{option.value}
									{#if option.description}
										<Tooltip
											positioning={{ placement: 'top' }}
											triggerBase="underline"
											contentBase="card preset-filled p-4"
											openDelay={50}
										>
											{#snippet trigger()}<i class="ml-2 fa-solid fa-circle-info"></i>{/snippet}
											{#snippet content()}{option.description}{/snippet}
										</Tooltip>
									{/if}
								</button>
							{/each}
						</div>
					{:else if question.type === 'date'}
						<input
							type="date"
							class="input {_class}"
							{disabled}
							bind:value={internalAnswers[urn]}
							onchange={(e) => onChange(urn, internalAnswers[urn])}
						/>
					{:else if question.type === 'text'}
						{#if form}
							<textarea
								placeholder=""
								class="input w-full {_class}"
								{disabled}
								bind:value={internalAnswers[urn]}
							></textarea>
						{:else}
							<div>
								<textarea
									placeholder=""
									class="input w-full {_class}"
									{disabled}
									bind:value={questionBuffers[urn]}
								></textarea>
								{#if !disabled && questionBuffers[urn] !== (internalAnswers[urn] || '')}
									<button
										class="rounded-md w-8 h-8 border shadow-lg hover:bg-green-300 hover:text-green-500 duration-300"
										onclick={() => saveTextAnswer(urn)}
										type="button"
										aria-label="Save observation"
									>
										<i class="fa-solid fa-check opacity-70"></i>
									</button>
									<button
										class="rounded-md w-8 h-8 border shadow-lg hover:bg-red-300 hover:text-red-500 duration-300"
										onclick={() => resetTextAnswer(urn)}
										type="button"
										aria-label="Reset observation"
									>
										<i class="fa-solid fa-xmark opacity-70"></i>
									</button>
								{/if}
							</div>
						{/if}
					{/if}
				</li>
			{/if}
		{/each}
	</div>

	{#if helpText}
		<p class="text-sm text-surface-600-400">{helpText}</p>
	{/if}
</div>
