import { complianceResultColorMap } from '$lib/utils/constants';

export function formatStringToDate(inputString: string, locale = 'en') {
	const date = new Date(inputString);
	return date.toLocaleDateString(locale, {
		year: 'numeric',
		month: 'short',
		day: 'numeric'
	});
}

export const isURL = (url: string) => {
	try {
		const urlToCheck = new URL(url);
		if (urlToCheck.protocol !== 'http:' && urlToCheck.protocol !== 'https:') return false;
		return true;
	} catch (e) {
		return false;
	}
};

export function getRequirementTitle(ref_id: string, name: string) {
	const pattern = (ref_id ? 2 : 0) + (name ? 1 : 0);
	const title: string =
		pattern == 3 ? `${ref_id} - ${name}` : pattern == 2 ? ref_id : pattern == 1 ? name : '';
	return title;
}

export function displayScoreColor(
	value: number | null,
	max_score: number,
	inversedColors = false,
	min_score = 0
) {
	value ??= min_score;
	const range = max_score - min_score;
	value = range > 0 ? ((value - min_score) * 100) / range : 0;
	if (inversedColors) {
		if (value < 25) {
			return 'stroke-green-300';
		}
		if (value < 50) {
			return 'stroke-yellow-300';
		}
		if (value < 75) {
			return 'stroke-orange-400';
		}
		return 'stroke-red-400';
	} else {
		if (value < 25) {
			return 'stroke-red-400';
		}
		if (value < 50) {
			return 'stroke-orange-400';
		}
		if (value < 75) {
			return 'stroke-yellow-300';
		}
		return 'stroke-green-300';
	}
}

export function getScoreHexColor(
	value: number | null,
	max_score: number,
	inversedColors = false,
	min_score = 0
) {
	value ??= min_score;
	const range = max_score - min_score;
	const percentage = range > 0 ? ((value - min_score) * 100) / range : 0;
	// Tailwind color hex equivalents
	const colors = {
		red400: '#f87171',
		orange400: '#fb923c',
		yellow300: '#fde047',
		green300: '#86efac'
	};
	if (inversedColors) {
		if (percentage < 25) return colors.green300;
		if (percentage < 50) return colors.yellow300;
		if (percentage < 75) return colors.orange400;
		return colors.red400;
	} else {
		if (percentage < 25) return colors.red400;
		if (percentage < 50) return colors.orange400;
		if (percentage < 75) return colors.yellow300;
		return colors.green300;
	}
}

export function formatScoreValue(
	value: number,
	max_score: number,
	fullDonut = false,
	min_score = 0
) {
	if (value === null) {
		return 0;
	} else if (fullDonut) {
		return 100;
	}
	const range = max_score - min_score;
	if (range <= 0) {
		return 0;
	}
	const boundedValue = Math.max(min_score, Math.min(max_score, value));
	return ((boundedValue - min_score) * 100) / range;
}

export function getSecureRedirect(url: any): string {
	const SECURE_REDIRECT_URL_REGEX = /^\/\w+/;
	return typeof url === 'string' && SECURE_REDIRECT_URL_REGEX.test(url) ? url : '';
}

