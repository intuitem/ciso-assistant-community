import { LOCALE_MAP, language, defaultLangLabels } from '$lib/utils/locales';

// ----- locale helpers (F1) -----

const localeMapTyped = LOCALE_MAP as Record<string, { name: string; flag: string }>;
const defaultLabels = defaultLangLabels as Record<string, string>;
const langNames = language as Record<string, string>;

/**
 * Produce a human-readable label for a locale code, e.g. "English (English)".
 */
export function localeLabel(code: string): string {
	const entry = localeMapTyped[code];
	if (!entry) return code.toUpperCase();
	return `${defaultLabels[code]} (${langNames[entry.name]})`;
}

// ----- question-type metadata (F5) -----

/**
 * A picker card. `value` is a composite key — for slider variants it's
 * `<storedType>:slider`. `storedType` is what gets written to `Question.type`.
 * Splitting the two means the picker can surface "Number (slider)" as a
 * first-class entry without needing a new value in the data model.
 */
export interface QuestionTypeInfo {
	value: string;
	storedType: string;
	widget: 'native' | 'slider';
	label: string;
	icon: string;
	color: string;
}

const SLIDER_ICON = 'fa-sliders';

// Order matters: the picker is a 2-column grid, so positions [0,1] form
// row 1, [2,3] row 2, etc. We pair each slider variant on the same row
// as its parent.
export const QUESTION_TYPES: QuestionTypeInfo[] = [
	// Row 1
	{
		value: 'text',
		storedType: 'text',
		widget: 'native',
		label: 'Text',
		icon: 'fa-font',
		color: 'text-blue-600 bg-blue-50'
	},
	{
		value: 'boolean',
		storedType: 'boolean',
		widget: 'native',
		label: 'Boolean',
		icon: 'fa-toggle-on',
		color: 'text-green-600 bg-green-50'
	},
	// Row 2
	{
		value: 'number',
		storedType: 'number',
		widget: 'native',
		label: 'Number',
		icon: 'fa-hashtag',
		color: 'text-emerald-600 bg-emerald-50'
	},
	{
		value: 'number:slider',
		storedType: 'number',
		widget: 'slider',
		label: 'Number (slider)',
		icon: SLIDER_ICON,
		color: 'text-emerald-600 bg-emerald-50'
	},
	// Row 3
	{
		value: 'unique_choice',
		storedType: 'unique_choice',
		widget: 'native',
		label: 'Single choice',
		icon: 'fa-circle-dot',
		color: 'text-violet-600 bg-violet-50'
	},
	{
		value: 'unique_choice:slider',
		storedType: 'unique_choice',
		widget: 'slider',
		label: 'Single choice (slider)',
		icon: SLIDER_ICON,
		color: 'text-violet-600 bg-violet-50'
	},
	// Row 4
	{
		value: 'multiple_choice',
		storedType: 'multiple_choice',
		widget: 'native',
		label: 'Multiple choice',
		icon: 'fa-square-check',
		color: 'text-purple-600 bg-purple-50'
	},
	{
		value: 'date',
		storedType: 'date',
		widget: 'native',
		label: 'Date',
		icon: 'fa-calendar',
		color: 'text-amber-600 bg-amber-50'
	}
];

/** Map from composite value to Font Awesome icon class. */
export const TYPE_ICONS: Record<string, string> = Object.fromEntries(
	QUESTION_TYPES.map((t) => [t.value, t.icon])
);

/** Map from composite value to Tailwind color classes. */
export const TYPE_COLORS: Record<string, string> = Object.fromEntries(
	QUESTION_TYPES.map((t) => [t.value, t.color])
);

/**
 * Derive the picker's composite key from a stored question. Slider questions
 * (any `type` with `config.widget === 'slider'`) map to `<type>:slider`.
 */
export function inferVariant(question: {
	type: string;
	config?: Record<string, unknown> | null;
}): string {
	if (question.config && (question.config as { widget?: unknown }).widget === 'slider') {
		return `${question.type}:slider`;
	}
	return question.type;
}

