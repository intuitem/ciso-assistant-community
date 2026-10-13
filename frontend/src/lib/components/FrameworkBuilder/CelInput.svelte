<script lang="ts">
	import { m } from '$paraglide/messages';
	import {
		celSuggestions,
		conditionExpression,
		conditionOps,
		joinCondition,
		NUMBER_OPS,
		type CelCatalog,
		type CelCompletion,
		type CelPlace,
		type ConditionOp
	} from './cel-complete';

	interface Props {
		value: string;
		/** Called on blur and after an inserted condition, with the whole expression. */
		oncommit: (value: string) => void;
		catalog: CelCatalog;
		place: CelPlace;
		multiline?: boolean;
		placeholder?: string;
		class?: string;
		testid?: string;
	}

	let {
		value,
		oncommit,
		catalog,
		place,
		multiline = false,
		placeholder = '',
		class: className = '',
		testid
	}: Props = $props();

	let field: HTMLInputElement | HTMLTextAreaElement | undefined = $state();
	let text = $state('');
	let completion: CelCompletion | null = $state(null);
	let active = $state(0);
	const listId = `cel-list-${Math.random().toString(36).slice(2, 10)}`;

	$effect(() => {
		text = value;
	});

	function suggest(explicit = false) {
		if (!field) return;
		text = field.value;
		const cursor = field.selectionStart ?? field.value.length;
		if (field.selectionEnd !== cursor) {
			completion = null;
			return;
		}
		completion = celSuggestions(field.value, cursor, catalog, place, explicit);
		active = 0;
	}

	function accept(index: number) {
		if (!field || !completion) return;
		const item = completion.items[index];
		if (!item) return;
		const typed = field.value;
		field.value = typed.slice(0, completion.from) + item.insert + typed.slice(completion.to);
		text = field.value;
		const caret = completion.from + item.insert.length;
		field.setSelectionRange(caret, caret);
		field.focus();
		completion = null;
		if (item.again) suggest(true);
	}

	function onkeydown(e: KeyboardEvent) {
		if (e.key === ' ' && (e.ctrlKey || e.metaKey)) {
			e.preventDefault();
			suggest(true);
			return;
		}
		if (!completion) return;
		const count = completion.items.length;
		if (e.key === 'ArrowDown') {
			e.preventDefault();
			active = (active + 1) % count;
		} else if (e.key === 'ArrowUp') {
			e.preventDefault();
			active = (active - 1 + count) % count;
		} else if (e.key === 'Enter' || e.key === 'Tab') {
			e.preventDefault();
			accept(active);
		} else if (e.key === 'Escape') {
			e.preventDefault();
			e.stopPropagation();
			completion = null;
		}
	}

	$effect(() => {
		if (!completion) return;
		document.getElementById(`${listId}-${active}`)?.scrollIntoView({ block: 'nearest' });
	});

	// ----- Insert condition -----

	let building = $state(false);
	let questionId = $state('');
	let op: ConditionOp | '' = $state('');
	let operand: string | number | null = $state('');
	let join: '&&' | '||' = $state('&&');

	const usable = $derived(
		catalog.questions.filter((q) => conditionOps(q.type, catalog.mode).length)
	);
	const groups = $derived(
		[...new Set(usable.map((q) => q.group))].map((group) => ({
			group,
			questions: usable.filter((q) => q.group === group)
		}))
	);
	const question = $derived(usable.find((q) => q.id === questionId));
	const ops = $derived(question ? conditionOps(question.type, catalog.mode) : []);
	const needsChoice = $derived(
		op === 'is' || op === 'is_not' || op === 'includes' || op === 'excludes'
	);
	const needsNumber = $derived(NUMBER_OPS.includes(op as ConditionOp));
	const condition = $derived(
		question && op
			? conditionExpression(question, op, operand === '' ? null : operand, catalog.mode)
			: null
	);

	const opLabel: Record<string, () => string> = {
		is: m.builderConditionIs,
		is_not: m.builderConditionIsNot,
		includes: m.builderConditionIncludes,
		excludes: m.builderConditionExcludes,
		yes: m.builderConditionIsYes,
		no: m.builderConditionIsNo,
		answered: m.builderConditionAnswered,
		not_answered: m.builderConditionNotAnswered
	};

	function pickQuestion(id: string) {
		questionId = id;
		const next = usable.find((q) => q.id === id);
		op = next ? (conditionOps(next.type, catalog.mode)[0] ?? '') : '';
		operand = '';
	}

	function insertCondition() {
		if (!condition || !field) return;
		const next = joinCondition(field.value, condition, join);
		field.value = next;
		text = next;
		oncommit(next);
		building = false;
		questionId = '';
		op = '';
		operand = '';
	}

	const selectClass =
		'text-xs border border-surface-200-800 rounded px-1.5 py-1 bg-surface-50-950 min-w-0';
</script>

