<script lang="ts">
	import { formFieldProxy, type SuperForm } from 'sveltekit-superforms';
	import RadioGroup from './RadioGroup.svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import * as m from '$paraglide/messages';

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
		onChange = () => {}
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
		// Initialize the array if it hasn't been already.
		if (!Array.isArray(internalAnswers[urn])) {
			internalAnswers[urn] = [];
		}
		// Toggle the option's selection
		if (internalAnswers[urn].includes(optionUrn)) {
			internalAnswers[urn] = internalAnswers[urn].filter((val) => val !== optionUrn);
		} else {
			internalAnswers[urn] = [...internalAnswers[urn], optionUrn];
		}
	}

	function saveTextAnswer(urn: string) {
		internalAnswers[urn] = questionBuffers[urn];
		onChange(urn, internalAnswers[urn]);
	}

	function resetTextAnswer(urn: string) {
		questionBuffers[urn] = internalAnswers[urn] || '';
	}
</script>

<div>
	{#if label}
		<label class="text-sm font-semibold" for={field}>{label}</label>
	{/if}

	<div class="control whitespace-pre-line">
		{#each Object.entries(questions) as [urn, question]}
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
								<p class="text-primary-500 font-semibold">
									{answerUrn}
								</p>
							{/if}
						{/each}
					{:else if question.choices?.find((choice) => choice.urn === internalAnswers[urn])}
						<p class="text-primary-500 font-semibold">
							{question.choices.find((choice) => choice.urn === internalAnswers[urn]).value}
						</p>
					{:else}
						<p class="text-gray-400 italic">{m.noAnswer()}</p>
					{/if}
				{:else if question.type === 'unique_choice'}
					<RadioGroup
						possibleOptions={question.choices}
						{form}
						initialValue={internalAnswers[urn]}
						key="urn"
						labelKey="value"
						field="answers"
						onChange={(newValue) => {
							internalAnswers[urn] = newValue;
							onChange(urn, newValue);
						}}
					/>
				{:else if question.type === 'multiple_choice'}
					<div class="flex flex-col gap-1 p-1 border border-surface-500 rounded-base">
						{#each question.choices as option}
							<button
								type="button"
								name="question"
								class="shadow-md p-1
									{internalAnswers[urn] && internalAnswers[urn].includes(option.urn)
									? 'preset-filled-primary-500 rounded-base'
									: 'hover:preset-tonal-primary bg-gray-200 rounded-base'}"
								onclick={() => toggleSelection(urn, option.urn)}
							>
								{option.value}
							</button>
						{/each}
					</div>
				{:else if question.type === 'date'}
					<input
						type="date"
						placeholder=""
						class="input {_class}"
						bind:value={internalAnswers[urn]}
						onchange={(e) => onChange(urn, internalAnswers[urn])}
					/>
				{:else if question.type === 'text'}
					{#if form}
						<textarea placeholder="" class="input w-full {_class}" bind:value={internalAnswers[urn]}
						></textarea>
					{:else}
						<div>
							<textarea
								placeholder=""
								class="input w-full {_class}"
								bind:value={questionBuffers[urn]}
							></textarea>
							{#if questionBuffers[urn] !== (internalAnswers[urn] || '')}
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
		{/each}
	</div>
	{#if helpText}
		<p class="text-sm text-gray-500">{helpText}</p>
	{/if}
</div>