export function darkenColor(hex: string, amount: number) {
	hex = hex.slice(1);
	const num = parseInt(hex, 16);

	let r = (num >> 16) - amount * 255;
	let g = ((num >> 8) & 0x00ff) - amount * 255;
	let b = (num & 0x0000ff) - amount * 255;

	r = Math.max(0, Math.min(255, r));
	g = Math.max(0, Math.min(255, g));
	b = Math.max(0, Math.min(255, b));

	return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, '0')}`;
}

export function stringify(value: string | number | boolean | null = null) {
	return String(value)
		.toLowerCase()
		.normalize('NFD')
		.replace(/[\u0300-\u036f]/g, '');
}

export function isDark(hexcolor: string | undefined): boolean {
	if (!hexcolor) return false;
	const r = parseInt(hexcolor.slice(1, 3), 16);
	const g = parseInt(hexcolor.slice(3, 5), 16);
	const b = parseInt(hexcolor.slice(5, 7), 16);
	// compute brightness from rgb values
	// https://www.w3.org/tr/aert/#color-contrast
	const brightness = (r * 299 + g * 587 + b * 114) / 1000;
	return brightness < 128;
}

// Get the search key from an option object or the option itself
// if it's a string or number
export const getSearchTarget = (opt: Option): string => {
	// Handle primitive values (string/number)
	if (typeof opt === 'string' || typeof opt === 'number') {
		return String(opt).trim();
	}

	// Handle non-object types
	if (!opt || typeof opt !== 'object') {
		return '';
	}

	// Validate object structure
	if (opt.label === undefined) {
		const opt_str = JSON.stringify(opt);
		console.error(`MultiSelect option ${opt_str} is an object but has no label key`);
		return '';
	}

	// Build searchable components
	const components: string[] = [];

	// Add path information (hierarchical context)
	if (opt.path && Array.isArray(opt.path)) {
		const pathString = opt.path
			.filter(Boolean) // Remove empty/null values
			.map((item) => String(item).trim())
			.join(' ');
		if (pathString) {
			components.push(pathString);
		}
	}

	// Add main label (primary searchable content)
	const mainLabel = String(opt.label || '').trim();
	if (mainLabel) {
		components.push(mainLabel);
	}

	// Add translated label if different from main label
	if (opt.translatedLabel && opt.translatedLabel !== opt.label) {
		const translatedLabel = String(opt.translatedLabel).trim();
		if (translatedLabel && translatedLabel !== mainLabel) {
			components.push(translatedLabel);
		}
	}

	// Add value if it's different from label (for ID-based searches)
	if (opt.value !== undefined && opt.value !== opt.label) {
		const valueString = String(opt.value).trim();
		if (valueString && valueString !== mainLabel) {
			components.push(valueString);
		}
	}

	// Add info string content
	if (opt.infoString?.string) {
		const infoString = String(opt.infoString.string).trim();
		if (infoString) {
			components.push(infoString);
		}
	}

	// Combine all components with spaces
	const searchTarget = components.join(' ');

	// Normalize the search target
	return normalizeSearchString(searchTarget);
};

// Helper function to normalize search strings for better matching
export function normalizeSearchString(str: string): string {
	return str
		.toLowerCase()
		.normalize('NFD') // Decompose accented characters
		.replace(/\p{Diacritic}/gu, '') // Remove combining marks (diacritics)
		.replace(/[^\w\s-]/g, ' ') // Replace special chars with spaces
		.replace(/\s+/g, ' ') // Collapse multiple spaces
		.trim();
}

export function isQuestionVisible(
	question: any,
	answers: any,
	questions: Record<string, any> | null = null,
	visited: Set<string> = new Set()
): boolean {
	if (!question.depends_on) return true;

	const dependency = question.depends_on;
	const targetUrn = dependency.question;

	if (questions && targetUrn && !visited.has(targetUrn)) {
		const parent = questions[targetUrn];
		if (parent) {
			const nextVisited = new Set(visited);
			nextVisited.add(targetUrn);
			if (!isQuestionVisible(parent, answers, questions, nextVisited)) return false;
		}
	}

	const targetAnswer = answers[targetUrn];
	if (targetAnswer === undefined || targetAnswer === null) return false;

	// Mirror backend default: missing `condition` (e.g. hand-authored YAML)
	// is treated as "any".
	const condition = dependency.condition ?? 'any';

	if (condition === 'any') {
		if (Array.isArray(targetAnswer)) {
			return targetAnswer.some((a) => dependency.answers.includes(a));
		}
		return dependency.answers.includes(targetAnswer);
	}

	if (condition === 'all') {
		if (Array.isArray(targetAnswer)) {
			return dependency.answers.every((a: unknown) => targetAnswer.includes(a));
		}
		return dependency.answers.length === 1 && dependency.answers[0] === targetAnswer;
	}

	return false;
}

export function computeRequirementScoreAndResult(requirementAssessment: any, answers: any) {
	const questions = requirementAssessment.requirement.questions;

	if (!questions) return { score: null, result: null };

	const ca = requirementAssessment.compliance_assessment ?? {};
	const min_score = requirementAssessment.effective_min_score ?? ca.min_score ?? 0;
	const max_score = requirementAssessment.effective_max_score ?? ca.max_score ?? 100;

	const scoresDef = ca.scores_definition;
	let aggregation: 'sum' | 'mean' | null = null;
	if (scoresDef && typeof scoresDef === 'object') {
		if (scoresDef.aggregation === 'sum' || scoresDef.aggregation === 'mean') {
			aggregation = scoresDef.aggregation;
		}
	}
	if (!aggregation) {
		aggregation = ca.score_calculation_method === 'sum' ? 'sum' : 'mean';
	}

	let totalScore = 0;
	let totalWeight = 0;
	let isScoreComputed = false;
	const results: string[] = [];
	let visibleCount = 0;
	let answeredVisibleCount = 0;

	for (const [q_urn, question] of Object.entries<any>(questions)) {
		if (!isQuestionVisible(question, answers, questions)) continue;

		visibleCount++;

		const selectedChoiceURNs = answers?.[q_urn];
		const hasAnswer =
			selectedChoiceURNs !== undefined &&
			selectedChoiceURNs !== null &&
			!(typeof selectedChoiceURNs === 'string' && selectedChoiceURNs.trim() === '') &&
			!(Array.isArray(selectedChoiceURNs) && selectedChoiceURNs.length === 0);

		if (!hasAnswer) continue;

		answeredVisibleCount++;

		const choiceURNs = Array.isArray(selectedChoiceURNs)
			? selectedChoiceURNs
			: [selectedChoiceURNs];

		if (!question.choices || !Array.isArray(question.choices)) continue;

		const weight = typeof question.weight === 'number' ? question.weight : 1;

		for (const urn of choiceURNs) {
			const selectedChoice = question.choices.find((choice: any) => choice.urn === urn);
			if (!selectedChoice) continue;

			if (selectedChoice.add_score !== undefined && selectedChoice.add_score !== null) {
				isScoreComputed = true;
				totalScore += selectedChoice.add_score * weight;
				totalWeight += weight;
			}

			if (selectedChoice.compute_result !== undefined && selectedChoice.compute_result !== null) {
				const resolved = resolveComputeResult(selectedChoice.compute_result);
				if (resolved !== null) results.push(resolved);
			}
		}
	}

	let score: number | null;
	if (isScoreComputed) {
		const raw = aggregation === 'mean' && totalWeight > 0 ? totalScore / totalWeight : totalScore;
		score = Math.max(min_score, Math.min(max_score, Math.trunc(raw)));
	} else {
		score = null;
	}

	// A requirement is "result-driven" only if at least one choice carries a
	// resolvable compute_result. For score-only questionnaires we return
	// result=null so the edit page falls back to the manual result select.
	const isResultDriven = hasComputedResult(questions);

	let result: string | null;
	if (!isResultDriven) {
		result = null;
	} else if (visibleCount === 0) {
		result = 'not_applicable';
	} else if (answeredVisibleCount < visibleCount || results.length === 0) {
		result = 'not_assessed';
	} else {
		const aggregated = aggregateComputeResults(results);
		result = aggregated ?? 'not_assessed';
	}

	return { score, result };
}

/** Map a QuestionChoice.compute_result value to a Result string. */
export function resolveComputeResult(value: unknown): string | null {
	if (value === null || value === undefined) return null;
	if (typeof value === 'boolean') return value ? 'compliant' : 'non_compliant';
	if (typeof value !== 'string') return null;
	const v = value.trim().toLowerCase();
	if (v === '') return null;
	if (v === 'true' || v === '1' || v === 'compliant') return 'compliant';
	if (v === 'false' || v === '0' || v === 'non_compliant') return 'non_compliant';
	if (v === 'partially_compliant') return 'partially_compliant';
	if (v === 'not_applicable') return 'not_applicable';
	console.warn(`Unknown compute_result value ignored: "${value}"`);
	return null;
}

/** Aggregate resolved compute_result values: not_applicable is neutral, else worst-wins. */
function aggregateComputeResults(resolved: string[]): string | null {
	const contributing = resolved.filter((r) => r !== null && r !== undefined);
	if (contributing.length === 0) return null;

	const nonNA = contributing.filter((r) => r !== 'not_applicable');
	if (nonNA.length === 0) return 'not_applicable';

	const hasCompliant = nonNA.some((r) => r === 'compliant');
	const hasNonCompliant = nonNA.some((r) => r === 'non_compliant');
	const hasPartial = nonNA.some((r) => r === 'partially_compliant');

	if (hasPartial || (hasCompliant && hasNonCompliant)) return 'partially_compliant';
	if (hasNonCompliant) return 'non_compliant';
	return 'compliant';
}

/**
 * Field names that the CA-level visibility editor knows about.
 * The audit's `field_visibility` is the single source of truth at runtime.
 *
 * Storage shape: {fieldName: {role: 'edit' | 'read' | 'hidden'}}.
 * Roles known today: 'auditor', 'respondent'. A missing field key — or a
 * missing role within the pair — resolves to 'edit'.
 */
// Order matches the rendering sequence in the respondent (auditee) view.
export const VISIBILITY_FIELDS = [
	'answers',
	'respondent_alignment',
	'status',
	'result',
	'extended_result',
	'score',
	'documentation_score',
	'applied_controls',
	'evidences',
	'security_exceptions',
	'observation',
	'comments'
] as const;

export type VisibilityField = (typeof VISIBILITY_FIELDS)[number];

export type RoleAccess = 'edit' | 'read' | 'hidden';
export type VisibilityPair = { auditor: RoleAccess; respondent: RoleAccess };

const EDIT_PAIR: VisibilityPair = { auditor: 'edit', respondent: 'edit' };

/**
 * Return the per-role visibility pair for a field. The backend resolves the
 * full cascade (stored overrides + framework + DEFAULT_VISIBILITY) before
 * serializing `field_visibility`, so the map always carries an explicit pair
 * for every known field. A missing key here means a truly unknown/structural
 * field, which everyone may edit.
 */
export function resolveFieldVisibility(
	complianceAssessment: Record<string, any> | null | undefined,
	fieldName: string
): VisibilityPair {
	const raw = complianceAssessment?.field_visibility?.[fieldName];
	if (!raw || typeof raw !== 'object') return { ...EDIT_PAIR };
	return {
		auditor: (raw.auditor as RoleAccess) ?? 'edit',
		respondent: (raw.respondent as RoleAccess) ?? 'edit'
	};
}

function roleAccess(
	complianceAssessment: Record<string, any> | null | undefined,
	fieldName: string,
	role: 'auditor' | 'respondent'
): RoleAccess {
	return resolveFieldVisibility(complianceAssessment, fieldName)[role];
}

/** Whether a field is readable by the given role. */
export function isFieldVisible(
	complianceAssessment: Record<string, any> | null | undefined,
	fieldName: string,
	viewerRole: 'respondent' | 'auditor' = 'auditor'
): boolean {
	return roleAccess(complianceAssessment, fieldName, viewerRole) !== 'hidden';
}

/** Whether a field is writable by the given role. */
export function isFieldEditable(
	complianceAssessment: Record<string, any> | null | undefined,
	fieldName: string,
	viewerRole: 'respondent' | 'auditor' = 'auditor'
): boolean {
	return roleAccess(complianceAssessment, fieldName, viewerRole) === 'edit';
}

/**
 * Return visibility flags for all standard assessment fields at once.
 */
export function getFieldVisibility(
	complianceAssessment: Record<string, any> | null | undefined,
	viewerRole: 'respondent' | 'auditor' = 'auditor'
): {
	showAnswers: boolean;
	showResult: boolean;
	showStatus: boolean;
	showScore: boolean;
	showDocumentationScore: boolean;
	showObservation: boolean;
	showAppliedControls: boolean;
	showEvidences: boolean;
	showSecurityExceptions: boolean;
	showRespondentAlignment: boolean;
	showComments: boolean;
	showExtendedResult: boolean;
} {
	return {
		showAnswers: isFieldVisible(complianceAssessment, 'answers', viewerRole),
		showResult: isFieldVisible(complianceAssessment, 'result', viewerRole),
		showStatus: isFieldVisible(complianceAssessment, 'status', viewerRole),
		showScore: isFieldVisible(complianceAssessment, 'score', viewerRole),
		showDocumentationScore: isFieldVisible(complianceAssessment, 'documentation_score', viewerRole),
		showObservation: isFieldVisible(complianceAssessment, 'observation', viewerRole),
		showAppliedControls: isFieldVisible(complianceAssessment, 'applied_controls', viewerRole),
		showEvidences: isFieldVisible(complianceAssessment, 'evidences', viewerRole),
		showSecurityExceptions: isFieldVisible(complianceAssessment, 'security_exceptions', viewerRole),
		showRespondentAlignment: isFieldVisible(
			complianceAssessment,
			'respondent_alignment',
			viewerRole
		),
		showComments: isFieldVisible(complianceAssessment, 'comments', viewerRole),
		showExtendedResult: isFieldVisible(complianceAssessment, 'extended_result', viewerRole)
	};
}

/**
 * Check whether any question in a questions object has at least one choice with
 * a *resolvable* `compute_result`. Mirrors `resolveComputeResult`: empty strings,
 * whitespace, and unknown values are not treated as result-bearing, so a
 * questionnaire that only carries scoring (`add_score`) does not hide the manual
 * result select on the requirement edit page.
 */
export function hasComputedResult(questions: Record<string, any> | null | undefined): boolean {
	if (!questions) return false;
	return Object.values(questions).some(
		(question: any) =>
			Array.isArray(question.choices) &&
			question.choices.some((choice: any) => resolveComputeResult(choice?.compute_result) !== null)
	);
}

/**
 * Check whether any question in a questions object has choices with `add_score` defined.
 */
export function hasComputedScore(questions: Record<string, any> | null | undefined): boolean {
	if (!questions) return false;
	return Object.values(questions).some(
		(question: any) =>
			Array.isArray(question.choices) &&
			question.choices.some((choice: any) => choice.add_score !== undefined)
	);
}

// --- Auto-alignment question for respondent mode ---

export const AUTO_ALIGNMENT_QUESTION_URN = 'auto:alignment';

const AUTO_CHOICES = [
	{ id: 'yes', urn: 'auto:alignment:choice:yes', color: '#22c55e' },
	{ id: 'no', urn: 'auto:alignment:choice:no', color: '#ef4444' },
	{ id: 'in_progress', urn: 'auto:alignment:choice:in_progress', color: '#f59e0b' },
	{ id: 'not_applicable', urn: 'auto:alignment:choice:not_applicable', color: '#9ca3af' }
] as const;

export const alignmentColorMap: Record<string, string> = Object.fromEntries(
	AUTO_CHOICES.map((c) => [c.id, c.color])
);

/**
 * Build a synthetic question dict for the auto-alignment question.
 * Passed to Question.svelte as the `questions` prop.
 */
export function buildAutoAlignmentQuestion(translations: {
	text: string;
	yes: string;
	no: string;
	inProgress: string;
	notApplicable: string;
}) {
	return {
		[AUTO_ALIGNMENT_QUESTION_URN]: {
			type: 'unique_choice',
			text: translations.text,
			choices: [
				{ urn: AUTO_CHOICES[0].urn, value: translations.yes, color: AUTO_CHOICES[0].color },
				{ urn: AUTO_CHOICES[1].urn, value: translations.no, color: AUTO_CHOICES[1].color },
				{
					urn: AUTO_CHOICES[2].urn,
					value: translations.inProgress,
					color: AUTO_CHOICES[2].color
				},
				{
					urn: AUTO_CHOICES[3].urn,
					value: translations.notApplicable,
					color: AUTO_CHOICES[3].color
				}
			]
		}
	};
}

export function alignmentValueFromChoiceUrn(choiceUrn: string | null): string | null {
	if (!choiceUrn) return null;
	return AUTO_CHOICES.find((c) => c.urn === choiceUrn)?.id ?? null;
}

export function choiceUrnFromAlignmentValue(value: string | null): string | undefined {
	if (!value) return undefined;
	return AUTO_CHOICES.find((c) => c.id === value)?.urn;
}

/** Background + readable text color for a compliance-result badge. */
export function resultBadgeStyle(result: string | null | undefined): string {
	const key = result ?? 'not_assessed';
	const bg = complianceResultColorMap[key] || '#ddd';
	return `background-color: ${bg};${isDark(bg) ? ' color: white;' : ''}`;
}

/**
 * Whether the auto-alignment question should be shown for a given requirement.
 * Visible to respondents when respondent_alignment visibility includes them and
 * the requirement has no framework questions of its own.
 */
export function shouldShowAutoQuestion(
	requirement: Record<string, any>,
	viewerRole: string,
	ca: Record<string, any> | null | undefined
): boolean {
	if (viewerRole !== 'respondent') return false;
	const hasQuestions =
		requirement.questions != null && Object.keys(requirement.questions).length > 0;
	if (hasQuestions) return false;
	return isFieldEditable(ca, 'respondent_alignment', 'respondent');
}
