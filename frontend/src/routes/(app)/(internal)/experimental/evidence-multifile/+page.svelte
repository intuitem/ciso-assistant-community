<script lang="ts">
	import { pageTitle } from '$lib/utils/stores';

	$pageTitle = 'Multi-file evidence (prototype)';

	type FileEntry = {
		name: string;
		size: number;
		hash: string;
		mime: string;
	};

	type RevStatus = 'draft' | 'in_review' | 'approved' | 'rejected';

	type Revision = {
		version: number;
		uploadedAt: string;
		uploadedBy: string;
		status: RevStatus;
		reviewedAt?: string;
		reviewedBy?: string;
		reviewComment?: string;
		observation: string;
		link?: string;
		files: FileEntry[];
	};

	const fmtSize = (n: number) =>
		n < 1024
			? `${n} B`
			: n < 1024 * 1024
				? `${(n / 1024).toFixed(1)} KB`
				: `${(n / 1024 / 1024).toFixed(1)} MB`;

	const short = (h: string) => `${h.slice(0, 6)}…${h.slice(-4)}`;

	const totalSize = (files: FileEntry[]) => files.reduce((s, f) => s + f.size, 0);

	const manifestHash = (files: FileEntry[]) => {
		const sorted = [...files].map((f) => f.hash).sort();
		return sorted.length === 0
			? '∅'
			: `${sorted[0].slice(0, 4)}${sorted[sorted.length - 1].slice(0, 4)}…m${sorted.length}`;
	};

	const evidence = {
		name: 'Q1 2026 Access Review',
		owner: 'Alice Martin',
		expiry: '2026-06-30',
		labels: ['SOC2', 'Annual', 'IAM']
	};

	const revisions: Revision[] = [
		{
			version: 1,
			uploadedAt: '2026-01-10',
			uploadedBy: 'Alice Martin',
			status: 'approved',
			reviewedAt: '2026-01-15',
			reviewedBy: 'Carla Reyes',
			reviewComment: 'Looks good for an initial baseline.',
			observation: 'Initial submission for Q1 access review.',
			files: [
				{
					name: 'access-review-summary.pdf',
					size: 2_140_000,
					hash: 'e4a91c2f8b3d4a91c2f8b3d4a91c2f8b3d4a91c2f8b3d4a91c2f8b3d4a91c2f8',
					mime: 'application/pdf'
				},
				{
					name: 'user-list-q1.xlsx',
					size: 4_600_000,
					hash: 'c27dabcdc27dabcdc27dabcdc27dabcdc27dabcdc27dabcdc27dabcdc27dabcd',
					mime: 'application/vnd.openxmlformats'
				}
			]
		},
		{
			version: 2,
			uploadedAt: '2026-02-12',
			uploadedBy: 'Bob Singh',
			status: 'rejected',
			reviewedAt: '2026-02-18',
			reviewedBy: 'Carla Reyes',
			reviewComment:
				'Narrative DOCX is unsigned and not auditable. Please replace with the raw ticket export.',
			observation: 'Added draft remediation plan; auditor wanted a narrative document.',
			files: [
				{
					name: 'access-review-summary.pdf',
					size: 2_140_000,
					hash: 'e4a91c2f8b3d4a91c2f8b3d4a91c2f8b3d4a91c2f8b3d4a91c2f8b3d4a91c2f8',
					mime: 'application/pdf'
				},
				{
					name: 'user-list-q1.xlsx',
					size: 4_600_000,
					hash: 'c27dabcdc27dabcdc27dabcdc27dabcdc27dabcdc27dabcdc27dabcdc27dabcd',
					mime: 'application/vnd.openxmlformats'
				},
				{
					name: 'draft-summary.docx',
					size: 320_000,
					hash: '7711aabb7711aabb7711aabb7711aabb7711aabb7711aabb7711aabb7711aabb',
					mime: 'application/vnd.openxmlformats'
				}
			]
		},
		{
			version: 3,
			uploadedAt: '2026-03-20',
			uploadedBy: 'Bob Singh',
			status: 'approved',
			reviewedAt: '2026-03-22',
			reviewedBy: 'Carla Reyes',
			reviewComment: 'Ticket export covers the audit period. Approved.',
			observation: 'Replaced draft narrative with the ticket export auditor requested.',
			files: [
				{
					name: 'access-review-summary.pdf',
					size: 2_140_000,
					hash: 'e4a91c2f8b3d4a91c2f8b3d4a91c2f8b3d4a91c2f8b3d4a91c2f8b3d4a91c2f8',
					mime: 'application/pdf'
				},
				{
					name: 'user-list-q1.xlsx',
					size: 4_600_000,
					hash: 'c27dabcdc27dabcdc27dabcdc27dabcdc27dabcdc27dabcdc27dabcdc27dabcd',
					mime: 'application/vnd.openxmlformats'
				},
				{
					name: 'ticket-export.csv',
					size: 1_500_000,
					hash: '9a12ef549a12ef549a12ef549a12ef549a12ef549a12ef549a12ef549a12ef54',
					mime: 'text/csv'
				}
			]
		},
		{
			version: 4,
			uploadedAt: '2026-04-15',
			uploadedBy: 'Alice Martin',
			status: 'in_review',
			observation:
				'Added remediation log for 3 stale accounts found during review. Refreshed user list with end-of-quarter snapshot.',
			link: 'https://confluence.example.com/x/access-review-q1',
			files: [
				{
					name: 'access-review-summary.pdf',
					size: 2_140_000,
					hash: 'e4a91c2f8b3d4a91c2f8b3d4a91c2f8b3d4a91c2f8b3d4a91c2f8b3d4a91c2f8',
					mime: 'application/pdf'
				},
				{
					name: 'user-list-q1.xlsx',
					size: 4_810_000,
					hash: 'd9ff0011d9ff0011d9ff0011d9ff0011d9ff0011d9ff0011d9ff0011d9ff0011',
					mime: 'application/vnd.openxmlformats'
				},
				{
					name: 'ticket-export.csv',
					size: 1_500_000,
					hash: '9a12ef549a12ef549a12ef549a12ef549a12ef549a12ef549a12ef549a12ef54',
					mime: 'text/csv'
				},
				{
					name: 'remediation-log.pdf',
					size: 4_010_000,
					hash: '11f3aabb11f3aabb11f3aabb11f3aabb11f3aabb11f3aabb11f3aabb11f3aabb',
					mime: 'application/pdf'
				}
			]
		}
	];

	const current = revisions[revisions.length - 1];

	type DiffRow = {
		state: 'added' | 'removed' | 'replaced' | 'unchanged';
		name: string;
		from?: FileEntry;
		to?: FileEntry;
	};

	function diff(base: Revision | null, target: Revision): DiffRow[] {
		const baseFiles = base ? base.files : [];
		const baseByName = new Map(baseFiles.map((f) => [f.name, f]));
		const targetByName = new Map(target.files.map((f) => [f.name, f]));
		const allNames = new Set<string>([...baseByName.keys(), ...targetByName.keys()]);

		const rows: DiffRow[] = [];
		for (const name of allNames) {
			const from = baseByName.get(name);
			const to = targetByName.get(name);
			if (from && to) {
				rows.push({
					state: from.hash === to.hash ? 'unchanged' : 'replaced',
					name,
					from,
					to
				});
			} else if (to) {
				rows.push({ state: 'added', name, to });
			} else if (from) {
				rows.push({ state: 'removed', name, from });
			}
		}
		const order: Record<DiffRow['state'], number> = {
			added: 0,
			replaced: 1,
			removed: 2,
			unchanged: 3
		};
		return rows.sort((a, b) => order[a.state] - order[b.state] || a.name.localeCompare(b.name));
	}

	function diffSummary(rows: DiffRow[]) {
		const c = { added: 0, replaced: 0, removed: 0, unchanged: 0 };
		for (const r of rows) c[r.state]++;
		return c;
	}

	const stateColor: Record<DiffRow['state'], string> = {
		added: 'text-green-700 bg-green-50 border-green-200',
		replaced: 'text-amber-700 bg-amber-50 border-amber-200',
		removed: 'text-red-700 bg-red-50 border-red-200',
		unchanged: 'text-gray-500 bg-gray-50 border-gray-200'
	};

	const stateLabel: Record<DiffRow['state'], string> = {
		added: 'new',
		replaced: 'replaced',
		removed: 'removed',
		unchanged: 'unchanged'
	};

	const stateGlyph: Record<DiffRow['state'], string> = {
		added: '+',
		replaced: '~',
		removed: '−',
		unchanged: '='
	};

	const statusStyle: Record<RevStatus, string> = {
		draft: 'bg-gray-100 text-gray-700 border-gray-300',
		in_review: 'bg-amber-100 text-amber-800 border-amber-300',
		approved: 'bg-green-100 text-green-800 border-green-300',
		rejected: 'bg-red-100 text-red-800 border-red-300'
	};
	const statusLabel: Record<RevStatus, string> = {
		draft: 'Draft',
		in_review: 'In review',
		approved: 'Approved',
		rejected: 'Rejected'
	};
	const statusIcon: Record<RevStatus, string> = {
		draft: 'fa-pencil',
		in_review: 'fa-hourglass-half',
		approved: 'fa-circle-check',
		rejected: 'fa-circle-xmark'
	};

	// Instance-level setting: whether new revisions go through a formal review cycle.
	// OFF (default): every new revision is auto-approved with the uploader as their own reviewer.
	// ON: new revisions land as in_review and need an explicit Approve/Reject.
	let instanceRequiresReview = $state(false);

	function displayRev(rev: Revision): Revision {
		if (instanceRequiresReview) return rev;
		// Auto-approve transform: the upload itself is the moment of approval.
		return {
			...rev,
			status: 'approved',
			reviewedBy: rev.uploadedBy,
			reviewedAt: rev.uploadedAt,
			reviewComment: undefined
		};
	}

	const displayCurrent = $derived(displayRev(revisions[revisions.length - 1]));
	const lastApproved = $derived(
		[...revisions]
			.reverse()
			.map(displayRev)
			.find((r) => r.status === 'approved') ?? null
	);

	let tab = $state<'current' | 'history' | 'compare' | 'new'>('history');
	let baseVersion = $state<number>(2);
	let targetVersion = $state<number>(4);
	let showUnchanged = $state(true);

	// "New revision" mockup state: per-file action against the current revision.
	type DraftAction = 'keep' | 'replace' | 'remove';
	type DraftEntry = {
		name: string;
		baseSize: number;
		baseHash: string;
		action: DraftAction;
		newSize?: number;
		newHash?: string;
	};

	let draftEntries = $state<DraftEntry[]>(
		current.files.map((f) => ({
			name: f.name,
			baseSize: f.size,
			baseHash: f.hash,
			action: 'keep'
		}))
	);
	// Pre-seed a couple of operations to demonstrate the four states.
	draftEntries[1] = {
		...draftEntries[1],
		action: 'replace',
		newSize: 5_120_000,
		newHash: 'aa00bb11aa00bb11aa00bb11aa00bb11aa00bb11aa00bb11aa00bb11aa00bb11'
	};
	draftEntries[3] = { ...draftEntries[3], action: 'remove' };

	let draftAdditions = $state<{ name: string; size: number; hash: string }[]>([
		{
			name: 'incident-followup.pdf',
			size: 980_000,
			hash: 'cc55dd66cc55dd66cc55dd66cc55dd66cc55dd66cc55dd66cc55dd66cc55dd66'
		}
	]);
	let draftObservation = $state(
		'Replaced user list with end-of-quarter snapshot; removed superseded remediation log; added Q2 incident follow-up.'
	);

	// Client-side hashing (Web Crypto) — what enables true wire-level dedup.
	let fileInput: HTMLInputElement | null = $state(null);
	let hashing = $state<{ name: string; progress: 'hashing' | 'done' | 'duplicate' | 'replaced' }[]>(
		[]
	);

	async function hashFile(file: File): Promise<string> {
		const buf = await file.arrayBuffer();
		const hashBuf = await crypto.subtle.digest('SHA-256', buf);
		return Array.from(new Uint8Array(hashBuf))
			.map((b) => b.toString(16).padStart(2, '0'))
			.join('');
	}

	async function handleFiles(files: FileList) {
		const newRecords = Array.from(files).map((f) => ({
			name: f.name,
			progress: 'hashing' as const
		}));
		hashing = [...hashing, ...newRecords];

		for (let i = 0; i < files.length; i++) {
			const file = files[i];
			const hash = await hashFile(file);
			const recordIdx = hashing.length - newRecords.length + i;

			// 1. Same name as an inherited file?
			const sameNameIdx = draftEntries.findIndex((e) => e.name === file.name);
			if (sameNameIdx >= 0) {
				const e = draftEntries[sameNameIdx];
				if (e.baseHash === hash) {
					// Bit-identical content → no-op. Still inherited; nothing to upload.
					hashing[recordIdx] = { ...hashing[recordIdx], progress: 'duplicate' };
					continue;
				}
				// Same name, different content → auto-promote to Replace.
				draftEntries[sameNameIdx] = {
					...e,
					action: 'replace',
					newSize: file.size,
					newHash: hash
				};
				hashing[recordIdx] = { ...hashing[recordIdx], progress: 'replaced' };
				continue;
			}

			// 2. Same hash as an inherited file (different name)? Still add as new — we don't
			//    auto-rename — but flag it so the user can decide.
			// 3. Otherwise: a genuinely new file.
			draftAdditions = [...draftAdditions, { name: file.name, size: file.size, hash }];
			hashing[recordIdx] = { ...hashing[recordIdx], progress: 'done' };
		}
	}

	function onDrop(e: DragEvent) {
		e.preventDefault();
		if (e.dataTransfer?.files?.length) handleFiles(e.dataTransfer.files);
	}

	function setAction(idx: number, action: DraftAction) {
		const e = draftEntries[idx];
		if (action === 'replace' && e.action !== 'replace') {
			// fake a replacement
			draftEntries[idx] = {
				...e,
				action,
				newSize: Math.round(e.baseSize * (0.85 + Math.random() * 0.4)),
				newHash: 'ffeeddccbbaa9988ffeeddccbbaa9988ffeeddccbbaa9988ffeeddccbbaa9988'
			};
		} else {
			draftEntries[idx] = { ...e, action, newSize: undefined, newHash: undefined };
		}
	}

	const draftPreview = $derived.by(() => {
		const inherited = draftEntries.filter((e) => e.action === 'keep');
		const replaced = draftEntries.filter((e) => e.action === 'replace');
		const removed = draftEntries.filter((e) => e.action === 'remove');
		const finalFiles: FileEntry[] = [
			...inherited.map((e) => ({
				name: e.name,
				size: e.baseSize,
				hash: e.baseHash,
				mime: ''
			})),
			...replaced.map((e) => ({
				name: e.name,
				size: e.newSize!,
				hash: e.newHash!,
				mime: ''
			})),
			...draftAdditions.map((a) => ({ ...a, mime: '' }))
		];
		return {
			finalFiles,
			counts: {
				inherited: inherited.length,
				replaced: replaced.length,
				removed: removed.length,
				added: draftAdditions.length
			},
			totalSize: finalFiles.reduce((s, f) => s + f.size, 0),
			manifest: manifestHash(finalFiles)
		};
	});

	const compareDiff = $derived(
		diff(
			revisions.find((r) => r.version === baseVersion) ?? null,
			revisions.find((r) => r.version === targetVersion) ?? revisions[revisions.length - 1]
		)
	);
	const compareSummary = $derived(diffSummary(compareDiff));
