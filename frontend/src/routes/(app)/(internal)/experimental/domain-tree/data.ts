// Dummy generator emitting the DomainTreeFeed contract, so the real endpoint can
// replace generateFeed() without touching the view.
import type { CountTuple, DomainTreeFeed } from './feed';

export type FeedSize = 'small' | 'medium' | 'large';

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

const SIGNATURES = [['IG1', 'IG2', 'IG3'], ['IG2', 'IG3'], ['IG3']];

interface AuditSpec {
	maturity: number;
	progress: number;
	status: string;
	igs?: string[];
	hidden?: boolean;
	/** Share of answers whose requirement is marked done (status-driven progress). */
	doneShare?: number;
	scale?: [number, number];
}

interface FolderSpec {
	id: string;
	name: string;
	parent: string | null;
	viewable?: boolean;
	audit?: AuditSpec;
}

const SMALL: FolderSpec[] = [
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
		audit: { maturity: 0.48, progress: 0.85, status: 'in_progress', hidden: true }
	},
	{
		id: 'secops',
		name: 'Security operations',
		parent: 'it',
		audit: { maturity: 0.85, progress: 1, status: 'done' }
	},
	{ id: 'bu', name: 'Business units', parent: 'group', viewable: false },
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
		audit: {
			maturity: 0.3,
			progress: 0.8,
			status: 'in_progress',
			igs: ['IG1', 'IG2'],
			doneShare: 0.3
		}
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
		audit: { maturity: 0.5, progress: 0.4, status: 'in_progress', scale: [0, 100] }
	}
];

