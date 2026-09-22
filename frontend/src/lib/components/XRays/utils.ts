import { m } from '$paraglide/messages';
import { safeTranslate } from '$lib/utils/i18n';
import { toCamelCase } from '$lib/utils/locales';
import { formatDateOrDateTime } from '$lib/utils/datetime';
import { getLocale } from '$paraglide/runtime';

export type SeverityKey = 'errors' | 'warnings' | 'info';

export const SEVERITIES: {
	key: SeverityKey;
	label: () => string;
	preset: string;
	border: string;
	text: string;
	icon: string;
}[] = [
	{
		key: 'errors',
		label: () => m.errors(),
		preset: 'preset-tonal-error',
		border: 'border-error-500',
		text: 'text-error-600-400',
		icon: 'fa-bug'
	},
	{
		key: 'warnings',
		label: () => m.warnings(),
		preset: 'preset-tonal-warning',
		border: 'border-warning-500',
		text: 'text-warning-600-400',
		icon: 'fa-triangle-exclamation'
	},
	{
		key: 'info',
		label: () => m.info(),
		preset: 'preset-tonal-secondary',
		border: 'border-secondary-500',
		text: 'text-secondary-600-400',
		icon: 'fa-circle-info'
	}
];

type Column = { key: string; label: () => string; kind?: 'enum' | 'date' | 'priority' };

// Columns beyond the name, per object type. Keys match the metadata the
// backend puts on each issue's object.
export const ISSUE_COLUMNS: Record<string, Column[]> = {
	appliedcontrol: [
		{ key: 'status', label: () => m.status(), kind: 'enum' },
		{ key: 'eta', label: () => m.eta(), kind: 'date' },
		{ key: 'priority', label: () => m.priority(), kind: 'priority' }
	],
	riskscenario: [
		{ key: 'ref_id', label: () => m.refId() },
		{ key: 'treatment', label: () => m.treatment(), kind: 'enum' }
	],
	requirementassessment: [
		{ key: 'result', label: () => m.result(), kind: 'enum' },
		{ key: 'status', label: () => m.xRaysAssessmentStatus(), kind: 'enum' }
	],
	riskacceptance: [
		{ key: 'state', label: () => m.state(), kind: 'enum' },
		{ key: 'expiry_date', label: () => m.expiryDate(), kind: 'date' }
	]
};

// What a rule's occurrences actually are, so the count on an issue row reads
// "4 requirements" rather than a bare "4".
const OBJECT_LABELS: Record<string, () => string> = {
	appliedcontrol: () => m.appliedControls(),
	riskscenario: () => m.riskScenarios(),
	requirementassessment: () => m.requirements(),
	riskacceptance: () => m.riskAcceptances(),
	evidence: () => m.evidences()
};

export const occurrenceLabel = (objType: string, count: number): string => {
	const noun =
		OBJECT_LABELS[objType]?.() ?? (count === 1 ? m.xRaysOccurrence() : m.xRaysOccurrences());
	return `${count} ${noun.toLowerCase()}`;
};

export const formatCell = (value: any, kind: Column['kind']): string => {
	if (value === null || value === undefined || value === '') return '-';
	if (kind === 'date') return formatDateOrDateTime(String(value), getLocale()) ?? '-';
	if (kind === 'priority') return safeTranslate(`p${value}`);
	if (kind === 'enum') return safeTranslate(toCamelCase(String(value)));
	return String(value);
};

export interface Issue {
	msgid: string;
	objType: string;
	occurrences: { name: string; link: string; object: Record<string, any> }[];
}

export const aggregateIssuesByType = (
	rawIssues: any[] | undefined,
	assessmentType: string,
	assessmentId: string
): Issue[] => {
	if (!Array.isArray(rawIssues) || rawIssues.length === 0) {
		return [];
	}

	const grouped = new Map<string, Issue>();

	rawIssues.forEach((issue) => {
		if (!issue?.msgid || !issue?.object) {
			return; // Skip malformed issues
		}

		if (!grouped.has(issue.msgid)) {
			grouped.set(issue.msgid, {
				msgid: issue.msgid,
				objType: issue.obj_type ?? '',
				occurrences: []
			});
		}

		// If issue has a link, use it with /edit, otherwise link to the assessment
		const link = issue.link ? `/${issue.link}/edit` : `/${assessmentType}/${assessmentId}`;

		grouped.get(issue.msgid)!.occurrences.push({
			name: issue.object.name || '',
			link,
			object: issue.object
		});
	});

	return Array.from(grouped.values());
};

export const aggregateQualityChecks = (item: any): Record<SeverityKey, any[]> => {
	const result = {} as Record<SeverityKey, any[]>;

	SEVERITIES.forEach(({ key }) => {
		if (!item?.objects || typeof item.objects !== 'object') {
			result[key] = [];
			return;
		}
		result[key] = Object.entries(item.objects).reduce((acc: any[], [entryKey, value]: any) => {
			if (entryKey !== 'object' && value?.quality_check?.[key]) {
				acc = [...acc, ...value.quality_check[key]];
			}
			return acc;
		}, []);
	});

	return result;
};

export const hasVisibleIssues = (
	assessment: any,
	activeSeverities: Record<SeverityKey, boolean>
): boolean =>
	SEVERITIES.some(
		({ key }) => activeSeverities[key] && (assessment?.quality_check?.[key]?.length ?? 0) > 0
	);
