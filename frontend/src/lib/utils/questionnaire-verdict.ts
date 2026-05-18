// Canonical questionnaire verdict strings.
//
// Kept in sync with `backend/chat/constants.py::Verdict`. A typo in either
// place silently corrupts answers — the LLM emits these strings as JSON, the
// refiner reads them, the xlsx exporter maps them back to customer
// vocabulary, and the UI bands review on them. One source of truth on each
// side.

export const VERDICT = {
	YES: 'yes',
	PARTIAL: 'partial',
	NO: 'no',
	NEEDS_INFO: 'needs_info'
} as const;

export type Verdict = (typeof VERDICT)[keyof typeof VERDICT];

// Display order used in the stats breakdown bar.
export const VERDICT_ORDER: readonly Verdict[] = [
	VERDICT.YES,
	VERDICT.PARTIAL,
	VERDICT.NO,
	VERDICT.NEEDS_INFO
];