</script>

<div class="p-6 space-y-6">
	<!-- Disclaimer -->
	<div class="rounded border border-amber-300 bg-amber-50 px-4 py-2 text-amber-900 text-sm">
		<i class="fa-solid fa-flask mr-2"></i>
		UX prototype. Static fake data, no backend. The point is to feel out the
		<strong>history & diff</strong> interaction before committing to the data model refactor.
	</div>

	<!-- Admin / instance setting strip -->
	<div
		class="rounded border bg-slate-900 text-white px-4 py-3 text-sm flex items-center justify-between"
	>
		<div class="flex items-center gap-2">
			<i class="fa-solid fa-shield-halved text-amber-400"></i>
			<span class="text-xs uppercase tracking-wide text-slate-300">Instance setting</span>
			<span>Require review on new revisions</span>
		</div>
		<label class="inline-flex items-center gap-2 cursor-pointer">
			<span class="text-xs text-slate-300">
				{instanceRequiresReview ? 'Audit-strict' : 'Lightweight (default)'}
			</span>
			<input
				type="checkbox"
				bind:checked={instanceRequiresReview}
				class="w-10 h-5 appearance-none rounded-full bg-slate-600 checked:bg-blue-500
					relative cursor-pointer transition-colors
					before:content-[''] before:absolute before:top-0.5 before:left-0.5 before:w-4 before:h-4
					before:bg-white before:rounded-full before:transition-transform
					checked:before:translate-x-5"
			/>
		</label>
	</div>
	<div class="text-xs text-gray-600 -mt-4 px-1">
		Set once by the admin, applies to all evidences. <strong>Lightweight</strong>: every new
		revision is recorded as <em>approved</em> with the uploader as their own reviewer — no friction
		added to the simple "refresh once a year" case. <strong>Audit-strict</strong>: new revisions
		land as <em>in_review</em> and need explicit Approve / Reject. Toggle to see both demos below react.
	</div>

	<!-- ───── SIMPLE CASE DEMO ───── -->
	<section class="border rounded-lg p-4 bg-white space-y-3">
		<header class="flex items-center justify-between">
			<div>
				<div class="text-xs uppercase tracking-wide text-gray-500">
					Simple case — single-file evidence
				</div>
				<h2 class="font-semibold">Annual Privacy Policy</h2>
				<div class="mt-1 flex flex-wrap gap-2 text-xs">
					<span class="px-2 py-0.5 rounded bg-gray-100">
						<i class="fa-solid fa-user mr-1"></i>Dana Lopez
					</span>
					<span class="px-2 py-0.5 rounded bg-gray-100">
						<i class="fa-solid fa-calendar mr-1"></i>expires 2027-01-15
					</span>
					<span class="px-2 py-0.5 rounded bg-blue-50 text-blue-700">Policy</span>
				</div>
			</div>
			<div class="text-right text-sm">
				<div class="flex items-center gap-2 justify-end">
					<strong>v3</strong>
					<span
						class="text-xs px-2 py-0.5 rounded border inline-flex items-center gap-1 {instanceRequiresReview
							? statusStyle.in_review
							: statusStyle.approved}"
					>
						<i
							class="fa-solid {instanceRequiresReview ? statusIcon.in_review : statusIcon.approved}"
						></i>
						{instanceRequiresReview ? statusLabel.in_review : statusLabel.approved}
					</span>
				</div>
				<div class="text-xs text-gray-600">1 file · 0.4 MB</div>
			</div>
		</header>

		<div class="border rounded text-sm">
			<div class="px-3 py-2 flex items-center gap-2">
				<i class="fa-solid fa-file text-gray-400"></i>
				<span class="flex-1 truncate">privacy-policy-2026.pdf</span>
				<span class="text-xs text-gray-500 tabular-nums">412 KB</span>
				<span class="text-xs font-mono text-gray-400">8a3c…f201</span>
				<button class="text-gray-500 hover:text-blue-600" title="Download">
					<i class="fa-solid fa-download"></i>
				</button>
			</div>
		</div>

		<div class="flex items-center justify-between">
			<div class="text-xs text-gray-600 italic">
				1-file evidence: <strong>no inherit/replace dialog</strong>. Clicking
				<em>Upload new revision</em>
				opens the file picker directly. Same 2 clicks as today.
				{#if instanceRequiresReview}
					New revision will land as <em>in_review</em>.
				{:else}
					New revision auto-approves on upload.
				{/if}
			</div>
			<button class="px-3 py-1.5 rounded bg-blue-600 text-white text-sm">
				<i class="fa-solid fa-cloud-arrow-up mr-1"></i>Upload new revision
			</button>
		</div>
	</section>

	<!-- ───── BUNDLE CASE DEMO ───── -->
	<div class="text-xs uppercase tracking-wide text-gray-500 pt-2 border-t">
		Bundle case — multi-file evidence
	</div>

	<!-- Evidence header -->
	<header class="border rounded-lg p-4 bg-white">
		<div class="flex items-start justify-between gap-4">
			<div>
				<div class="text-xs uppercase tracking-wide text-gray-500">Evidence</div>
				<h1 class="text-xl font-semibold">{evidence.name}</h1>
				<div class="mt-2 flex flex-wrap gap-2 text-xs">
					<span class="px-2 py-0.5 rounded bg-gray-100">
						<i class="fa-solid fa-user mr-1"></i>{evidence.owner}
					</span>
					<span class="px-2 py-0.5 rounded bg-gray-100">
						<i class="fa-solid fa-calendar mr-1"></i>expires {evidence.expiry}
					</span>
					{#each evidence.labels as l}
						<span class="px-2 py-0.5 rounded bg-blue-50 text-blue-700">{l}</span>
					{/each}
				</div>
				<div class="mt-3 text-xs text-gray-500">
					Owner, expiry and labels are <strong>evidence-level</strong> (durable across revisions).
					Status, reviewer and approval timestamps are <strong>revision-level</strong>.
				</div>
			</div>
			<div class="text-right text-sm space-y-1">
				<div class="flex items-center justify-end gap-2">
					<span class="text-xs uppercase tracking-wide text-gray-500">Current</span>
					<strong class="text-base">v{current.version}</strong>
					<span
						class="px-2 py-0.5 rounded border text-xs inline-flex items-center gap-1 {statusStyle[
							displayCurrent.status
						]}"
					>
						<i class="fa-solid {statusIcon[displayCurrent.status]}"></i>
						{statusLabel[displayCurrent.status]}
					</span>
				</div>
				<div class="text-xs text-gray-600">
					{current.files.length} files · {fmtSize(totalSize(current.files))}
				</div>
				<div class="font-mono text-xs text-gray-500">
					manifest {manifestHash(current.files)}
				</div>
				{#if displayCurrent.status !== 'approved' && lastApproved}
					<div class="mt-2 text-xs text-gray-600 border-t pt-1">
						<i class="fa-solid fa-circle-check text-green-600 mr-1"></i>
						Last approved: <strong>v{lastApproved.version}</strong>
						by {lastApproved.reviewedBy} on {lastApproved.reviewedAt}
					</div>
				{/if}
			</div>
		</div>
	</header>

	<!-- Tabs -->
	<nav class="flex gap-1 border-b">
		{#each [{ id: 'current', label: 'Current revision', icon: 'fa-folder-open' }, { id: 'history', label: 'History', icon: 'fa-clock-rotate-left' }, { id: 'compare', label: 'Compare', icon: 'fa-code-compare' }, { id: 'new', label: 'New revision', icon: 'fa-plus' }] as t}
			<button
				class="px-3 py-2 text-sm border-b-2 -mb-px {tab === t.id
					? 'border-blue-600 text-blue-700 font-medium'
					: 'border-transparent text-gray-600 hover:text-gray-900'}"
				onclick={() => (tab = t.id as typeof tab)}
			>
				<i class="fa-solid {t.icon} mr-1"></i>{t.label}
			</button>
		{/each}
	</nav>

	<!-- CURRENT TAB -->
	{#if tab === 'current'}
		<section class="space-y-3">
			<div class="flex items-center justify-between">
				<div>
					<h2 class="text-lg font-semibold flex items-center gap-2">
						v{current.version}
						<span class="text-xs px-2 py-0.5 rounded bg-blue-100 text-blue-800"> current </span>
						<span
							class="text-xs px-2 py-0.5 rounded border inline-flex items-center gap-1 {statusStyle[
								displayCurrent.status
							]}"
						>
							<i class="fa-solid {statusIcon[displayCurrent.status]}"></i>
							{statusLabel[displayCurrent.status]}
						</span>
					</h2>
					<div class="text-sm text-gray-600">
						Uploaded {current.uploadedAt} by {current.uploadedBy}
					</div>
				</div>
				<div class="flex gap-2">
					<button class="px-3 py-1.5 rounded bg-blue-600 text-white text-sm">
						<i class="fa-solid fa-download mr-1"></i>Download all (zip)
					</button>
					<button class="px-3 py-1.5 rounded border text-sm">
						<i class="fa-solid fa-plus mr-1"></i>Upload new revision
					</button>
					{#if displayCurrent.status === 'in_review'}
						<button
							class="px-3 py-1.5 rounded border text-sm bg-green-50 text-green-800 border-green-300"
						>
							<i class="fa-solid fa-circle-check mr-1"></i>Approve…
						</button>
						<button
							class="px-3 py-1.5 rounded border text-sm bg-red-50 text-red-800 border-red-300"
						>
							<i class="fa-solid fa-circle-xmark mr-1"></i>Reject…
						</button>
					{/if}
				</div>
			</div>

			{#if current.observation}
				<div class="text-sm bg-gray-50 border-l-4 border-gray-300 px-3 py-2 italic">
					{current.observation}
				</div>
			{/if}

			{#if displayCurrent.reviewedAt}
				<div
					class="text-sm border-l-4 px-3 py-2 {displayCurrent.status === 'approved'
						? 'bg-green-50 border-green-400'
						: displayCurrent.status === 'rejected'
							? 'bg-red-50 border-red-400'
							: 'bg-gray-50 border-gray-300'}"
				>
					<i class="fa-solid {statusIcon[displayCurrent.status]} mr-1"></i>
					<strong>{statusLabel[displayCurrent.status]}</strong> by {displayCurrent.reviewedBy} on
					{displayCurrent.reviewedAt}
					{#if displayCurrent.reviewComment}
						<div class="mt-1 italic">"{displayCurrent.reviewComment}"</div>
					{/if}
				</div>
			{/if}

			<div class="border rounded">
				<table class="w-full text-sm">
					<thead class="bg-gray-50 text-xs uppercase text-gray-600">
						<tr>
							<th class="text-left px-3 py-2">File</th>
							<th class="text-right px-3 py-2">Size</th>
							<th class="text-left px-3 py-2">SHA-256</th>
							<th class="px-3 py-2"></th>
						</tr>
					</thead>
					<tbody>
						{#each current.files as f}
							<tr class="border-t">
								<td class="px-3 py-2">
									<i class="fa-solid fa-file mr-2 text-gray-400"></i>{f.name}
								</td>
								<td class="px-3 py-2 text-right tabular-nums">{fmtSize(f.size)}</td>
								<td class="px-3 py-2 font-mono text-xs text-gray-600">{short(f.hash)}</td>
								<td class="px-3 py-2 text-right">
									<button class="text-gray-500 hover:text-blue-600 mx-1" title="Preview">
										<i class="fa-solid fa-eye"></i>
									</button>
									<button class="text-gray-500 hover:text-blue-600 mx-1" title="Download">
										<i class="fa-solid fa-download"></i>
									</button>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>

			{#if current.link}
				<div class="text-sm">
					<i class="fa-solid fa-link mr-1 text-gray-500"></i>
					<a href={current.link} class="text-blue-600 hover:underline">{current.link}</a>
				</div>
			{/if}
		</section>
	{/if}

	<!-- HISTORY TAB -->
	{#if tab === 'history'}
		<section>
			<div class="flex items-center justify-between mb-4">
				<p class="text-sm text-gray-600">
					Each revision is an immutable snapshot. File identity is by name — same name with a new
					hash is a <em>replacement</em>, not a separate file.
				</p>
				<label class="text-xs flex items-center gap-1">
					<input type="checkbox" bind:checked={showUnchanged} />
					Show unchanged files
				</label>
			</div>

			<ol class="relative border-l-2 border-gray-200 ml-3 space-y-6">
				{#each [...revisions].reverse() as rawRev, idx}
					{@const rev = displayRev(rawRev)}
					{@const prev = revisions.find((r) => r.version === rev.version - 1) ?? null}
					{@const rows = diff(prev, rev)}
					{@const summary = diffSummary(rows)}
					{@const isCurrent = rev.version === current.version}
					<li class="ml-6 relative">
						<span
							class="absolute -left-[34px] top-3 w-4 h-4 rounded-full border-2 {isCurrent
								? 'bg-blue-600 border-blue-600'
								: rev.status === 'approved'
									? 'bg-green-500 border-green-500'
									: rev.status === 'rejected'
										? 'bg-red-500 border-red-500'
										: 'bg-white border-gray-400'}"
						></span>

						<article class="border rounded-lg bg-white">
							<header class="flex items-center justify-between px-4 py-2 border-b bg-gray-50">
								<div class="flex items-center gap-3 flex-wrap">
									<h3 class="font-semibold">
										v{rev.version}
									</h3>
									<span
										class="text-xs px-2 py-0.5 rounded border inline-flex items-center gap-1 {statusStyle[
											rev.status
										]}"
									>
										<i class="fa-solid {statusIcon[rev.status]}"></i>
										{statusLabel[rev.status]}
									</span>
									{#if isCurrent}
										<span class="text-xs px-2 py-0.5 rounded bg-blue-100 text-blue-800">
											current
										</span>
									{/if}
									{#if rev.version === 1}
										<span class="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-700">
											initial
										</span>
									{/if}
									<span class="text-sm text-gray-500">
										uploaded {rev.uploadedAt} by {rev.uploadedBy}
									</span>
								</div>
								<div class="flex gap-3 text-xs tabular-nums">
									{#if summary.added > 0}
										<span class="text-green-700">+{summary.added}</span>
									{/if}
									{#if summary.replaced > 0}
										<span class="text-amber-700">~{summary.replaced}</span>
									{/if}
									{#if summary.removed > 0}
										<span class="text-red-700">−{summary.removed}</span>
									{/if}
									<span class="text-gray-400">·</span>
									<span class="text-gray-500">
										{rev.files.length} files · {fmtSize(totalSize(rev.files))}
									</span>
								</div>
							</header>

							{#if rev.observation}
								<div class="px-4 py-2 text-sm italic text-gray-700 border-b">
									<i class="fa-solid fa-quote-left text-gray-300 mr-1"></i>
									{rev.observation}
								</div>
							{/if}

							{#if rev.reviewedAt}
								<div
									class="px-4 py-2 text-sm border-b {rev.status === 'approved'
										? 'bg-green-50 text-green-900'
										: rev.status === 'rejected'
											? 'bg-red-50 text-red-900'
											: 'bg-gray-50 text-gray-700'}"
								>
									<i class="fa-solid {statusIcon[rev.status]} mr-1"></i>
									<strong>{statusLabel[rev.status]}</strong> by
									{rev.reviewedBy} on {rev.reviewedAt}
									{#if rev.reviewComment}
										<span class="italic"> — "{rev.reviewComment}"</span>
									{/if}
								</div>
							{/if}

							<ul class="divide-y text-sm">
								{#each rows as r}
									{#if showUnchanged || r.state !== 'unchanged'}
										<li class="px-4 py-1.5 flex items-center gap-3">
											<span
												class="font-mono text-xs px-1.5 py-0.5 rounded border w-20 inline-flex items-center gap-1 {stateColor[
													r.state
												]}"
											>
												<span class="font-bold">{stateGlyph[r.state]}</span>
												{stateLabel[r.state]}
											</span>
											<span class="flex-1 truncate">
												<i class="fa-solid fa-file mr-1 text-gray-400"></i>{r.name}
											</span>
											<span class="text-xs text-gray-500 tabular-nums w-32 text-right">
												{#if r.state === 'replaced'}
													{fmtSize(r.from!.size)} → {fmtSize(r.to!.size)}
												{:else if r.state === 'removed'}
													{fmtSize(r.from!.size)}
												{:else}
													{fmtSize(r.to!.size)}
												{/if}
											</span>
											<span class="text-xs font-mono text-gray-400 w-28 text-right">
												{#if r.state === 'replaced'}
													{short(r.from!.hash)}→{short(r.to!.hash).slice(-4)}
												{:else if r.state === 'removed'}
													{short(r.from!.hash)}
												{:else}
													{short(r.to!.hash)}
												{/if}
											</span>
										</li>
									{/if}
								{/each}
							</ul>

							<footer
								class="px-4 py-2 border-t bg-gray-50 flex items-center justify-between text-xs"
							>
								<span class="font-mono text-gray-500">
									manifest {manifestHash(rev.files)}
								</span>
								<div class="flex gap-2">
									<button
										class="px-2 py-1 rounded border bg-white hover:bg-gray-100"
										onclick={() => {
											tab = 'compare';
											baseVersion = prev ? prev.version : rev.version;
											targetVersion = rev.version;
										}}
									>
										<i class="fa-solid fa-code-compare mr-1"></i>Compare to…
									</button>
									<button class="px-2 py-1 rounded border bg-white hover:bg-gray-100">
										<i class="fa-solid fa-download mr-1"></i>Download zip
									</button>
									{#if !isCurrent}
										<button
											class="px-2 py-1 rounded border bg-white hover:bg-gray-100"
											title="Re-publish this revision's files as a new revision (history is preserved)"
										>
											<i class="fa-solid fa-rotate-left mr-1"></i>Restore as new revision
										</button>
									{/if}
								</div>
							</footer>
						</article>
					</li>
				{/each}
			</ol>
		</section>
	{/if}

	<!-- COMPARE TAB -->
	{#if tab === 'compare'}
		<section class="space-y-4">
			<div class="flex items-end gap-3">
				<label class="text-sm">
					<span class="block text-xs text-gray-500 mb-1">Base</span>
					<select bind:value={baseVersion} class="border rounded px-2 py-1.5 text-sm bg-white">
						{#each revisions as r}
							<option value={r.version}
								>v{r.version} — {r.uploadedAt} ({statusLabel[r.status]})</option
							>
						{/each}
					</select>
				</label>
				<i class="fa-solid fa-arrow-right text-gray-400 mb-2"></i>
				<label class="text-sm">
					<span class="block text-xs text-gray-500 mb-1">Target</span>
					<select bind:value={targetVersion} class="border rounded px-2 py-1.5 text-sm bg-white">
						{#each revisions as r}
							<option value={r.version}
								>v{r.version} — {r.uploadedAt} ({statusLabel[r.status]})</option
							>
						{/each}
					</select>
				</label>
				<div class="ml-auto text-sm text-gray-600 flex gap-4">
					<span class="text-green-700">+{compareSummary.added} added</span>
					<span class="text-amber-700">~{compareSummary.replaced} replaced</span>
					<span class="text-red-700">−{compareSummary.removed} removed</span>
					<span class="text-gray-500">={compareSummary.unchanged} unchanged</span>
				</div>
			</div>

			<div class="border rounded">
				<table class="w-full text-sm">
					<thead class="bg-gray-50 text-xs uppercase text-gray-600">
						<tr>
							<th class="text-left px-3 py-2 w-28">State</th>
							<th class="text-left px-3 py-2">File</th>
							<th class="text-right px-3 py-2">Size (base → target)</th>
							<th class="text-right px-3 py-2">SHA-256 (base → target)</th>
						</tr>
					</thead>
					<tbody>
						{#each compareDiff as r}
							<tr class="border-t">
								<td class="px-3 py-2">
									<span
										class="font-mono text-xs px-1.5 py-0.5 rounded border inline-flex items-center gap-1 {stateColor[
											r.state
										]}"
									>
										<span class="font-bold">{stateGlyph[r.state]}</span>
										{stateLabel[r.state]}
									</span>
								</td>
								<td class="px-3 py-2">
									<i class="fa-solid fa-file mr-2 text-gray-400"></i>{r.name}
								</td>
								<td class="px-3 py-2 text-right tabular-nums text-gray-600">
									{r.from ? fmtSize(r.from.size) : '—'} → {r.to ? fmtSize(r.to.size) : '—'}
								</td>
								<td class="px-3 py-2 text-right font-mono text-xs text-gray-500">
									{r.from ? short(r.from.hash) : '—'} → {r.to ? short(r.to.hash) : '—'}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>

			<div class="text-xs text-gray-500">
				File identity is matched by <strong>name</strong>. A same-name file with a different hash is
				shown as <em>replaced</em>; a hash-identical match is <em>unchanged</em>. Renames are not
				detected (would need a heuristic — out of scope here).
			</div>
		</section>
	{/if}

	<!-- NEW REVISION TAB -->
	{#if tab === 'new'}
		<section class="space-y-4">
			<div class="text-sm text-gray-700">
				This will become <strong>v{current.version + 1}</strong>. By default, all files from v{current.version}
				are inherited. Untick to remove, click <em>Replace</em> to upload a new version of an
				existing file (filename is preserved → it shows as <em>replaced</em> in history), or drop new
				files at the bottom.
			</div>

			<!-- Inherit / replace / remove list -->
			<div class="border rounded">
				<div class="px-3 py-2 bg-gray-50 border-b text-xs uppercase tracking-wide text-gray-600">
					Files in v{current.version} — choose what carries over
				</div>
				<ul class="divide-y text-sm">
					{#each draftEntries as e, idx}
						<li class="px-3 py-2 flex items-center gap-3">
							<span
								class="font-mono text-xs px-1.5 py-0.5 rounded border w-24 inline-flex items-center justify-center gap-1 {e.action ===
								'keep'
									? 'text-gray-600 bg-gray-50 border-gray-200'
									: e.action === 'replace'
										? 'text-amber-700 bg-amber-50 border-amber-200'
										: 'text-red-700 bg-red-50 border-red-200'}"
							>
								{e.action === 'keep' ? 'inherit' : e.action === 'replace' ? 'replace' : 'remove'}
							</span>

							<span class="flex-1 truncate">
								<i class="fa-solid fa-file mr-1 text-gray-400"></i>{e.name}
							</span>

							<span class="text-xs text-gray-500 tabular-nums w-32 text-right">
								{#if e.action === 'replace'}
									{fmtSize(e.baseSize)} → {fmtSize(e.newSize!)}
								{:else}
									{fmtSize(e.baseSize)}
								{/if}
							</span>

							<span class="text-xs font-mono text-gray-400 w-28 text-right">
								{#if e.action === 'replace'}
									{short(e.baseHash)}→{short(e.newHash!).slice(-4)}
								{:else}
									{short(e.baseHash)}
								{/if}
							</span>

							<div class="flex gap-1">
								<button
									class="px-2 py-0.5 text-xs rounded border {e.action === 'keep'
										? 'bg-gray-100 border-gray-400'
										: 'bg-white hover:bg-gray-50'}"
									onclick={() => setAction(idx, 'keep')}
									title="Carry this file over unchanged"
								>
									Keep
								</button>
								<button
									class="px-2 py-0.5 text-xs rounded border {e.action === 'replace'
										? 'bg-amber-100 border-amber-400'
										: 'bg-white hover:bg-gray-50'}"
									onclick={() => setAction(idx, 'replace')}
									title="Upload a new file with the same name"
								>
									Replace…
								</button>
								<button
									class="px-2 py-0.5 text-xs rounded border {e.action === 'remove'
										? 'bg-red-100 border-red-400'
										: 'bg-white hover:bg-gray-50'}"
									onclick={() => setAction(idx, 'remove')}
									title="Drop this file from the new revision"
								>
									Remove
								</button>
							</div>
						</li>
					{/each}
				</ul>
			</div>

			<!-- Drop zone for genuinely new files -->
			<div
				class="border-2 border-dashed rounded p-4 bg-gray-50"
				ondragover={(e) => e.preventDefault()}
				ondrop={onDrop}
				role="button"
				tabindex="0"
			>
				<div
					class="text-xs uppercase tracking-wide text-gray-600 mb-2 flex items-center justify-between"
				>
					<span>Add files</span>
					<span class="text-gray-400 normal-case">
						SHA-256 is computed in your browser — no upload yet.
					</span>
				</div>
				{#if draftAdditions.length > 0}
					<ul class="text-sm divide-y mb-2">
						{#each draftAdditions as a, idx}
							<li class="py-1 flex items-center gap-2">
								<span
									class="font-mono text-xs px-1.5 py-0.5 rounded border text-green-700 bg-green-50 border-green-200"
								>
									new
								</span>
								<i class="fa-solid fa-file text-gray-400"></i>
								<span class="flex-1 truncate">{a.name}</span>
								<span class="text-xs text-gray-500 tabular-nums">{fmtSize(a.size)}</span>
								<span class="text-xs font-mono text-gray-400">{short(a.hash)}</span>
								<button
									class="text-gray-400 hover:text-red-600"
									onclick={() => (draftAdditions = draftAdditions.filter((_, i) => i !== idx))}
									title="Remove from the new revision"
								>
									<i class="fa-solid fa-xmark"></i>
								</button>
							</li>
						{/each}
					</ul>
				{/if}

				{#if hashing.length > 0}
					<ul class="text-xs space-y-0.5 mb-2 border-t pt-2">
						{#each hashing as h}
							<li class="flex items-center gap-2 text-gray-600">
								{#if h.progress === 'hashing'}
									<i class="fa-solid fa-spinner fa-spin text-blue-500"></i>
									<span>{h.name}</span>
									<span class="text-gray-400">hashing…</span>
								{:else if h.progress === 'duplicate'}
									<i class="fa-solid fa-equals text-gray-500"></i>
									<span>{h.name}</span>
									<span class="text-gray-500 italic">
										identical to inherited file → nothing to upload
									</span>
								{:else if h.progress === 'replaced'}
									<i class="fa-solid fa-arrows-rotate text-amber-600"></i>
									<span>{h.name}</span>
									<span class="text-amber-700 italic">
										auto-promoted to Replace (same name, new content)
									</span>
								{:else}
									<i class="fa-solid fa-check text-green-600"></i>
									<span>{h.name}</span>
									<span class="text-green-700 italic">hashed → queued for upload</span>
								{/if}
							</li>
						{/each}
					</ul>
				{/if}

				<button
					type="button"
					class="w-full text-center text-sm text-gray-500 py-3 hover:bg-gray-100 rounded"
					onclick={() => fileInput?.click()}
				>
					<i class="fa-solid fa-cloud-arrow-up text-2xl mb-1 block"></i>
					Drag files here or click to browse
					<div class="text-xs mt-1 text-gray-400">
						Same-name as an inherited file? Auto-promoted to Replace. Bit-identical content?
						Detected and skipped.
					</div>
				</button>
				<input
					bind:this={fileInput}
					type="file"
					multiple
					class="hidden"
					onchange={(e) => {
						const f = (e.currentTarget as HTMLInputElement).files;
						if (f) handleFiles(f);
					}}
				/>
			</div>

			<!-- Observation -->
			<label class="block text-sm">
				<span class="text-xs uppercase tracking-wide text-gray-600">Observation</span>
				<textarea
					bind:value={draftObservation}
					rows="2"
					class="mt-1 w-full border rounded px-2 py-1.5 text-sm"
				></textarea>
			</label>

			<!-- Preview -->
			<div class="border rounded-lg bg-blue-50 border-blue-200 p-4 space-y-2">
				<div class="text-sm font-semibold text-blue-900">
					<i class="fa-solid fa-eye mr-1"></i>Preview of v{current.version + 1}
				</div>
				<div class="flex gap-4 text-xs">
					<span class="text-gray-700">
						<strong>{draftPreview.finalFiles.length}</strong> files,
						<strong>{fmtSize(draftPreview.totalSize)}</strong>
					</span>
					<span class="text-gray-500 font-mono">manifest {draftPreview.manifest}</span>
				</div>
				<div class="flex gap-3 text-xs">
					<span class="text-gray-600">
						= {draftPreview.counts.inherited} inherited
					</span>
					{#if draftPreview.counts.replaced > 0}
						<span class="text-amber-700">
							~ {draftPreview.counts.replaced} replaced
						</span>
					{/if}
					{#if draftPreview.counts.removed > 0}
						<span class="text-red-700">
							− {draftPreview.counts.removed} removed
						</span>
					{/if}
					{#if draftPreview.counts.added > 0}
						<span class="text-green-700">
							+ {draftPreview.counts.added} new
						</span>
					{/if}
				</div>
				<ul class="text-xs space-y-0.5 mt-2">
					{#each draftPreview.finalFiles as f}
						<li class="flex items-center gap-2">
							<i class="fa-solid fa-file text-gray-400"></i>
							<span class="flex-1 truncate">{f.name}</span>
							<span class="text-gray-500 tabular-nums">{fmtSize(f.size)}</span>
							<span class="font-mono text-gray-400">{short(f.hash)}</span>
						</li>
					{/each}
				</ul>
				<div class="text-xs text-gray-500 italic mt-2 space-y-1">
					<div>
						<strong>How dedup works</strong> — two stages, no trust:
					</div>
					<ol class="list-decimal ml-5">
						<li>
							<strong>Client side</strong> (browser): each file is SHA-256 hashed via Web Crypto before
							any upload. The browser then asks the server "do you already have these hashes?" — only
							files marked unknown are uploaded.
						</li>
						<li>
							<strong>Server side</strong>: every uploaded file is re-hashed on receipt and compared
							to the claimed hash. Lookup is scoped to the user's reachable evidence (same
							evidence's prior revisions by default; cross-evidence dedup is a separate policy
							decision with RBAC implications).
						</li>
					</ol>
					<div>
						Result for this revision: <strong
							>only the new + replaced bytes are sent over the wire</strong
						>. Inherited files are link-only.
					</div>
				</div>
			</div>

			<div class="flex justify-end gap-2">
				<button class="px-3 py-1.5 rounded border text-sm">Cancel</button>
				<button class="px-3 py-1.5 rounded bg-blue-600 text-white text-sm">
					<i class="fa-solid fa-check mr-1"></i>
					Create v{current.version + 1}
					{instanceRequiresReview ? '(in_review)' : '(auto-approved)'}
				</button>
			</div>

			<div class="text-xs text-gray-500 italic">
				{#if instanceRequiresReview}
					Instance setting <strong>requires review</strong> — the new revision lands as
					<em>in_review</em> and needs explicit Approve / Reject. The previous revision keeps its status;
					history is never rewritten.
				{:else}
					Instance setting allows <strong>auto-approve</strong> — the new revision is recorded as
					<em>approved</em> with you (the uploader) as its own reviewer. No review cycle is imposed; the
					audit trail still shows who uploaded what, when.
				{/if}
			</div>
		</section>
	{/if}

	<!-- Open UX questions -->
	<aside class="border rounded-lg bg-blue-50 border-blue-200 p-4 text-sm space-y-2">
		<div class="font-semibold text-blue-900">
			<i class="fa-solid fa-circle-question mr-1"></i>Open UX questions to validate
		</div>
		<div class="text-xs font-semibold text-blue-900 mt-3 mb-1">Decided</div>
		<ul class="list-disc ml-5 space-y-1 text-blue-900 text-xs opacity-80">
			<li>
				<strong>Lifecycle split</strong>: owner / expiry / labels are evidence-level; status /
				reviewer / approval timestamps are revision-level.
			</li>
			<li>
				<strong>Upload model</strong>: inherit-by-default with explicit Keep / Replace / Remove + a
				drop zone for genuinely new files. Same-name file → auto-promote to Replace.
			</li>
			<li>
				<strong>Client-side dedup</strong>: SHA-256 in the browser via Web Crypto, server
				re-verifies on receipt. Scope = same evidence's prior revisions.
			</li>
			<li>
				<strong>Approval workflow as instance setting</strong> (above). Lightweight by default so the
				simple "refresh once a year" case has zero added friction.
			</li>
			<li>
				<strong>Simple case stays simple</strong>: 1-file evidence skips the inherit dialog and goes
				straight to the file picker (see top demo).
			</li>
		</ul>

		<div class="text-sm font-semibold text-blue-900 mt-3 mb-1">Still open</div>
		<ul class="list-disc ml-5 space-y-1 text-blue-900">
			<li>
				History as a <strong>vertical timeline</strong> vs a flat sortable table — timeline wins for ≤20
				revisions; should we offer a table fallback for very long histories?
			</li>
			<li>
				File identity = filename. Drop a renamed-file detector entirely, or add a "rename" badge
				later via name+hash heuristic?
			</li>
			<li>"Restore as new revision" replaces "rollback" — explicit, no history lost. OK?</li>
			<li>
				Manifest hash visibility: footer-only as here, or surfaced more prominently for audit-trail
				reassurance?
			</li>
			<li>
				Approver as Actor reference (per revision) so "things I approved" becomes a filterable query
				— worth the extra FK or overkill?
			</li>
		</ul>
	</aside>
</div>
