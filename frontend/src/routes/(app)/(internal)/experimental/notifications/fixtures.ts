export type Category = 'deadlines' | 'assignments' | 'approvals' | 'expiry' | 'questionnaires';

export const CATEGORY_META: Record<Category, { label: string; icon: string }> = {
	deadlines: { label: 'Deadlines', icon: 'fa-clock' },
	assignments: { label: 'Assignments', icon: 'fa-user-plus' },
	approvals: { label: 'Approvals', icon: 'fa-stamp' },
	expiry: { label: 'Expiry', icon: 'fa-hourglass-end' },
	questionnaires: { label: 'Questionnaires', icon: 'fa-clipboard-question' }
};

/**
 * The event-type registry. Keys are the existing email template names
 * (backend/core/templates/emails/{en,fr}/<key>.yaml); `label` and `category` are what
 * those YAML files would gain so the vocabulary stays in one place instead of being
 * pattern-matched off key suffixes.
 */
export const EVENT_TYPES: Record<string, { label: string; category: Category }> = {
	expired_controls: { label: 'Control past its ETA', category: 'deadlines' },
	task_node_overdue: { label: 'Task overdue', category: 'deadlines' },
	compliance_assessment_due_soon: { label: 'Audit due soon', category: 'deadlines' },
	applied_control_assignment: { label: 'Control assigned to you', category: 'assignments' },
	risk_scenario_assignment: { label: 'Risk scenario assigned to you', category: 'assignments' },
	evidence_expiring_soon: { label: 'Evidence expiring soon', category: 'expiry' },
	security_exception_expiring_soon: { label: 'Exception expiring soon', category: 'expiry' },
	validation_flow_created: { label: 'Added as approver', category: 'approvals' },
	validation_deadline: { label: 'Validation deadline', category: 'approvals' },
	policy_acknowledgement_due: { label: 'Policy needs acknowledgement', category: 'approvals' },
	questionnaire_assignment: { label: 'Questionnaire activity', category: 'questionnaires' }
};

export interface Notif {
	id: string;
	/** email template_key — carries the category and the filter label (see EVENT_TYPES) */
	type: string;
	severity: 'info' | 'warning' | 'critical';
	title: string;
	body: string;
	/** condition-backed rows are upserted and auto-clear; event rows are append-only */
	conditionBacked: boolean;
	/** non-nullable: every notification has a destination, even when it has no object */
	link: string;
	linkLabel: string;
	/** where an attestation actually lives, when the notification needs one */
	attestation?: { label: string; link: string };
	createdAt: string;
	/** condition-backed only: how many sweeps have re-observed the same condition */
	seenCount?: number;
	lastSeenAt?: string;
	isRead: boolean;
	/** set when the sweep observed the condition go away and marked the row read itself */
	autoCleared?: boolean;
}

export const SEVERITY_META = {
	info: { dot: 'bg-sky-500', text: 'text-sky-700 dark:text-sky-300' },
	warning: { dot: 'bg-amber-500', text: 'text-amber-700 dark:text-amber-300' },
	critical: { dot: 'bg-rose-500', text: 'text-rose-700 dark:text-rose-300' }
} as const;

export const categoryOf = (n: Notif): Category => EVENT_TYPES[n.type].category;

