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
 * (backend/core/templates/emails/{en,fr}/<key>.yaml); `label`, `category` and
 * `conditionBacked` are what those YAML files would gain, so the vocabulary stays in one
 * place instead of being pattern-matched off key suffixes.
 *
 * `conditionBacked` is a property of the type, not the row: a condition-backed type is one
 * a nightly sweep re-evaluates, so its rows carry a dedupeKey and can auto-clear. Event
 * types fire once and are append-only.
 */
export const EVENT_TYPES: Record<
	string,
	{ label: string; category: Category; conditionBacked: boolean }
> = {
	expired_controls: { label: 'Control past its ETA', category: 'deadlines', conditionBacked: true },
	task_node_overdue: { label: 'Task overdue', category: 'deadlines', conditionBacked: true },
	compliance_assessment_due_soon: {
		label: 'Audit due soon',
		category: 'deadlines',
		conditionBacked: true
	},
	evidence_expiring_soon: {
		label: 'Evidence expiring soon',
		category: 'expiry',
		conditionBacked: true
	},
	security_exception_expiring_soon: {
		label: 'Exception expiring soon',
		category: 'expiry',
		conditionBacked: true
	},
	validation_deadline: {
		label: 'Validation deadline',
		category: 'approvals',
		conditionBacked: true
	},
	policy_acknowledgement_due: {
		label: 'Policy needs acknowledgement',
		category: 'approvals',
		conditionBacked: true
	},
	applied_control_assignment: {
		label: 'Control assigned to you',
		category: 'assignments',
		conditionBacked: false
	},
	risk_scenario_assignment: {
		label: 'Risk scenario assigned to you',
		category: 'assignments',
		conditionBacked: false
	},
	validation_flow_created: {
		label: 'Added as approver',
		category: 'approvals',
		conditionBacked: false
	},
	questionnaire_assignment: {
		label: 'Questionnaire activity',
		category: 'questionnaires',
		conditionBacked: false
	}
};

/**
 * Mirrors the Notification model field for field, so the mock doubles as the API shape.
 * `welcome` / `welcome_sso` / `password_reset` are absent on purpose: they have no target,
 * so they stay email-only and never reach an inbox.
 */
export interface Notif {
	id: string;
	type: string; // == email template_key
	severity: 'info' | 'warning' | 'critical';
	title: string; // rendered from the template subject
	body: string; // rendered from the template body
	link: string; // destination, never null
	linkLabel: string;
	objectId: string; // GFK object_id — every in-app notification has a target
	folder: string; // FolderMixin — the domain the notification is about
	/** null = not tracking a condition: an event row, or one the sweep has auto-cleared */
	dedupeKey: string | null;
	seenCount: number;
	createdAt: string;
	lastSeenAt: string;
	isRead: boolean;
	autoClearedAt: string | null;
	/** where an attestation actually lives, when the notification needs one */
	attestation?: { label: string; link: string };
}

export const SEVERITY_META = {
	info: { dot: 'bg-sky-500' },
	warning: { dot: 'bg-amber-500' },
	critical: { dot: 'bg-rose-500' }
} as const;

export const categoryOf = (n: Notif): Category => EVENT_TYPES[n.type].category;
export const isConditionBacked = (n: Notif): boolean => EVENT_TYPES[n.type].conditionBacked;
/** What the sweep computes; equals dedupeKey while the row is tracking its condition. */
export const conditionKeyOf = (n: Notif): string => `${n.type}:${n.objectId}`;

const row = (
	n: Omit<Notif, 'dedupeKey' | 'seenCount' | 'lastSeenAt' | 'autoClearedAt'> &
		Partial<Pick<Notif, 'dedupeKey' | 'seenCount' | 'lastSeenAt' | 'autoClearedAt'>>
): Notif => ({
	seenCount: 1,
	lastSeenAt: n.createdAt,
	autoClearedAt: null,
	dedupeKey: EVENT_TYPES[n.type].conditionBacked ? `${n.type}:${n.objectId}` : null,
	...n
});