/**
 * Default `config` to write when the author picks a given variant. Native
 * variants store `null`; slider variants seed sensible defaults.
 */
export function defaultConfigFor(variant: string): Record<string, unknown> | null {
	if (variant === 'number:slider') return { widget: 'slider', min: 0, max: 100, step: 1 };
	if (variant === 'unique_choice:slider') return { widget: 'slider' };
	return null;
}

// ----- drag-and-drop helpers (F2) -----

export interface DragHandlers {
	readonly draggedIndex: number | null;
	handleDragStart: (index: number) => void;
	handleDragOver: (e: DragEvent) => void;
	handleDrop: (e: DragEvent, dropIndex: number) => void;
	handleDragEnd: () => void;
}

/**
 * Create a reusable set of drag-and-drop handlers for simple lists.
 * The `onReorder` callback receives `(fromIndex, toIndex)` so the caller
 * can decide how to persist the new order.
 */
export function createDragHandlers(
	onReorder: (fromIndex: number, toIndex: number) => void
): DragHandlers {
	const state = $state({ index: null as number | null });

	return {
		get draggedIndex() {
			return state.index;
		},
		handleDragStart(index: number) {
			state.index = index;
		},
		handleDragOver(e: DragEvent) {
			e.preventDefault();
		},
		handleDrop(e: DragEvent, dropIndex: number) {
			e.preventDefault();
			if (state.index === null || state.index === dropIndex) return;
			onReorder(state.index, dropIndex);
			state.index = null;
		},
		handleDragEnd() {
			state.index = null;
		}
	};
}

export interface HandleGatedDragHandlers {
	readonly draggedIndex: number | null;
	recordMousedown: (e: MouseEvent) => void;
	handleDragStart: (e: DragEvent, index: number) => void;
	handleDragOver: (e: DragEvent) => void;
	handleDrop: (e: DragEvent, dropIndex: number) => void;
	handleDragEnd: () => void;
}

/**
 * Like `createDragHandlers` but the drag only initiates when the mousedown
 * target (or an ancestor) matches `[data-drag-handle]`.
 */
export function createHandleGatedDragHandlers(
	onReorder: (fromIndex: number, toIndex: number) => void
): HandleGatedDragHandlers {
	const state = $state({ index: null as number | null });
	let lastMousedownTarget: EventTarget | null = null;

	return {
		get draggedIndex() {
			return state.index;
		},
		recordMousedown(e: MouseEvent) {
			lastMousedownTarget = e.target;
		},
		handleDragStart(e: DragEvent, index: number) {
			if (!(lastMousedownTarget as HTMLElement)?.closest('[data-drag-handle]')) {
				e.preventDefault();
				return;
			}
			state.index = index;
		},
		handleDragOver(e: DragEvent) {
			e.preventDefault();
		},
		handleDrop(e: DragEvent, dropIndex: number) {
			e.preventDefault();
			if (state.index === null || state.index === dropIndex) return;
			onReorder(state.index, dropIndex);
			state.index = null;
		},
		handleDragEnd() {
			state.index = null;
		}
	};
}

// ----- copy-to-clipboard helper (F3) -----

/**
 * Create a reactive copy-to-clipboard handler.
 * Returns `{ copied, copy }` where `copied` is a `$state` boolean that
 * auto-resets after 1500 ms and `copy(text)` writes to the clipboard.
 */
export function createCopyHandler(): { copied: boolean; copy: (text: string) => void } {
	let timer: ReturnType<typeof setTimeout> | undefined;
	const handler = $state({ copied: false });

	function copy(text: string) {
		navigator.clipboard.writeText(text);
		handler.copied = true;
		clearTimeout(timer);
		timer = setTimeout(() => (handler.copied = false), 1500);
	}

	return {
		get copied() {
			return handler.copied;
		},
		set copied(v: boolean) {
			handler.copied = v;
		},
		copy
	};
}
