import type { BuilderStore } from './builder-state';

export interface FocusedNodeInfo {
	nodeId: string;
	parent: string | null;
	siblingIndex: number;
}

let focused: FocusedNodeInfo | null = null;

export function setFocusedNode(info: FocusedNodeInfo | null) {
	focused = info;
}

export function getFocusedNode(): FocusedNodeInfo | null {
	return focused;
}

function isEditingText(target: EventTarget | null): boolean {
	if (!target) return false;
	const t = target as HTMLElement;
	return (
		t.tagName === 'INPUT' ||
		t.tagName === 'TEXTAREA' ||
		t.tagName === 'SELECT' ||
		t.isContentEditable === true
	);
}

export function installKeyboardHandlers(builder: BuilderStore): () => void {
	function onKey(e: KeyboardEvent) {
		if (!focused) return;

		// ⌘ / Ctrl + . — toggle assessable. Works even when focus is in a text input.
		if (e.key === '.' && (e.metaKey || e.ctrlKey) && !e.altKey && !e.shiftKey) {
			builder.toggleAssessable(focused.nodeId);
			e.preventDefault();
			return;
		}

		// All other shortcuts must NOT fire when the user is typing.
		if (isEditingText(e.target)) return;

		// Use e.code (physical key) rather than e.key — on macOS, the Option
		// modifier transforms Enter's e.key into a newline char and the arrow
		// keys into alternate symbols. e.code stays stable: 'Enter',
		// 'ArrowLeft', 'ArrowRight'.
		if (e.altKey && !e.shiftKey && !e.metaKey && !e.ctrlKey) {
			if (e.code === 'ArrowRight') {
				if (builder.indentNode(focused.nodeId)) e.preventDefault();
				return;
			}
			if (e.code === 'ArrowLeft') {
				if (builder.outdentNode(focused.nodeId)) e.preventDefault();
				return;
			}
			if (e.code === 'Enter' || e.code === 'NumpadEnter') {
				builder.addNode({ parent: focused.nodeId, preset: 'blank' });
				e.preventDefault();
				return;
			}
		}

		if (
			e.altKey &&
			e.shiftKey &&
			!e.metaKey &&
			!e.ctrlKey &&
			(e.code === 'Enter' || e.code === 'NumpadEnter')
		) {
			builder.addNode({
				parent: focused.parent,
				preset: 'blank',
				afterIndex: focused.siblingIndex
			});
			e.preventDefault();
		}
	}

	window.addEventListener('keydown', onKey);
	return () => window.removeEventListener('keydown', onKey);
}