export const NOTIFICATIONS: Notif[] = [
	row({
		id: 'n1',
		type: 'expired_controls',
		severity: 'critical',
		title: 'Disk encryption on endpoints is past its ETA',
		body: 'The ETA was 2026-08-14. This reminder stops once the control is marked active or you update the ETA.',
		link: '/applied-controls/3f2a',
		linkLabel: 'Disk encryption on endpoints',
		objectId: '3f2a',
		folder: 'IT Operations',
		createdAt: '2026-08-15T06:00:00Z',
		seenCount: 30,
		lastSeenAt: '2026-09-14T06:00:00Z',
		isRead: false
	}),
	row({
		id: 'n2',
		type: 'task_node_overdue',
		severity: 'critical',
		title: 'Quarterly access review is overdue',
		body: 'Due 2026-09-01. Recurs every quarter.',
		link: '/task-nodes/8b1c',
		linkLabel: 'Quarterly access review — Q3',
		objectId: '8b1c',
		folder: 'IT Operations',
		createdAt: '2026-09-02T07:05:00Z',
		seenCount: 13,
		lastSeenAt: '2026-09-14T07:05:00Z',
		isRead: false
	}),
	row({
		id: 'n3',
		type: 'applied_control_assignment',
		severity: 'info',
		title: 'A. Rossi assigned you “MFA for admin accounts”',
		body: 'You are now the owner of this applied control.',
		link: '/applied-controls/91de',
		linkLabel: 'MFA for admin accounts',
		objectId: '91de',
		folder: 'IT Operations',
		createdAt: '2026-09-13T14:22:00Z',
		isRead: false
	}),
	row({
		id: 'n4',
		type: 'policy_acknowledgement_due',
		severity: 'warning',
		title: 'Acceptable Use Policy v4 needs your acknowledgement',
		body: 'Published 2026-09-08. Acknowledgement is recorded on the policy itself, not here.',
		link: '/policies/aup-v4',
		linkLabel: 'Acceptable Use Policy v4',
		objectId: 'aup-v4',
		folder: 'Global',
		attestation: { label: 'Acknowledge policy', link: '/policies/aup-v4/acknowledge' },
		createdAt: '2026-09-08T06:10:00Z',
		seenCount: 7,
		lastSeenAt: '2026-09-14T06:10:00Z',
		isRead: false
	}),
	// One row per evidence, not one digest row for all three: that is what makes
	// click-to-object universal and per-row read/delete meaningful.
	row({
		id: 'n5a',
		type: 'evidence_expiring_soon',
		severity: 'warning',
		title: 'Pentest report 2025 expires in 6 days',
		body: 'Expires 2026-09-20. Attached to 4 requirements in ISO 27001:2022.',
		link: '/evidences/a11f',
		linkLabel: 'Pentest report 2025',
		objectId: 'a11f',
		folder: 'IT Operations',
		createdAt: '2026-09-09T06:27:00Z',
		seenCount: 6,
		lastSeenAt: '2026-09-14T06:27:00Z',
		isRead: false
	}),
	row({
		id: 'n5b',
		type: 'evidence_expiring_soon',
		severity: 'warning',
		title: 'SOC 2 bridge letter expires in 3 days',
		body: 'Expires 2026-09-17. Supplied by Northwind.',
		link: '/evidences/b22c',
		linkLabel: 'SOC 2 bridge letter',
		objectId: 'b22c',
		folder: 'Third parties',
		createdAt: '2026-09-09T06:27:00Z',
		seenCount: 6,
		lastSeenAt: '2026-09-14T06:27:00Z',
		isRead: false
	}),
	row({
		id: 'n5c',
		type: 'evidence_expiring_soon',
		severity: 'warning',
		title: 'ISO 27001 certificate expires in 7 days',
		body: 'Expires 2026-09-21. Renewal audit booked for 2026-09-18.',
		link: '/evidences/c33d',
		linkLabel: 'ISO 27001 certificate',
		objectId: 'c33d',
		folder: 'Global',
		createdAt: '2026-09-09T06:27:00Z',
		seenCount: 6,
		lastSeenAt: '2026-09-14T06:27:00Z',
		isRead: true
	}),
	row({
		id: 'n6',
		type: 'validation_flow_created',
		severity: 'info',
		title: 'You were added as approver on “Q3 exception review”',
		body: 'Deadline 2026-09-20.',
		link: '/validation-flows/77ab',
		linkLabel: 'Q3 exception review',
		objectId: '77ab',
		folder: 'Global',
		createdAt: '2026-09-11T09:41:00Z',
		isRead: true
	}),
	row({
		id: 'n7',
		type: 'compliance_assessment_due_soon',
		severity: 'warning',
		title: 'ISO 27001:2022 internal audit is due in a week',
		body: 'Due 2026-09-21. You are the author.',
		link: '/compliance-assessments/12cd',
		linkLabel: 'ISO 27001:2022 internal audit',
		objectId: '12cd',
		folder: 'Global',
		createdAt: '2026-09-14T06:05:00Z',
		lastSeenAt: '2026-09-14T06:05:00Z',
		isRead: false
	}),
	// Auto-cleared: the sweep saw the ETA met, marked it read and released the dedupe key.
	row({
		id: 'n8',
		type: 'expired_controls',
		severity: 'critical',
		title: 'Backup restore test is past its ETA',
		body: 'The ETA was 2026-08-30.',
		link: '/applied-controls/44fa',
		linkLabel: 'Backup restore test',
		objectId: '44fa',
		folder: 'IT Operations',
		createdAt: '2026-08-31T06:00:00Z',
		seenCount: 12,
		lastSeenAt: '2026-09-11T06:00:00Z',
		isRead: true,
		dedupeKey: null,
		autoClearedAt: '2026-09-11T06:00:00Z'
	}),
	row({
		id: 'n9',
		type: 'security_exception_expiring_soon',
		severity: 'warning',
		title: 'Legacy TLS exception expires in a month',
		body: 'Expires 2026-10-12. You are the owner.',
		link: '/security-exceptions/5c9e',
		linkLabel: 'Legacy TLS on payment gateway',
		objectId: '5c9e',
		folder: 'Finance',
		createdAt: '2026-09-12T07:15:00Z',
		seenCount: 3,
		lastSeenAt: '2026-09-14T07:15:00Z',
		isRead: true
	}),
	row({
		id: 'n10',
		type: 'questionnaire_assignment',
		severity: 'info',
		title: 'Acme Corp submitted their security questionnaire',
		body: '48 of 52 questions answered.',
		link: '/entity-assessments/6d31',
		linkLabel: 'Acme Corp — 2026 due diligence',
		objectId: '6d31',
		folder: 'Third parties',
		createdAt: '2026-09-10T16:03:00Z',
		isRead: true
	}),
	row({
		id: 'n11',
		type: 'risk_scenario_assignment',
		severity: 'info',
		title: 'You now own risk scenario “Ransomware on file shares”',
		body: 'Part of the 2026 enterprise risk assessment.',
		link: '/risk-scenarios/2f77',
		linkLabel: 'Ransomware on file shares',
		objectId: '2f77',
		folder: 'Global',
		createdAt: '2026-09-05T11:18:00Z',
		isRead: true
	}),
	row({
		id: 'n12a',
		type: 'validation_deadline',
		severity: 'critical',
		title: 'Vendor onboarding — Northwind closes tomorrow',
		body: 'You are one of 2 approvers. Deadline 2026-09-15.',
		link: '/validation-flows/9a01',
		linkLabel: 'Vendor onboarding — Northwind',
		objectId: '9a01',
		folder: 'Third parties',
		createdAt: '2026-09-13T06:45:00Z',
		seenCount: 2,
		lastSeenAt: '2026-09-14T06:45:00Z',
		isRead: false
	}),
	row({
		id: 'n12b',
		type: 'validation_deadline',
		severity: 'critical',
		title: 'DPIA — HR analytics closes tomorrow',
		body: 'You are the sole approver. Deadline 2026-09-15.',
		link: '/validation-flows/9a02',
		linkLabel: 'DPIA — HR analytics',
		objectId: '9a02',
		folder: 'HR',
		createdAt: '2026-09-13T06:45:00Z',
		seenCount: 2,
		lastSeenAt: '2026-09-14T06:45:00Z',
		isRead: false
	}),
	row({
		id: 'n13',
		type: 'evidence_expiring_soon',
		severity: 'warning',
		title: 'Vulnerability scan — July expired',
		body: 'Expired 2026-09-03, replaced by the August scan.',
		link: '/evidences/d44e',
		linkLabel: 'Vulnerability scan — July',
		objectId: 'd44e',
		folder: 'IT Operations',
		createdAt: '2026-08-27T06:27:00Z',
		seenCount: 8,
		lastSeenAt: '2026-09-04T06:27:00Z',
		isRead: true,
		dedupeKey: null,
		autoClearedAt: '2026-09-04T06:27:00Z'
	})
];
