// Constants shared across the workflow builder panels.
import { m } from '$paraglide/messages';

// Variable value kinds, offered wherever a variable's type is chosen.
export const VARIABLE_TYPES = ['string', 'number', 'boolean', 'date', 'json'];

// Version-status pill styling + label, shared by the canvas header and the
// versions panel.
export const STATUS_BADGE: Record<string, { class: string; label: () => string }> = {
	draft: { class: 'preset-tonal-warning', label: () => m.draftVersion() },
	published: { class: 'preset-tonal-success', label: () => m.publishedVersion() },
	archived: { class: 'preset-tonal', label: () => m.archivedVersion() }
};