const LEVEL_NAMES = [
	['Subsidiary', 'Region', 'Division'],
	['IT', 'Finance', 'HR', 'Operations', 'Sales', 'R&D', 'Legal', 'Logistics'],
	['Site', 'Plant', 'Office', 'Team']
];
const PLACES = [
	'Lyon',
	'Porto',
	'Madrid',
	'Milan',
	'Berlin',
	'Ghent',
	'Krakow',
	'Dublin',
	'Austin',
	'Montreal',
	'Casablanca',
	'Singapore',
	'Tokyo',
	'Sydney',
	'Nairobi',
	'Lima'
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

function proceduralFolders(rand: () => number, target: number): FolderSpec[] {
	const pick = <T>(a: T[]) => a[Math.floor(rand() * a.length)];
	const folders: FolderSpec[] = [{ id: 'global', name: 'Global', parent: null }];
	const fanout = target > 100 ? [6, 6, 5] : [4, 4, 3];
	const grow = (parent: FolderSpec, depth: number, maturity: number) => {
		if (depth > 3 || folders.length >= target) return;
		const n = 1 + Math.floor(rand() * fanout[depth - 1]);
		for (let i = 0; i < n && folders.length < target; i++) {
			const m = Math.min(0.92, Math.max(0.15, maturity + (rand() - 0.5) * 0.35));
			const name =
				depth === 2
					? `${pick(LEVEL_NAMES[1])} ${parent.name.split(' ').pop()}`
					: `${pick(LEVEL_NAMES[depth - 1])} ${pick(PLACES)}`;
			const r = rand();
			const hasAudit = rand() < (depth === 1 ? 0.6 : 0.8);
			const f: FolderSpec = {
				id: `f${folders.length}`,
				name,
				parent: parent.id,
				viewable: hasAudit || rand() > 0.15,
				audit: hasAudit
					? {
							maturity: m,
							progress: 0.3 + rand() * 0.7,
							status: r < 0.5 ? 'done' : r < 0.7 ? 'in_review' : 'in_progress',
							igs: r < 0.6 ? undefined : r < 0.85 ? ['IG1'] : ['IG1', 'IG2']
						}
					: undefined
			};
			folders.push(f);
			grow(f, depth + 1, m);
		}
	};
	while (folders.length < target) grow(folders[0], 1, 0.5);
	return folders;
}

export function generateFeed(seed = 42, size: FeedSize = 'small'): DomainTreeFeed {
	const rand = mulberry32(seed);
	const all = size === 'small' ? SMALL : proceduralFolders(rand, size === 'medium' ? 60 : 200);
	// hidden domains are only sent when something viewable sits below them
	const keep = new Set<string>();
	const byId = new Map(all.map((f) => [f.id, f]));
	for (const f of all) {
		if (f.viewable === false) continue;
		for (let c: FolderSpec | undefined = f; c; c = c.parent ? byId.get(c.parent) : undefined)
			keep.add(c.id);
	}
	const specs = all.filter((f) => keep.has(f.id));

	const sections = SECTIONS.map(([name], i) => ({
		id: `sec-${i + 1}`,
		ref_id: String(i + 1),
		name
	}));
	// requirement → [section index, signature index]; IGs are cumulative in CIS
	const requirements: [number, number][] = [];
	SECTIONS.forEach(([, count], s) => {
		for (let j = 1; j <= count; j++) {
			const pos = j / count;
			const sig = s === 17 ? 1 : pos <= 0.4 ? 0 : pos <= 0.8 ? 1 : 2;
			requirements.push([s, sig]);
		}
	});
	const scopeMap = new Map<string, number>();
	for (const [s, g] of requirements)
		scopeMap.set(`${s}|${g}`, (scopeMap.get(`${s}|${g}`) ?? 0) + 1);
	const scope = [...scopeMap].map(([k, n]) => {
		const [s, g] = k.split('|').map(Number);
		return [s, g, n] as [number, number, number];
	});

	const audits: DomainTreeFeed['audits'] = [];
	const counts: CountTuple[] = [];
	for (const f of specs) {
		const a = f.audit;
		if (!a || f.viewable === false) continue;
		const [min, max] = a.scale ?? [0, 5];
		const ai = audits.length;
		audits.push({
			id: `ca-${f.id}`,
			name: `CIS v8 — ${f.name}`,
			folder_id: f.id,
			status: a.status,
			updated_at: new Date(Date.UTC(2026, 8, 1 + Math.floor(rand() * 30))).toISOString(),
			selected_implementation_groups: a.igs ?? [],
			results_hidden: !!a.hidden,
			score: null,
			progress: a.hidden ? null : Math.floor(a.progress * (a.doneShare ?? 1) * 100)
		});
		if (a.hidden) continue;
		const cells = new Map<string, CountTuple>();
		for (const [s, g] of requirements) {
			if (a.igs && !SIGNATURES[g].some((ig) => a.igs!.includes(ig))) continue;
			const key = `${s}|${g}`;
			let t = cells.get(key);
			if (!t) cells.set(key, (t = [ai, s, g, 0, 0, 0, 0, 0, 0, 0]));
			if (rand() > a.progress) {
				t[7]++;
				continue;
			}
			if (rand() < 0.04) {
				t[6]++;
				continue;
			}
			const igPenalty = (3 - SIGNATURES[g].length) * 0.08;
			const x = a.maturity + (SECTION_BIAS[String(s + 1)] ?? 0) - igPenalty + (rand() - 0.5) * 0.5;
			let level: number;
			if (x > 0.5) {
				t[3]++;
				level = 0.8 + rand() * 0.2;
			} else if (x > 0.28) {
				t[4]++;
				level = 0.4 + rand() * 0.2;
			} else {
				t[5]++;
				level = rand() * 0.2;
			}
			if (rand() < 0.88) {
				t[8] += (Math.round(min + level * (max - min)) - min) / (max - min);
				t[9]++;
			}
		}
		counts.push(...cells.values());
		const own = [...cells.values()].reduce((acc, c) => [acc[0] + c[8], acc[1] + c[9]], [0, 0]);
		audits[ai].score = own[1] ? Math.round((own[0] / own[1]) * 1000) / 10 : null;
	}

	return {
		framework: {
			id: 'fw-cis-v8',
			name: 'CIS Controls v8',
			implementation_groups: SIGNATURES[0].map((ig) => ({ ref_id: ig, name: ig }))
		},
		sections,
		signatures: SIGNATURES,
		scope,
		folders: specs.map((f) => ({
			id: f.id,
			name: f.viewable === false ? '' : f.name,
			parent_id: f.parent,
			viewable: f.viewable !== false
		})),
		audits,
		counts
	};
}
