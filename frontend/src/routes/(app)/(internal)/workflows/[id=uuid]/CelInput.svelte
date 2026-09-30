<script lang="ts">
	// CEL input with an autocomplete popover: variables, step outputs, loop
	// item, seeds, functions, and list/string methods after a dot. Keeps
	// `data-syntax="cel"` so the data browser inserts bare paths.
	//
	// It is a textarea that behaves like a single-line input: the inspector is
	// narrow, and a formula that scrolls sideways inside a 150px box is
	// unreadable. The field wraps and grows with its content instead, so the
	// whole expression stays visible. Enter never inserts a line break (it
	// accepts a suggestion); Shift+Enter does, for authors who want to format
	// a long expression, which CEL reads as whitespace.
	import {
		applySuggestion,
		buildSuggestions,
		currentToken,
		type Scope,
		type Suggestion
	} from './compute-assist';

	interface Props {
		value: string;
		scope: Scope;
		placeholder?: string;
		oninput?: () => void;
		testid?: string;
	}

	// No default on the binding: a freshly mounted instance must never push an
	// empty string up into the row it displays.
	let { value = $bindable(), scope, placeholder = '', oninput, testid }: Props = $props();

	let input = $state<HTMLTextAreaElement | null>(null);

	// `field-sizing: content` does this in CSS where supported; the manual
	// resize covers the rest and costs nothing where it is redundant.
	function autosize(el: HTMLTextAreaElement | null) {
		if (!el) return;
		el.style.height = 'auto';
		el.style.height = `${el.scrollHeight}px`;
	}

	$effect(() => {
		void value;
		autosize(input);
	});
	let suggestions = $state<Suggestion[]>([]);
	let selected = $state(0);
	let tokenStart = $state(0);
	let open = $derived(suggestions.length > 0);

	function refresh() {
		const el = input;
		if (!el) return;
		const cursor = el.selectionStart ?? el.value.length;
		// Only complete at the end of a token: a cursor in the middle of a word
		// or after a space has nothing to finish.
		const token = currentToken(el.value, cursor);
		tokenStart = token.start;
		suggestions = buildSuggestions(token.text, scope);
		selected = 0;
	}

	function close() {
		suggestions = [];
	}

	function accept(suggestion: Suggestion) {
		const el = input;
		if (!el) return;
		const cursor = el.selectionStart ?? el.value.length;
		const next = applySuggestion(el.value, cursor, tokenStart, suggestion);
		value = next.value;
		el.value = next.value;
		el.dispatchEvent(new Event('input', { bubbles: true }));
		requestAnimationFrame(() => {
			el.focus();
			el.setSelectionRange(next.cursor, next.cursor);
			// A suggestion ending in a dot has more to offer.
			if (suggestion.insert.endsWith('.')) refresh();
			else close();
		});
	}

	function onKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter' && !event.shiftKey && !open) {
			// Single-line semantics: Enter is not a line break here.
			event.preventDefault();
			return;
		}
		if (!open) return;
		if (event.key === 'ArrowDown') {
			event.preventDefault();
			selected = (selected + 1) % suggestions.length;
		} else if (event.key === 'ArrowUp') {
			event.preventDefault();
			selected = (selected - 1 + suggestions.length) % suggestions.length;
		} else if (event.key === 'Tab' || event.key === 'Enter') {
			event.preventDefault();
			accept(suggestions[selected]);
		} else if (event.key === 'Escape') {
			event.preventDefault();
			close();
		}
	}

	function onInput() {
		autosize(input);
		refresh();
		oninput?.();
	}

	function onBlur() {
		// Let a click on an item land before the list goes away.
		setTimeout(close, 120);
	}
</script>

<div class="relative w-full min-w-0">
	<textarea
		bind:this={input}
		rows="1"
		class="input text-xs font-mono w-full min-w-0 resize-none overflow-hidden leading-snug py-1 [field-sizing:content] [overflow-wrap:anywhere]"
		{placeholder}
		bind:value
		oninput={onInput}
		onkeydown={onKeydown}
		onclick={refresh}
		onblur={onBlur}
		autocomplete="off"
		spellcheck="false"
		wrap="soft"
		data-syntax="cel"
		data-testid={testid}
		role="combobox"
		aria-expanded={open}
		aria-autocomplete="list"
		aria-controls={open ? 'cel-suggestions' : undefined}
	></textarea>
	{#if open}
		<ul
			id="cel-suggestions"
			role="listbox"
			class="absolute left-0 right-0 top-full mt-0.5 z-50 max-h-48 overflow-auto rounded border border-surface-200-800 bg-surface-50-950 shadow-lg text-[10px] font-mono"
		>
			{#each suggestions as suggestion, index (suggestion.kind + suggestion.insert)}
				<li
					role="option"
					aria-selected={index === selected}
					class="flex items-baseline gap-2 px-2 py-1 cursor-pointer {index === selected
						? 'bg-primary-500/20'
						: 'hover:bg-surface-200-800'}"
					onmousedown={(event) => {
						event.preventDefault();
						accept(suggestion);
					}}
					onmouseenter={() => (selected = index)}
				>
					<span class="text-surface-900-100 shrink-0">{suggestion.text}</span>
					{#if suggestion.detail}
						<span class="text-surface-500 truncate">{suggestion.detail}</span>
					{/if}
					<span class="ml-auto text-[9px] uppercase text-surface-400-600 shrink-0"
						>{suggestion.kind}</span
					>
				</li>
			{/each}
		</ul>
	{/if}
</div>
