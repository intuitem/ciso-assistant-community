import { getLocale } from '$paraglide/runtime';

type Rule = {
	label?: string;
	annotation?: string;
	translations?: Record<string, { label?: string; annotation?: string }> | null;
};

/** A quick-form rule's label in the current language, falling back to the
 * library's own wording, then to its ref_id. */
export function ruleLabel(rule: Rule | null | undefined, refId: string): string {
	const tr = rule?.translations?.[getLocale()];
	return tr?.label || tr?.annotation || rule?.label || rule?.annotation || refId;
}
