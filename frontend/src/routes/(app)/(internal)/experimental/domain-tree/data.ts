// Dummy dataset shaped like FrameworkViewSet.report rows, so swapping in the
// real endpoint later only means replacing generateDataset().

export type Result =
	'compliant' | 'partially_compliant' | 'non_compliant' | 'not_applicable' | 'not_assessed';

export interface Requirement {
	ref_id: string;
	section: string;
	implementation_groups: string[];
}

export interface Section {
	ref_id: string;
	name: string;
}

export interface Folder {
	id: string;
	name: string;
	parent_id: string | null;
}

export interface Audit {
	id: string;
	name: string;
	folder_id: string;
	status: 'in_progress' | 'in_review' | 'done';
	selected_implementation_groups: string[];
}

export interface Row {
	compliance_assessment_id: string;
	folder_id: string;
	requirement_ref_id: string;
	section: string;
	implementation_groups: string[];
	result: Result;
	score: number | null;
}

export interface Dataset {
	framework: { name: string; min_score: number; max_score: number };
	implementationGroups: string[];
	sections: Section[];
	requirements: Requirement[];
	folders: Folder[];
	audits: Audit[];
	rows: Row[];
}

const SECTIONS: [string, number][] = [
	['Inventory and Control of Enterprise Assets', 5],
	['Inventory and Control of Software Assets', 7],
	['Data Protection', 14],
	['Secure Configuration of Enterprise Assets and Software', 12],
	['Account Management', 6],
	['Access Control Management', 8],
	['Continuous Vulnerability Management', 7],
	['Audit Log Management', 12],
	['Email and Web Browser Protections', 7],
	['Malware Defenses', 7],
	['Data Recovery', 5],
	['Network Infrastructure Management', 8],
	['Network Monitoring and Defense', 11],
	['Security Awareness and Skills Training', 9],
	['Service Provider Management', 7],
	['Application Software Security', 14],
	['Incident Response Management', 9],
	['Penetration Testing', 5]
];

// Organisation-wide weak spots, so the section breakdown has a story to tell.
const SECTION_BIAS: Record<string, number> = {
	'3': -0.1,
	'7': -0.2,
	'13': -0.15,
	'16': -0.25,
	'18': -0.3,
	'5': 0.1,
	'14': 0.15
};

interface FolderSpec {
	id: string;
	name: string;
	parent: string | null;
	audit?: {
		maturity: number;
		progress: number;
		status: Audit['status'];
		igs?: string[];
	};
}

const FOLDERS: FolderSpec[] = [
	{ id: 'global', name: 'Global', parent: null },
	{
		id: 'group',
		name: 'Group',
		parent: 'global',
		audit: { maturity: 0.55, progress: 0.95, status: 'done' }
	},
	{
		id: 'it',
		name: 'IT department',
		parent: 'group',
		audit: { maturity: 0.6, progress: 0.9, status: 'in_review' }
	},
	{
		id: 'infra',
		name: 'Infrastructure',
		parent: 'it',
		audit: { maturity: 0.7, progress: 1, status: 'done' }
	},
	{
		id: 'workplace',
		name: 'Workplace',
		parent: 'it',
		audit: { maturity: 0.48, progress: 0.85, status: 'in_progress' }
	},
	{
		id: 'secops',
		name: 'Security operations',
		parent: 'it',
		audit: { maturity: 0.85, progress: 1, status: 'done' }
	},
	{ id: 'bu', name: 'Business units', parent: 'group' },
	{
		id: 'retail',
		name: 'Retail',
		parent: 'bu',
		audit: { maturity: 0.42, progress: 1, status: 'done', igs: ['IG1'] }
	},
	{
		id: 'manufacturing',
		name: 'Manufacturing',
		parent: 'bu',
		audit: { maturity: 0.3, progress: 0.8, status: 'in_progress', igs: ['IG1', 'IG2'] }
	},
	{
		id: 'lyon',
		name: 'Plant Lyon',
		parent: 'manufacturing',
		audit: { maturity: 0.34, progress: 0.6, status: 'in_progress', igs: ['IG1'] }
	},
	{ id: 'porto', name: 'Plant Porto', parent: 'manufacturing' },
	{
		id: 'iberia',
		name: 'Subsidiary Iberia',
		parent: 'global',
		audit: { maturity: 0.5, progress: 0.4, status: 'in_progress' }
	}
];

function mulberry32(seed: number) {
	return () => {
		seed |= 0;
		seed = (seed + 0x6d2b79f5) | 0;
		let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
		t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
		return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
	};
}

function buildRequirements(): { sections: Section[]; requirements: Requirement[] } {
	const sections: Section[] = [];
	const requirements: Requirement[] = [];
	SECTIONS.forEach(([name, count], i) => {
		const ref = String(i + 1);
		sections.push({ ref_id: ref, name });
		for (let j = 1; j <= count; j++) {
			// IGs are cumulative: an IG1 safeguard is also part of IG2 and IG3.
			const pos = j / count;
			const minIg = ref === '18' ? 2 : pos <= 0.4 ? 1 : pos <= 0.8 ? 2 : 3;
			const igs = ['IG1', 'IG2', 'IG3'].slice(minIg - 1);
			requirements.push({ ref_id: `${ref}.${j}`, section: ref, implementation_groups: igs });
		}
	});
	return { sections, requirements };
}

export function generateDataset(seed = 42): Dataset {
	const rand = mulberry32(seed);
	const { sections, requirements } = buildRequirements();
	const folders: Folder[] = FOLDERS.map((f) => ({ id: f.id, name: f.name, parent_id: f.parent }));
	const audits: Audit[] = [];
	const rows: Row[] = [];

	for (const f of FOLDERS) {
		if (!f.audit) continue;
		const a = f.audit;
		const audit: Audit = {
			id: `ca-${f.id}`,
			name: `CIS v8 — ${f.name}`,
			folder_id: f.id,
			status: a.status,
			selected_implementation_groups: a.igs ?? []
		};
		audits.push(audit);

		for (const req of requirements) {
			if (a.igs && !req.implementation_groups.some((g) => a.igs!.includes(g))) continue;
			let result: Result;
			let score: number | null = null;
			if (rand() > a.progress) {
				result = 'not_assessed';
			} else if (rand() < 0.04) {
				result = 'not_applicable';
			} else {
				const igPenalty = (3 - req.implementation_groups.length) * 0.08;
				const x = a.maturity + (SECTION_BIAS[req.section] ?? 0) - igPenalty + (rand() - 0.5) * 0.5;
				if (x > 0.5) {
					result = 'compliant';
					score = 4 + Math.round(rand());
				} else if (x > 0.28) {
					result = 'partially_compliant';
					score = 2 + Math.round(rand());
				} else {
					result = 'non_compliant';
					score = Math.round(rand());
				}
				if (rand() < 0.12) score = null;
			}
			rows.push({
				compliance_assessment_id: audit.id,
				folder_id: f.id,
				requirement_ref_id: req.ref_id,
				section: req.section,
				implementation_groups: req.implementation_groups,
				result,
				score
			});
		}
	}

	return {
		framework: { name: 'CIS Controls v8', min_score: 0, max_score: 5 },
		implementationGroups: ['IG1', 'IG2', 'IG3'],
		sections,
		requirements,
		folders,
		audits,
		rows
	};
}