export const NOTIFICATIONS: Notif[] = [
	{
		id: 'n1',
		type: 'expired_controls',
		severity: 'critical',
		title: 'Disk encryption on endpoints is past its ETA',
		body: 'The ETA was 2026-08-14. This reminder stops once the control is marked active or you update the ETA.',
		conditionBacked: true,
		link: '/applied-controls/3f2a',
		linkLabel: 'Disk encryption on endpoints',
		createdAt: '2026-08-15T06:00:00Z',
		seenCount: 30,
		lastSeenAt: '2026-09-14T06:00:00Z',
		isRead: false
	},
	{
		id: 'n2',
		type: 'task_node_overdue',
		severity: 'critical',
		title: 'Quarterly access review is overdue',
		body: 'Due 2026-09-01. Recurs every quarter.',
		conditionBacked: true,
		link: '/task-nodes/8b1c',
		linkLabel: 'Quarterly access review — Q3',
		createdAt: '2026-09-02T07:05:00Z',
		seenCount: 13,
		lastSeenAt: '2026-09-14T07:05:00Z',
		isRead: false
	},
	{
		id: 'n3',
		type: 'applied_control_assignment',
		severity: 'info',
		title: 'A. Rossi assigned you “MFA for admin accounts”',
		body: 'You are now the owner of this applied control.',
		conditionBacked: false,
		link: '/applied-controls/91de',
		linkLabel: 'MFA for admin accounts',
		createdAt: '2026-09-13T14:22:00Z',
		isRead: false
	},
	{
		id: 'n4',
		type: 'policy_acknowledgement_due',
		severity: 'warning',
		title: 'Acceptable Use Policy v4 needs your acknowledgement',
		body: 'Published 2026-09-08. Acknowledgement is recorded on the policy itself, not here.',
		conditionBacked: true,
		link: '/policies/aup-v4',
		linkLabel: 'Acceptable Use Policy v4',
		attestation: { label: 'Acknowledge policy', link: '/policies/aup-v4/acknowledge' },
		createdAt: '2026-09-08T06:10:00Z',
		seenCount: 7,
		lastSeenAt: '2026-09-14T06:10:00Z',
		isRead: false
	},
	// Was one digest row ("3 evidences expire within a week"). Per-object is what makes
	// click-to-object universal and per-row read/delete meaningful — at the cost of 3 rows.
	{
		id: 'n5a',
		type: 'evidence_expiring_soon',
		severity: 'warning',
		title: 'Pentest report 2025 expires in 6 days',
		body: 'Expires 2026-09-20. Attached to 4 requirements in ISO 27001:2022.',
		conditionBacked: true,
		link: '/evidences/a11f',
		linkLabel: 'Pentest report 2025',
		createdAt: '2026-09-09T06:27:00Z',
		seenCount: 6,
		lastSeenAt: '2026-09-14T06:27:00Z',
		isRead: false
	},
	{
		id: 'n5b',
		type: 'evidence_expiring_soon',
		severity: 'warning',
		title: 'SOC 2 bridge letter expires in 3 days',
		body: 'Expires 2026-09-17. Supplied by Northwind.',
		conditionBacked: true,
		link: '/evidences/b22c',
		linkLabel: 'SOC 2 bridge letter',
		createdAt: '2026-09-09T06:27:00Z',
		seenCount: 6,
		lastSeenAt: '2026-09-14T06:27:00Z',
		isRead: false
	},
	{
		id: 'n5c',
		type: 'evidence_expiring_soon',
		severity: 'warning',
		title: 'ISO 27001 certificate expires in 7 days',
		body: 'Expires 2026-09-21. Renewal audit booked for 2026-09-18.',
		conditionBacked: true,
		link: '/evidences/c33d',
		linkLabel: 'ISO 27001 certificate',
		createdAt: '2026-09-09T06:27:00Z',
		seenCount: 6,
		lastSeenAt: '2026-09-14T06:27:00Z',
		isRead: true
	},
	{
		id: 'n6',
		type: 'validation_flow_created',
		severity: 'info',
		title: 'You were added as approver on “Q3 exception review”',
		body: 'Deadline 2026-09-20.',
		conditionBacked: false,
		link: '/validation-flows/77ab',
		linkLabel: 'Q3 exception review',
		createdAt: '2026-09-11T09:41:00Z',
		isRead: true
	},
	{
		id: 'n7',
		type: 'compliance_assessment_due_soon',
		severity: 'warning',
		title: 'ISO 27001:2022 internal audit is due in a week',
		body: 'Due 2026-09-21. You are the author.',
		conditionBacked: true,
		link: '/compliance-assessments/12cd',
		linkLabel: 'ISO 27001:2022 internal audit',
		createdAt: '2026-09-14T06:05:00Z',
		seenCount: 1,
		lastSeenAt: '2026-09-14T06:05:00Z',
		isRead: false
	},
	{
		id: 'n8',
		type: 'expired_controls',
		severity: 'critical',
		title: 'Backup restore test is past its ETA',
		body: 'The ETA was 2026-08-30.',
		conditionBacked: true,
		link: '/applied-controls/44fa',
		linkLabel: 'Backup restore test',
		createdAt: '2026-08-31T06:00:00Z',
		seenCount: 12,
		lastSeenAt: '2026-09-11T06:00:00Z',
		isRead: true,
		autoCleared: true
	},
	{
		id: 'n9',
		type: 'security_exception_expiring_soon',
		severity: 'warning',
		title: 'Legacy TLS exception expires in a month',
		body: 'Expires 2026-10-12. You are the owner.',
		conditionBacked: true,
		link: '/security-exceptions/5c9e',
		linkLabel: 'Legacy TLS on payment gateway',
		createdAt: '2026-09-12T07:15:00Z',
		seenCount: 3,
		lastSeenAt: '2026-09-14T07:15:00Z',
		isRead: true
	},
	{
		id: 'n10',
		type: 'questionnaire_assignment',
		severity: 'info',
		title: 'Acme Corp submitted their security questionnaire',
		body: '48 of 52 questions answered.',
		conditionBacked: false,
		link: '/entity-assessments/6d31',
		linkLabel: 'Acme Corp — 2026 due diligence',
		createdAt: '2026-09-10T16:03:00Z',
		isRead: true
	},
	{
		id: 'n11',
		type: 'risk_scenario_assignment',
		severity: 'info',
		title: 'You now own risk scenario “Ransomware on file shares”',
		body: 'Part of the 2026 enterprise risk assessment.',
		conditionBacked: false,
		link: '/risk-scenarios/2f77',
		linkLabel: 'Ransomware on file shares',
		createdAt: '2026-09-05T11:18:00Z',
		isRead: true
	},
	// Was "2 validations are waiting on you", likewise split.
	{
		id: 'n12a',
		type: 'validation_deadline',
		severity: 'critical',
		title: 'Vendor onboarding — Northwind closes tomorrow',
		body: 'You are one of 2 approvers. Deadline 2026-09-15.',
		conditionBacked: true,
		link: '/validation-flows/9a01',
		linkLabel: 'Vendor onboarding — Northwind',
		createdAt: '2026-09-13T06:45:00Z',
		seenCount: 2,
		lastSeenAt: '2026-09-14T06:45:00Z',
		isRead: false
	},
	{
		id: 'n12b',
		type: 'validation_deadline',
		severity: 'critical',
		title: 'DPIA — HR analytics closes tomorrow',
		body: 'You are the sole approver. Deadline 2026-09-15.',
		conditionBacked: true,
		link: '/validation-flows/9a02',
		linkLabel: 'DPIA — HR analytics',
		createdAt: '2026-09-13T06:45:00Z',
		seenCount: 2,
		lastSeenAt: '2026-09-14T06:45:00Z',
		isRead: false
	},
	{
		id: 'n13',
		type: 'evidence_expiring_soon',
		severity: 'warning',
		title: 'Vulnerability scan — July expired',
		body: 'Expired 2026-09-03, replaced by the August scan.',
		conditionBacked: true,
		link: '/evidences/d44e',
		linkLabel: 'Vulnerability scan — July',
		createdAt: '2026-08-27T06:27:00Z',
		seenCount: 8,
		lastSeenAt: '2026-09-04T06:27:00Z',
		isRead: true,
		autoCleared: true
	}
];
