<script lang="ts">
	import { formFieldProxy, type SuperForm } from 'sveltekit-superforms';
	import { safeTranslate } from '$lib/utils/i18n';
	import { isQuestionVisible } from '$lib/utils/helpers';
	import * as m from '$paraglide/messages';
	import { Tooltip } from '@skeletonlabs/skeleton-svelte';
	import SliderInput from './SliderInput.svelte';

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
		/** {question urn: [attachment]} — file questions are answered by uploading. */
		attachments?: Record<string, any[]>;
		onUpload?: (urn: string, file: File) => Promise<void> | void;
		onRemoveAttachment?: (urn: string, attachmentId: string) => Promise<void> | void;
		/** Where to open an attached file. Absent on surfaces that store nothing. */
		attachmentHref?: (attachment: any) => string;
		/** {question urn: [{id, label, folder}]} — resolved names for stored ids. */
		references?: Record<string, any[]>;
		/** Search the objects an object-reference question may point at. */
		onSearchReferences?: (urn: string, search: string) => Promise<any[]>;
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
		disabled = false,
		attachments = {},
		onUpload,
		onRemoveAttachment,
		attachmentHref,
		references = {},
		onSearchReferences
	}: Props = $props();

	// Object-reference pickers: one open dropdown at a time, results per question.
	let refOpen = $state<string | null>(null);
	let refSearch = $state<Record<string, string>>({});
	let refResults = $state<Record<string, any[]>>({});
	let refBusy = $state<Record<string, boolean>>({});

	async function searchReferences(urn: string) {
		if (!onSearchReferences) return;
		refBusy[urn] = true;
		try {
			refResults[urn] = await onSearchReferences(urn, refSearch[urn] ?? '');
		} finally {
			refBusy[urn] = false;
		}
	}

	function toggleReference(urn: string, question: any, option: any) {
		const current: string[] = Array.isArray(internalAnswers[urn]) ? internalAnswers[urn] : [];
		const multiple = !!question.config?.multiple;
		let next: string[];
		if (current.includes(option.id)) next = current.filter((id) => id !== option.id);
		else next = multiple ? [...current, option.id] : [option.id];
		internalAnswers[urn] = next;
		const known = [...(references[urn] ?? []), ...(refResults[urn] ?? [])];
		references[urn] = next.map(
			(id) => known.find((o) => o.id === id) ?? { id, label: id, folder: null }
		);
		if (!multiple) refOpen = null;
		onChange(urn, next);
	}

	let uploading = $state<Record<string, boolean>>({});
	let uploadError = $state<Record<string, string>>({});

	const humanSize = (bytes: number) =>
		bytes >= 1024 * 1024
			? `${(bytes / 1024 / 1024).toFixed(1)} MB`
			: `${Math.max(1, Math.round(bytes / 1024))} KB`;

	async function handleFiles(urn: string, input: HTMLInputElement) {
		if (!onUpload) return;
		const files = [...(input.files ?? [])];
		input.value = '';
		uploadError[urn] = '';
		uploading[urn] = true;
		try {
			for (const file of files) await onUpload(urn, file);
		} catch (e) {
			uploadError[urn] = e instanceof Error ? e.message : String(e);
		} finally {
			uploading[urn] = false;
		}
	}

	const { value } = form ? formFieldProxy(form, field) : {};

	let internalAnswers = $state(value ? $value : $state.snapshot(initialValue));
	let questionBuffers = $state<Record<string, string>>({});

	// Initialize buffers for text questions
	$effect(() => {
		Object.entries(questions).forEach(([urn, question]) => {
			if ((question.type === 'text' || question.type === 'number') && !(urn in questionBuffers)) {
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

	// Leaving the field commits it; the check/cross buttons stay as a shortcut.
	function commitOnBlur(urn: string, event: FocusEvent) {
		const next = event.relatedTarget as HTMLElement | null;
		// Revert blurs the field first; committing would save what it exists to discard.
		if (next?.dataset?.answerAction === 'revert') return;
		if (questionBuffers[urn] !== (internalAnswers[urn] ?? '')) saveTextAnswer(urn);
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

	<ul class="control flex flex-col gap-4 whitespace-pre-line">
		{#each Object.entries(questions) as [urn, question]}
			<!-- Only render if visible according to depends_on -->
			{#if isQuestionVisible(question, internalAnswers, questions)}
				<li
					class="flex flex-col justify-between gap-2 rounded-xl border border-surface-200-800 bg-surface-50-950 px-4 py-3"
				>
					<p class="flex flex-wrap items-baseline gap-x-2 font-semibold">
						<span>{question.text}</span>
						{#if question.required === false}
							<span class="text-xs font-normal text-surface-400">{m.optional()}</span>
						{:else}
							<span class="text-sm font-bold text-error-500" title={m.required()}>*</span>
						{/if}
						<span class="text-[11px] font-normal uppercase tracking-wide text-surface-400"
							>{safeTranslate(question.type)}</span
						>
					</p>

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
						{:else if internalAnswers[urn] === true}
							<p class="text-primary-500 font-semibold">{m.yes()}</p>
						{:else if internalAnswers[urn] === false}
							<p class="text-primary-500 font-semibold">{m.no()}</p>
						{:else if internalAnswers[urn] != null}
							<p class="text-primary-500 font-semibold">{internalAnswers[urn]}</p>
						{:else}
							<p class="text-surface-400-600 italic">{m.noAnswer()}</p>
						{/if}
					{:else if question.type === 'unique_choice'}
						{#if question.config?.widget === 'slider' && question.choices.length >= 2}
							<SliderInput
								mode="choice"
								choices={question.choices}
								value={internalAnswers[urn] ?? null}
								{disabled}
								ariaLabel={question.text}
								onChange={(v) => {
									internalAnswers[urn] = v;
									onChange(urn, v);
								}}
							/>
						{:else}
							<div class="flex flex-col gap-1.5 rounded-lg border border-surface-200-800 p-1.5">
								{#each question.choices as option}
									{@const selected = internalAnswers[urn] === option.urn}
									<button
										type="button"
										name="question"
										{disabled}
										class="rounded-base border border-surface-300-700 px-3 py-2 text-left shadow-sm transition-all duration-150
											{selected
											? 'preset-filled-primary-500 rounded-base'
											: 'bg-surface-100-900 rounded-base hover:bg-surface-300-700'}
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
											<Tooltip positioning={{ placement: 'top' }} openDelay={50}>
												<Tooltip.Trigger>
													{#snippet child({ props })}
														<span {...props} class="underline"
															><i class="ml-2 fa-solid fa-circle-info"></i></span
														>
													{/snippet}
												</Tooltip.Trigger>
												<Tooltip.Positioner>
													<Tooltip.Content class="card preset-filled p-4"
														>{option.description}</Tooltip.Content
													>
												</Tooltip.Positioner>
											</Tooltip>
										{/if}
									</button>
								{/each}
							</div>
						{/if}
					{:else if question.type === 'multiple_choice'}
						<div class="flex flex-col gap-1.5 rounded-lg border border-surface-200-800 p-1.5">
							{#each question.choices as option}
								{@const selected =
									Array.isArray(internalAnswers[urn]) && internalAnswers[urn].includes(option.urn)}
								<button
									type="button"
									name="question"
									{disabled}
									class="rounded-base border border-surface-300-700 px-3 py-2 text-left shadow-sm transition-all duration-150
										{selected
										? 'preset-filled-primary-500 rounded-base'
										: 'bg-surface-100-900 rounded-base hover:bg-surface-300-700'}
										{disabled ? 'opacity-50 cursor-not-allowed' : ''}"
									style={selected
										? `background-color: ${sanitizeColor(option.color) ?? ''}; color: white;`
										: ''}
									onclick={() => toggleSelection(urn, option.urn)}
								>
									{option.value}
									{#if option.description}
										<Tooltip positioning={{ placement: 'top' }} openDelay={50}>
											<Tooltip.Trigger>
												{#snippet child({ props })}
													<span {...props} class="underline"
														><i class="ml-2 fa-solid fa-circle-info"></i></span
													>
												{/snippet}
											</Tooltip.Trigger>
											<Tooltip.Positioner>
												<Tooltip.Content class="card preset-filled p-4"
													>{option.description}</Tooltip.Content
												>
											</Tooltip.Positioner>
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
					{:else if question.type === 'boolean'}
						<div class="flex flex-col gap-1.5 rounded-lg border border-surface-200-800 p-1.5">
							{#each [{ value: true, label: m.yes() }, { value: false, label: m.no() }] as option}
								{@const selected = internalAnswers[urn] === option.value}
								<button
									type="button"
									name="question"
									{disabled}
									class="rounded-base border border-surface-300-700 px-3 py-2 text-left shadow-sm transition-all duration-150
										{selected
										? 'preset-filled-primary-500 rounded-base'
										: 'bg-surface-100-900 rounded-base hover:bg-surface-300-700'}
										{disabled ? 'opacity-50 cursor-not-allowed' : ''}"
									onclick={() => {
										internalAnswers[urn] =
											internalAnswers[urn] === option.value ? null : option.value;
										onChange(urn, internalAnswers[urn]);
									}}
								>
									{option.label}
								</button>
							{/each}
						</div>
					{:else if question.type === 'number'}
						{#if question.config?.widget === 'slider'}
							<SliderInput
								mode="number"
								min={Number(question.config.min ?? 0)}
								max={Number(question.config.max ?? 100)}
								step={Number(question.config.step ?? 1)}
								value={internalAnswers[urn] ?? null}
								{disabled}
								ariaLabel={question.text}
								onChange={(v) => {
									internalAnswers[urn] = v;
									onChange(urn, v);
								}}
							/>
						{:else if form}
							<input
								type="number"
								class="input {_class}"
								{disabled}
								bind:value={internalAnswers[urn]}
								onchange={() => onChange(urn, internalAnswers[urn])}
							/>
						{:else}
							<div>
								<input
									type="number"
									class="input {_class}"
									{disabled}
									bind:value={questionBuffers[urn]}
									onchange={() => {
										const val = questionBuffers[urn] === '' ? null : Number(questionBuffers[urn]);
										internalAnswers[urn] = val;
										onChange(urn, val);
									}}
								/>
							</div>
						{/if}
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
									onblur={(e) => commitOnBlur(urn, e)}
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
										data-answer-action="revert"
										aria-label="Reset observation"
									>
										<i class="fa-solid fa-xmark opacity-70"></i>
									</button>
								{/if}
							</div>
						{/if}
					{:else if question.type === 'object_reference'}
						{@const picked = references[urn] ?? []}
						<div class="flex flex-col gap-2">
							{#if picked.length}
								<ul class="flex flex-col gap-1">
									{#each picked as option (option.id)}
										<li
											class="flex items-center gap-2 rounded-lg border border-surface-200-800 bg-surface-100-900 px-3 py-2 text-sm"
										>
											<i class="fa-solid fa-link text-surface-400"></i>
											<span class="min-w-0 grow truncate">{option.label}</span>
											{#if option.folder}
												<span class="shrink-0 text-xs text-surface-400">{option.folder}</span>
											{/if}
											{#if !disabled && onSearchReferences}
												<button
													type="button"
													class="shrink-0 text-surface-400 hover:text-error-500"
													aria-label={m.delete()}
													onclick={() => toggleReference(urn, question, option)}
												>
													<i class="fa-solid fa-xmark"></i>
												</button>
											{/if}
										</li>
									{/each}
								</ul>
							{:else if disabled || !onSearchReferences}
								<p class="text-xs italic text-surface-400">{m.objectReferenceNone()}</p>
							{/if}

							{#if !disabled && onSearchReferences}
								<div class="flex items-center gap-2">
									<input
										type="text"
										class="input text-sm"
										placeholder={m.objectReferenceSearch()}
										bind:value={refSearch[urn]}
										onfocus={() => {
											refOpen = urn;
											if (!refResults[urn]) searchReferences(urn);
										}}
										oninput={() => searchReferences(urn)}
									/>
									{#if refBusy[urn]}
										<i class="fa-solid fa-spinner fa-spin text-xs text-surface-400"></i>
									{/if}
								</div>
								{#if refOpen === urn && (refResults[urn] ?? []).length}
									<ul
										class="max-h-56 overflow-y-auto rounded-lg border border-surface-200-800 bg-surface-50-950"
									>
										{#each refResults[urn] as option (option.id)}
											{@const selected = (internalAnswers[urn] ?? []).includes(option.id)}
											<li>
												<button
													type="button"
													class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-surface-100-900 {selected
														? 'text-primary-600'
														: ''}"
													onclick={() => toggleReference(urn, question, option)}
												>
													<i
														class="fa-solid {selected
															? 'fa-circle-check'
															: 'fa-circle'} text-xs opacity-60"
													></i>
													<span class="min-w-0 grow truncate">{option.label}</span>
													{#if option.folder}
														<span class="shrink-0 text-xs text-surface-400">{option.folder}</span>
													{/if}
												</button>
											</li>
										{/each}
									</ul>
								{/if}
							{/if}
						</div>
					{:else if question.type === 'file'}
						{@const files = attachments[urn] ?? []}
						{@const fileLimit = question.config?.multiple
							? Number(question.config?.max_files) || Infinity
							: 1}
						<div class="flex flex-col gap-2">
							{#if files.length}
								<ul class="flex flex-col gap-1">
									{#each files as file (file.id)}
										<li
											class="flex items-center gap-2 rounded-lg border border-surface-200-800 bg-surface-100-900 px-3 py-2 text-sm"
										>
											<i class="fa-solid fa-paperclip text-surface-400"></i>
											{#if attachmentHref}
												<a
													class="anchor min-w-0 grow truncate"
													href={attachmentHref(file)}
													target="_blank"
													rel="noopener"
													title={m.openFile()}>{file.filename}</a
												>
											{:else}
												<span class="min-w-0 grow truncate">{file.filename}</span>
											{/if}
											<span class="shrink-0 text-xs text-surface-400">{humanSize(file.size)}</span>
											{#if file.promoted_to}
												<span class="shrink-0 text-xs text-emerald-600" title={m.evidence()}>
													<i class="fa-solid fa-circle-check"></i>
												</span>
											{/if}
											{#if !disabled && onRemoveAttachment}
												<button
													type="button"
													class="shrink-0 text-surface-400 hover:text-error-500"
													aria-label={m.delete()}
													onclick={() => onRemoveAttachment?.(urn, file.id)}
												>
													<i class="fa-solid fa-xmark"></i>
												</button>
											{/if}
										</li>
									{/each}
								</ul>
							{/if}
							{#if onUpload && !disabled && files.length >= fileLimit}
								<p class="text-xs text-surface-400">
									{m.fileLimitReached({ count: fileLimit })}
								</p>
							{:else if onUpload && !disabled}
								<label
									class="flex w-fit cursor-pointer items-center gap-2 rounded-base border border-surface-300-700 bg-surface-100-900 px-3 py-2 text-sm shadow-sm hover:bg-surface-200-800"
								>
									{#if uploading[urn]}
										<i class="fa-solid fa-spinner fa-spin"></i>
									{:else}
										<i class="fa-solid fa-arrow-up-from-bracket"></i>
									{/if}
									<span>{m.addFile()}</span>
									<input
										type="file"
										class="hidden"
										multiple={question.config?.multiple ?? false}
										accept={question.config?.accept || undefined}
										disabled={uploading[urn]}
										onchange={(e) => handleFiles(urn, e.currentTarget)}
									/>
								</label>
							{:else if !files.length}
								<p class="text-xs italic text-surface-400">{m.uploadUnavailableHere()}</p>
							{/if}
							{#if uploadError[urn]}
								<p class="text-xs text-error-500">{uploadError[urn]}</p>
							{/if}
						</div>
					{/if}
				</li>
			{/if}
		{/each}
	</ul>

	{#if helpText}
		<p class="text-sm text-surface-600-400">{helpText}</p>
	{/if}
</div>