<div class="relative">
	{#if multiline}
		<textarea
			bind:this={field}
			{value}
			{placeholder}
			rows="2"
			class={className}
			autocomplete="off"
			spellcheck="false"
			role="combobox"
			aria-expanded={!!completion}
			aria-controls={listId}
			aria-autocomplete="list"
			data-testid={testid}
			oninput={() => suggest()}
			{onkeydown}
			onclick={() => completion && suggest()}
			onblur={(e) => {
				completion = null;
				oncommit(e.currentTarget.value);
			}}
		></textarea>
	{:else}
		<input
			bind:this={field}
			type="text"
			{value}
			{placeholder}
			class={className}
			autocomplete="off"
			spellcheck="false"
			role="combobox"
			aria-expanded={!!completion}
			aria-controls={listId}
			aria-autocomplete="list"
			data-testid={testid}
			oninput={() => suggest()}
			{onkeydown}
			onclick={() => completion && suggest()}
			onblur={(e) => {
				completion = null;
				oncommit(e.currentTarget.value);
			}}
		/>
	{/if}

	{#if completion}
		<ul
			id={listId}
			role="listbox"
			class="absolute left-0 right-0 z-30 mt-1 max-h-56 overflow-auto rounded-md border border-surface-200-800 bg-surface-50-950 shadow-lg text-xs"
		>
			{#each completion.items as item, i (i)}
				<li
					id="{listId}-{i}"
					role="option"
					aria-selected={i === active}
					class="flex items-baseline gap-2 px-2 py-1 cursor-pointer {i === active
						? 'bg-primary-100-900'
						: 'hover:bg-surface-100-900'}"
					onmousedown={(e) => {
						e.preventDefault();
						accept(i);
					}}
					onmouseenter={() => (active = i)}
				>
					<span class="font-mono text-surface-800-200 shrink-0">{item.label}</span>
					{#if item.detail}
						<span class="text-surface-500 truncate min-w-0">{item.detail}</span>
					{/if}
				</li>
			{/each}
		</ul>
	{/if}
</div>

<div class="mt-1">
	{#if !building}
		<button
			type="button"
			class="text-xs text-blue-600 hover:text-blue-700 font-medium"
			onclick={() => (building = true)}
			data-testid="cel-insert-condition"
		>
			<i class="fa-solid fa-wand-magic-sparkles mr-1"></i>{m.builderInsertCondition()}
		</button>
	{:else if !usable.length}
		<p class="text-xs text-surface-500">
			{m.builderConditionNoQuestions()}
			<button
				type="button"
				class="ml-1 text-surface-500 hover:text-surface-600-400 underline"
				onclick={() => (building = false)}>{m.cancel()}</button
			>
		</p>
	{:else}
		<div
			class="flex flex-wrap items-center gap-1.5 rounded-md border border-surface-200-800 bg-surface-100-900/50 p-2"
			data-testid="cel-condition-builder"
		>
			{#if text.trim()}
				<select class={selectClass} bind:value={join} aria-label={m.builderConditionJoin()}>
					<option value="&&">{m.builderConditionAnd()}</option>
					<option value="||">{m.builderConditionOr()}</option>
				</select>
			{/if}
			<select
				class="{selectClass} flex-1 basis-48"
				value={questionId}
				onchange={(e) => pickQuestion(e.currentTarget.value)}
				aria-label={m.builderConditionQuestion()}
				data-testid="cel-condition-question"
			>
				<option value="">{m.builderConditionQuestion()}…</option>
				{#each groups as { group, questions } (group)}
					<optgroup label={group}>
						{#each questions as q (q.id)}
							<option value={q.id}>{q.label}</option>
						{/each}
					</optgroup>
				{/each}
			</select>
			{#if question}
				<select
					class={selectClass}
					bind:value={op}
					onchange={() => (operand = '')}
					data-testid="cel-condition-op"
				>
					{#each ops as o (o)}
						<option value={o}>{opLabel[o]?.() ?? o}</option>
					{/each}
				</select>
				{#if needsChoice}
					<select class={selectClass} bind:value={operand} data-testid="cel-condition-choice">
						<option value="">…</option>
						{#each question.choices as choice (choice.id)}
							<option value={choice.id}>{choice.label || choice.id}</option>
						{/each}
					</select>
				{:else if needsNumber}
					<input
						type="number"
						step="any"
						class="{selectClass} w-24"
						bind:value={operand}
						data-testid="cel-condition-number"
					/>
				{/if}
			{/if}
			<button
				type="button"
				class="btn btn-sm preset-filled-primary-500 text-xs px-2 py-1"
				disabled={!condition}
				onclick={insertCondition}
				data-testid="cel-condition-insert">{m.builderConditionInsert()}</button
			>
			<button
				type="button"
				class="text-xs text-surface-500 hover:text-surface-600-400"
				onclick={() => (building = false)}>{m.cancel()}</button
			>
			{#if condition}
				<code class="basis-full font-mono text-[11px] text-surface-500 break-all">{condition}</code>
			{/if}
		</div>
	{/if}
</div>
