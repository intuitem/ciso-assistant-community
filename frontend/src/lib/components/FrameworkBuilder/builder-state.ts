import { getContext, setContext } from 'svelte';
import { writable, type Writable } from 'svelte/store';
import {
	apiSaveDraft,
	apiPublishDraft,
	apiDiscardDraft,
	apiStartEditing,
	type DraftJSON
} from './builder-api';

// --- Types ---

export type Translations = Record<string, Record<string, string>>;

export interface QuestionChoice {
	id: string;
	urn: string | null;
	ref_id: string | null;
	value: string | null;
	annotation: string | null;
	add_score: number | null;
	compute_result: string | null;
	order: number;
	description: string | null;
	color: string | null;
	select_implementation_groups: string[] | null;
	translations?: Translations | null;
	folder: { id: string; str: string } | string;
	question: string;
}

export interface Question {
	id: string;
	urn: string;
	ref_id: string | null;
	text: string | null;
	annotation: string | null;
	type: 'text' | 'number' | 'boolean' | 'unique_choice' | 'multiple_choice' | 'date';
	config: Record<string, unknown> | null;
	depends_on: Record<string, unknown> | null;
	order: number;
	weight: number;
	translations?: Translations | null;
	folder: { id: string; str: string } | string;
	requirement_node: string;
	choices: QuestionChoice[];
}

export interface RequirementNode {
	id: string;
	urn: string | null;
	ref_id: string | null;
	name: string | null;
	description: string | null;
	annotation: string | null;
	parent_urn: string | null;
	order_id: number | null;
	assessable: boolean;
	implementation_groups: string[] | null;
	typical_evidence: string | null;
	weight: number;
	importance: string;
	display_mode: 'default' | 'splash';
	translations?: Translations | null;
	framework: string | { id: string };
	folder: { id: string; str: string } | string;
}

export interface OutcomeRule {
	ref_id: string;
	annotation: string;
	color: string | null;
	expression: string;
	translations?: Translations | null;
}

export interface ImplementationGroup {
	ref_id: string;
	name: string;
	description: string;
	default_selected?: boolean;
	translations?: Translations | null;
}

export interface Framework {
	id: string;
	name: string;
	description: string | null;
	annotation: string | null;
	folder: { id: string; str: string };
	library: { id: string; str: string } | null;
	min_score: number;
	max_score: number;
	scores_definition: Record<string, unknown> | null;
	implementation_groups_definition: Record<string, unknown>[] | null;
	outcomes_definition: OutcomeRule[] | null;
	field_visibility: Record<string, string>;
	locale?: string;
	translations?: Translations | null;
	available_languages?: string[];
	urn: string | null;
}

export interface BuilderRequirement {
	node: RequirementNode;
	questions: BuilderQuestion[];
	children: BuilderRequirement[];
	depth: number;
}

export interface BuilderQuestion {
	question: Question;
}

export interface BuilderSection {
	node: RequirementNode;
	requirements: BuilderRequirement[];
	collapsed: boolean;
}

// --- Recursive helpers ---

/** Recursively map over a requirement tree, applying fn to each requirement */
function mapRequirements(
	reqs: BuilderRequirement[],
	fn: (req: BuilderRequirement) => BuilderRequirement
): BuilderRequirement[] {
	return reqs.map((req) => {
		const updated = fn(req);
		return { ...updated, children: mapRequirements(updated.children, fn) };
	});
}

/** Find a requirement by node ID in a recursive tree */
function findRequirement(reqs: BuilderRequirement[], nodeId: string): BuilderRequirement | null {
	for (const req of reqs) {
		if (req.node.id === nodeId) return req;
		const found = findRequirement(req.children, nodeId);
		if (found) return found;
	}
	return null;
}

/** Remove a requirement by node ID from a recursive tree */
function removeRequirement(reqs: BuilderRequirement[], nodeId: string): BuilderRequirement[] {
	return reqs
		.filter((req) => req.node.id !== nodeId)
		.map((req) => ({ ...req, children: removeRequirement(req.children, nodeId) }));
}

/** Add a child requirement under a parent node ID */
function addChildToRequirement(
	reqs: BuilderRequirement[],
	parentNodeId: string,
	child: BuilderRequirement
): BuilderRequirement[] {
	return reqs.map((req) => {
		if (req.node.id === parentNodeId) {
			return { ...req, children: [...req.children, child] };
		}
		return { ...req, children: addChildToRequirement(req.children, parentNodeId, child) };
	});
}

/** Apply a function to a specific requirement found by node ID */
function updateRequirementById(
	reqs: BuilderRequirement[],
	nodeId: string,
	fn: (req: BuilderRequirement) => BuilderRequirement
): BuilderRequirement[] {
	return reqs.map((req) => {
		if (req.node.id === nodeId) return fn(req);
		return { ...req, children: updateRequirementById(req.children, nodeId, fn) };
	});
}

// --- Serialization / Hydration helpers ---

/** Extract a plain folder_id string from a folder that may be an object or string */
function extractFolderId(folder: { id: string; str: string } | string): string {
	return typeof folder === 'string' ? folder : folder.id;
}

/** Extract a plain requirement_node ID string */
function extractRequirementNodeId(rn: string | { id: string }): string {
	return typeof rn === 'string' ? rn : rn.id;
}

/** Get a translated field value */
export function getTranslation(
	translations: Translations | null | undefined,
	lang: string,
	field: string
): string {
	return translations?.[lang]?.[field] ?? '';
}

/** Return a new translations dict with one field updated */
export function withTranslation(
	translations: Translations | null | undefined,
	lang: string,
	field: string,
	value: string
): Translations {
	const current = translations ?? {};
	const langDict = { ...(current[lang] ?? {}), [field]: value };
	if (!value) delete langDict[field];
	return { ...current, [lang]: langDict };
}

/**
 * Serialize the current builder state into a flat DraftJSON for persistence.
 */
function serializeDraft(fw: Framework, sections: BuilderSection[]): DraftJSON {
	const nodes: Record<string, unknown>[] = [];
	const questions: Record<string, unknown>[] = [];
	const choices: Record<string, unknown>[] = [];

	function collectFromRequirements(reqs: BuilderRequirement[]) {
		for (const req of reqs) {
			const n = req.node;
			nodes.push({
				id: n.id,
				urn: n.urn,
				ref_id: n.ref_id,
				name: n.name,
				description: n.description,
				annotation: n.annotation,
				parent_urn: n.parent_urn,
				order_id: n.order_id,
				assessable: n.assessable,
				implementation_groups: n.implementation_groups,
				typical_evidence: n.typical_evidence,
				weight: n.weight,
				importance: n.importance,
				display_mode: n.display_mode,
				folder_id: extractFolderId(n.folder),
				translations: n.translations ?? null
			});
			for (const bq of req.questions) {
				const q = bq.question;
				questions.push({
					id: q.id,
					urn: q.urn,
					ref_id: q.ref_id,
					text: q.text,
					annotation: q.annotation,
					type: q.type,
					config: q.config,
					depends_on: q.depends_on,
					order: q.order,
					weight: q.weight,
					requirement_node_id: extractRequirementNodeId(q.requirement_node),
					folder_id: extractFolderId(q.folder),
					translations: q.translations ?? null
				});
				for (const c of q.choices) {
					choices.push({
						id: c.id,
						urn: c.urn,
						ref_id: c.ref_id,
						value: c.value,
						annotation: c.annotation,
						add_score: c.add_score,
						compute_result: c.compute_result,
						order: c.order,
						description: c.description,
						color: c.color,
						select_implementation_groups: c.select_implementation_groups,
						question_id: typeof c.question === 'string' ? c.question : c.question,
						folder_id: extractFolderId(c.folder),
						translations: c.translations ?? null
					});
				}
			}
			collectFromRequirements(req.children);
		}
	}

	for (const sec of sections) {
		const n = sec.node;
		nodes.push({
			id: n.id,
			urn: n.urn,
			ref_id: n.ref_id,
			name: n.name,
			description: n.description,
			annotation: n.annotation,
			parent_urn: n.parent_urn,
			order_id: n.order_id,
			assessable: n.assessable,
			implementation_groups: n.implementation_groups,
			typical_evidence: n.typical_evidence,
			weight: n.weight,
			importance: n.importance,
			display_mode: n.display_mode,
			folder_id: extractFolderId(n.folder),
			translations: n.translations ?? null
		});
		collectFromRequirements(sec.requirements);
	}

	return {
		framework_meta: {
			name: fw.name,
			description: fw.description,
			annotation: fw.annotation,
			locale: fw.locale,
			translations: fw.translations ?? {},
			available_languages: fw.available_languages ?? [],
			min_score: fw.min_score,
			max_score: fw.max_score,
			scores_definition: fw.scores_definition,
			implementation_groups_definition: fw.implementation_groups_definition,
			outcomes_definition: fw.outcomes_definition as Record<string, unknown>[] | null,
			field_visibility: fw.field_visibility
		},
		nodes,
		questions,
		choices
	};
}

/**
 * Hydrate draft JSON (flat arrays with _id suffixed FK fields) into
 * the RequirementNode[] and Question[] format expected by buildTree.
 */
export function hydrateDraft(
	draft: DraftJSON,
	frameworkId: string
): {
	frameworkPatch: Partial<Framework>;
	nodes: RequirementNode[];
	questions: Question[];
} {
	const meta = draft.framework_meta;
	const frameworkPatch: Partial<Framework> = {
		name: meta.name,
		description: meta.description,
		annotation: meta.annotation ?? null,
		locale: meta.locale ?? 'en',
		translations: meta.translations ?? {},
		available_languages: meta.available_languages ?? [],
		min_score: meta.min_score,
		max_score: meta.max_score,
		scores_definition: meta.scores_definition,
		implementation_groups_definition: meta.implementation_groups_definition,
		outcomes_definition: meta.outcomes_definition as OutcomeRule[] | null,
		field_visibility: meta.field_visibility ?? {}
	};

	// Build a lookup from question_id to choices
	const choicesByQuestion = new Map<string, QuestionChoice[]>();
	for (const c of draft.choices) {
		const qId = (c.question_id ?? c.question) as string;
		if (!choicesByQuestion.has(qId)) choicesByQuestion.set(qId, []);
		choicesByQuestion.get(qId)!.push({
			id: c.id as string,
			urn: (c.urn ?? null) as string | null,
			ref_id: (c.ref_id ?? null) as string | null,
			value: (c.value ?? null) as string | null,
			annotation: (c.annotation ?? null) as string | null,
			add_score: (c.add_score ?? null) as number | null,
			compute_result: (c.compute_result ?? null) as string | null,
			order: (c.order ?? 0) as number,
			description: (c.description ?? null) as string | null,
			color: (c.color ?? null) as string | null,
			select_implementation_groups: (c.select_implementation_groups ?? null) as string[] | null,
			translations: (c.translations ?? null) as Translations | null,
			folder: (c.folder_id ?? c.folder ?? '') as string,
			question: qId
		});
	}

	const questions: Question[] = draft.questions.map((q) => {
		const nodeId = (q.requirement_node_id ?? q.requirement_node) as string;
		const qId = q.id as string;
		return {
			id: qId,
			urn: (q.urn ?? '') as string,
			ref_id: (q.ref_id ?? null) as string | null,
			text: (q.text ?? null) as string | null,
			annotation: (q.annotation ?? null) as string | null,
			type: (q.type ?? 'text') as Question['type'],
			config: (q.config ?? null) as Record<string, unknown> | null,
			depends_on: (q.depends_on ?? null) as Record<string, unknown> | null,
			order: (q.order ?? 0) as number,
			weight: (q.weight ?? 1) as number,
			translations: (q.translations ?? null) as Translations | null,
			folder: (q.folder_id ?? q.folder ?? '') as string,
			requirement_node: nodeId,
			choices: (choicesByQuestion.get(qId) ?? []).sort((a, b) => a.order - b.order)
		};
	});

	const nodes: RequirementNode[] = draft.nodes.map((n) => ({
		id: n.id as string,
		urn: (n.urn ?? null) as string | null,
		ref_id: (n.ref_id ?? null) as string | null,
		name: (n.name ?? null) as string | null,
		description: (n.description ?? null) as string | null,
		annotation: (n.annotation ?? null) as string | null,
		parent_urn: (n.parent_urn ?? null) as string | null,
		order_id: (n.order_id ?? null) as number | null,
		assessable: (n.assessable ?? false) as boolean,
		implementation_groups: (n.implementation_groups ?? null) as string[] | null,
		typical_evidence: (n.typical_evidence ?? null) as string | null,
		weight: (n.weight ?? 1) as number,
		importance: (n.importance ?? '') as string,
		display_mode: (n.display_mode ?? 'default') as 'default' | 'splash',
		translations: (n.translations ?? null) as Translations | null,
		framework: (n.framework ?? frameworkId) as string,
		folder: (n.folder_id ?? n.folder ?? '') as string
	}));

	return { frameworkPatch, nodes, questions };
}

// --- State ---

const CONTEXT_KEY = 'framework-builder';

export interface BuilderStore {
	framework: Writable<Framework>;
	sections: Writable<BuilderSection[]>;
	saving: Writable<boolean>;
	errors: Writable<Map<string, string>>;
	activeSection: Writable<string>;
	hasPendingFlush: Writable<boolean>;
	unsaved: Writable<boolean>;
	unpublished: Writable<boolean>;
	isScrolling: Writable<boolean>;
	addSection: (afterIndex?: number) => void;
	deleteSection: (sectionIndex: number) => void;
	addRequirement: (parentNodeId: string, parentUrn: string) => void;
	addSplashScreen: (parentNodeId: string, parentUrn: string) => void;
	deleteRequirement: (nodeId: string) => void;
	updateNode: (nodeId: string, patch: Record<string, unknown>) => void;
	addQuestion: (reqNodeId: string, type?: Question['type']) => void;
	updateQuestion: (questionId: string, patch: Record<string, unknown>) => void;
	deleteQuestion: (reqNodeId: string, qIndex: number) => void;
	addChoice: (reqNodeId: string, qIndex: number) => void;
	updateChoice: (choiceId: string, patch: Record<string, unknown>) => void;
	deleteChoice: (reqNodeId: string, qIndex: number, choiceIndex: number) => void;
	reorderSections: (fromIndex: number, toIndex: number) => void;
	reorderRequirements: (parentNodeId: string, fromIndex: number, toIndex: number) => void;
	reorderQuestions: (reqNodeId: string, fromIndex: number, toIndex: number) => void;
	reorderChoices: (reqNodeId: string, qIndex: number, fromIndex: number, toIndex: number) => void;
	updateFramework: (patch: Record<string, unknown>) => void;
	activeLanguage: Writable<string | null>;
	setActiveLanguage: (lang: string | null) => void;
	getTranslationProgress: (lang: string) => { translated: number; total: number };
	copyFromBase: (lang: string) => void;
	addLanguage: (lang: string) => void;
	removeLanguage: (lang: string) => void;
	setBaseLocale: (locale: string) => void;
	flushDraft: () => Promise<void>;
	publish: () => Promise<void>;
	discard: () => Promise<void>;
	destroy: () => void;
}

export function buildTree(nodes: RequirementNode[], questions: Question[]): BuilderSection[] {
	const questionsByNode = new Map<string, Question[]>();
	for (const q of questions) {
		const nodeId = typeof q.requirement_node === 'string' ? q.requirement_node : q.requirement_node;
		if (!questionsByNode.has(nodeId)) {
			questionsByNode.set(nodeId, []);
		}
		questionsByNode.get(nodeId)!.push(q);
	}

	const childrenByUrn = new Map<string, RequirementNode[]>();
	for (const node of nodes) {
		if (node.parent_urn) {
			if (!childrenByUrn.has(node.parent_urn)) {
				childrenByUrn.set(node.parent_urn, []);
			}
			childrenByUrn.get(node.parent_urn)!.push(node);
		}
	}
	for (const children of childrenByUrn.values()) {
		children.sort((a, b) => (a.order_id ?? 0) - (b.order_id ?? 0));
	}

	function buildRequirements(parentUrn: string, depth: number): BuilderRequirement[] {
		const children = childrenByUrn.get(parentUrn) ?? [];
		return children.map((child) => {
			const nodeQuestions = (questionsByNode.get(child.id) ?? [])
				.sort((a, b) => a.order - b.order)
				.map((q) => ({ question: q }));
			const nested = child.urn ? buildRequirements(child.urn, depth + 1) : [];
			return { node: child, questions: nodeQuestions, children: nested, depth };
		});
	}

	const sectionNodes = nodes
		.filter((n) => !n.parent_urn)
		.sort((a, b) => (a.order_id ?? 0) - (b.order_id ?? 0));

	return sectionNodes.map((sectionNode) => {
		if (sectionNode.assessable) {
			const directQuestions = (questionsByNode.get(sectionNode.id) ?? [])
				.sort((a, b) => a.order - b.order)
				.map((q) => ({ question: q }));
			return {
				node: sectionNode,
				requirements: [{ node: sectionNode, questions: directQuestions, children: [], depth: 0 }],
				collapsed: false
			};
		}

		const requirements = sectionNode.urn ? buildRequirements(sectionNode.urn, 0) : [];
		return { node: sectionNode, requirements, collapsed: false };
	});
}

/**
 * Create the builder state. Accepts either:
 * 1. Draft JSON (from editing_draft) -- hydrates from flat arrays
 * 2. Relational data (frameworkData, nodes, questions) -- builds tree directly
 */
export function createBuilderState(
	frameworkData: Framework,
	nodes: RequirementNode[],
	questions: Question[],
	editingDraft?: DraftJSON | null
): BuilderStore {
	const folderId =
		typeof frameworkData.folder === 'string' ? frameworkData.folder : frameworkData.folder.id;
	const frameworkId = frameworkData.id;

	// If we have a draft, hydrate from it; otherwise use relational data
	let initialNodes = nodes;
	let initialQuestions = questions;
	let initialFrameworkData = frameworkData;

	if (editingDraft) {
		const hydrated = hydrateDraft(editingDraft, frameworkId);
		initialNodes = hydrated.nodes;
		initialQuestions = hydrated.questions;
		initialFrameworkData = { ...frameworkData, ...hydrated.frameworkPatch } as Framework;
	}

	const framework = writable<Framework>(initialFrameworkData);
	const initialSections = buildTree(initialNodes, initialQuestions);
	const sections = writable<BuilderSection[]>(initialSections);
	const saving = writable(false);
	const errors = writable<Map<string, string>>(new Map());
	const activeSection = writable<string>(initialSections[0]?.node.id ?? '');
	const hasPendingFlush = writable(false);
	const unsaved = writable(false); // local edits not yet saved to draft
	// Check if the draft was marked dirty by a prior save-draft call
	const draftMarkedDirty = editingDraft && (editingDraft as any)._dirty === true;
	const unpublished = writable(!!draftMarkedDirty);
	const isScrolling = writable(false);
	const activeLanguage = writable<string | null>(null);

	function markDirty() {
		unsaved.set(true);
		unpublished.set(true);
	}

	function setError(key: string, message: string) {
		errors.update((m) => new Map(m).set(key, message));
	}

	function clearError(key: string) {
		errors.update((m) => {
			const next = new Map(m);
			next.delete(key);
			return next;
		});
	}

	function get<T>(store: Writable<T>): T {
		let value: T;
		store.subscribe((v) => (value = v))();
		return value!;
	}

	/** Map all requirements in all sections recursively */
	function updateAllRequirements(fn: (req: BuilderRequirement) => BuilderRequirement) {
		sections.update((s) =>
			s.map((sec) => ({
				...sec,
				requirements: mapRequirements(sec.requirements, fn)
			}))
		);
	}

	/** Find a requirement across all sections */
	function findReqGlobal(nodeId: string): BuilderRequirement | null {
		for (const sec of get(sections)) {
			const found = findRequirement(sec.requirements, nodeId);
			if (found) return found;
		}
		return null;
	}

	// --- Draft save (explicit, triggered by Save button) ---

	let saveInFlight = false;

	async function flushDraft() {
		if (saveInFlight) return;
		saveInFlight = true;
		saving.set(true);
		try {
			const draft = serializeDraft(get(framework), get(sections));
			(draft as any)._dirty = true; // mark draft as having user changes
			await apiSaveDraft(frameworkId, draft);
			unsaved.set(false); // saved to draft, but still unpublished
			clearError('save-draft');
		} catch (e) {
			setError('save-draft', (e as Error).message);
		} finally {
			saving.set(false);
			saveInFlight = false;
		}
	}

	async function publish() {
		await flushDraft();
		try {
			await apiPublishDraft(frameworkId);
			clearError('publish');
		} catch (e) {
			setError('publish', (e as Error).message);
			throw e;
		}
	}

	async function discard() {
		try {
			// Clear the draft on the server
			await apiDiscardDraft(frameworkId);
			// Re-create a fresh draft from live relational data
			const { draft: freshDraft } = await apiStartEditing(frameworkId);
			// Re-hydrate stores from the fresh draft
			const hydrated = hydrateDraft(freshDraft, frameworkId);
			const freshFramework = { ...frameworkData, ...hydrated.frameworkPatch } as Framework;
			const freshSections = buildTree(hydrated.nodes, hydrated.questions);
			framework.set(freshFramework);
			sections.set(freshSections);
			activeSection.set(freshSections[0]?.node.id ?? '');
			unsaved.set(false);
			unpublished.set(false);
			clearError('discard');
		} catch (e) {
			setError('discard', (e as Error).message);
			throw e;
		}
	}

	function destroy() {
		// No cleanup needed — saves are now explicit
	}

	// --- Section CRUD ---

	function addSection(afterIndex?: number) {
		const currentSections = get(sections);
		const order =
			afterIndex !== undefined ? (afterIndex + 1) * 100 + 50 : currentSections.length * 100;

		const newId = crypto.randomUUID();
		const newUrn = `urn:intuitem:risk:req_node:${newId}`;
		const newNode: RequirementNode = {
			id: newId,
			urn: newUrn,
			ref_id: null,
			name: 'New Section',
			description: null,
			annotation: null,
			parent_urn: null,
			order_id: order,
			assessable: false,
			implementation_groups: null,
			typical_evidence: null,
			weight: 1,
			importance: '',
			display_mode: 'default',
			framework: frameworkId,
			folder: folderId
		};
		const newSection: BuilderSection = {
			node: newNode,
			requirements: [],
			collapsed: false
		};
		const idx = afterIndex !== undefined ? afterIndex + 1 : currentSections.length;
		sections.update((s) => [...s.slice(0, idx), newSection, ...s.slice(idx)]);
		markDirty();
	}

	function deleteSection(sectionIndex: number) {
		const section = get(sections)[sectionIndex];
		if (!section) return;
		sections.update((s) => s.filter((_, i) => i !== sectionIndex));
		markDirty();
	}

	// --- Requirement CRUD (node ID-based) ---

	function addSplashScreen(parentNodeId: string, parentUrn: string) {
		const siblings = (() => {
			for (const sec of get(sections)) {
				if (sec.node.id === parentNodeId) return sec.requirements;
			}
			return [];
		})();
		const order = siblings.length * 100;

		const newId = crypto.randomUUID();
		const newNode: RequirementNode = {
			id: newId,
			urn: `urn:intuitem:risk:req_node:${newId}`,
			ref_id: null,
			name: 'New Splash Screen',
			description: null,
			annotation: null,
			parent_urn: parentUrn,
			order_id: order,
			assessable: false,
			implementation_groups: null,
			typical_evidence: null,
			weight: 1,
			importance: '',
			display_mode: 'splash',
			framework: frameworkId,
			folder: folderId
		};
		const newReq: BuilderRequirement = {
			node: newNode,
			questions: [],
			children: [],
			depth: 0
		};
		sections.update((s) =>
			s.map((sec) =>
				sec.node.id === parentNodeId ? { ...sec, requirements: [...sec.requirements, newReq] } : sec
			)
		);
		markDirty();
	}

	function addRequirement(parentNodeId: string, parentUrn: string) {
		const parentReq = findReqGlobal(parentNodeId);
		const siblings = parentReq
			? parentReq.children
			: (() => {
					for (const sec of get(sections)) {
						if (sec.node.id === parentNodeId) return sec.requirements;
					}
					return [];
				})();
		const parentDepth = parentReq ? parentReq.depth : -1;
		const order = siblings.length * 100;

		const newId = crypto.randomUUID();
		const newNode: RequirementNode = {
			id: newId,
			urn: `urn:intuitem:risk:req_node:${newId}`,
			ref_id: null,
			name: 'New Requirement',
			description: null,
			annotation: null,
			parent_urn: parentUrn,
			order_id: order,
			assessable: true,
			implementation_groups: null,
			typical_evidence: null,
			weight: 1,
			importance: '',
			display_mode: 'default',
			framework: frameworkId,
			folder: folderId
		};
		const newReq: BuilderRequirement = {
			node: newNode,
			questions: [],
			children: [],
			depth: parentDepth + 1
		};

		if (parentReq) {
			sections.update((s) =>
				s.map((sec) => ({
					...sec,
					requirements: addChildToRequirement(sec.requirements, parentNodeId, newReq)
				}))
			);
		} else {
			sections.update((s) =>
				s.map((sec) =>
					sec.node.id === parentNodeId
						? { ...sec, requirements: [...sec.requirements, newReq] }
						: sec
				)
			);
		}
		markDirty();
	}

	function deleteRequirement(nodeId: string) {
		sections.update((s) =>
			s.map((sec) => ({
				...sec,
				requirements: removeRequirement(sec.requirements, nodeId)
			}))
		);
		markDirty();
	}

	// --- Node update ---

	function updateNode(nodeId: string, patch: Record<string, unknown>) {
		sections.update((s) =>
			s.map((sec) => ({
				...sec,
				node: sec.node.id === nodeId ? { ...sec.node, ...patch } : sec.node,
				requirements: mapRequirements(sec.requirements, (req) => ({
					...req,
					node: req.node.id === nodeId ? { ...req.node, ...patch } : req.node
				}))
			}))
		);
		markDirty();
	}

	// --- Question CRUD (node ID-based) ---

	function addQuestion(reqNodeId: string, type: Question['type'] = 'text') {
		const req = findReqGlobal(reqNodeId);
		if (!req) return;
		const order = req.questions.length * 100;
		const newId = crypto.randomUUID();
		const urn = `urn:intuitem:risk:question:${newId}`;

		const newQuestion: Question = {
			id: newId,
			urn,
			ref_id: null,
			text: '',
			annotation: null,
			type,
			config: null,
			depends_on: null,
			order,
			weight: 1,
			folder: folderId,
			requirement_node: reqNodeId,
			choices: []
		};
		sections.update((s) =>
			s.map((sec) => ({
				...sec,
				requirements: updateRequirementById(sec.requirements, reqNodeId, (r) => ({
					...r,
					questions: [...r.questions, { question: newQuestion }]
				}))
			}))
		);
		markDirty();
	}

	function updateQuestion(questionId: string, patch: Record<string, unknown>) {
		updateAllRequirements((req) => ({
			...req,
			questions: req.questions.map((q) => ({
				...q,
				question: q.question.id === questionId ? { ...q.question, ...patch } : q.question
			}))
		}));
		markDirty();
	}

	function deleteQuestion(reqNodeId: string, qIndex: number) {
		const req = findReqGlobal(reqNodeId);
		const q = req?.questions[qIndex];
		if (!q) return;
		sections.update((s) =>
			s.map((sec) => ({
				...sec,
				requirements: updateRequirementById(sec.requirements, reqNodeId, (r) => ({
					...r,
					questions: r.questions.filter((_, i) => i !== qIndex)
				}))
			}))
		);
		markDirty();
	}

	// --- Choice CRUD (node ID-based) ---

	function addChoice(reqNodeId: string, qIndex: number) {
		const req = findReqGlobal(reqNodeId);
		const q = req?.questions[qIndex];
		if (!q) return;
		const order = q.question.choices.length * 100;
		const newId = crypto.randomUUID();

		const newChoice: QuestionChoice = {
			id: newId,
			urn: `urn:intuitem:risk:question_choice:${newId}`,
			ref_id: null,
			value: '',
			annotation: null,
			add_score: null,
			compute_result: null,
			order,
			description: null,
			color: null,
			select_implementation_groups: null,
			folder: folderId,
			question: q.question.id
		};
		sections.update((s) =>
			s.map((sec) => ({
				...sec,
				requirements: updateRequirementById(sec.requirements, reqNodeId, (r) => ({
					...r,
					questions: r.questions.map((qq, i) =>
						i === qIndex
							? {
									...qq,
									question: {
										...qq.question,
										choices: [...qq.question.choices, newChoice]
									}
								}
							: qq
					)
				}))
			}))
		);
		markDirty();
	}

	function updateChoice(choiceId: string, patch: Record<string, unknown>) {
		updateAllRequirements((req) => ({
			...req,
			questions: req.questions.map((q) => ({
				...q,
				question: {
					...q.question,
					choices: q.question.choices.map((c) => (c.id === choiceId ? { ...c, ...patch } : c))
				}
			}))
		}));
		markDirty();
	}

	function deleteChoice(reqNodeId: string, qIndex: number, choiceIndex: number) {
		const req = findReqGlobal(reqNodeId);
		const choice = req?.questions[qIndex]?.question.choices[choiceIndex];
		if (!choice) return;
		sections.update((s) =>
			s.map((sec) => ({
				...sec,
				requirements: updateRequirementById(sec.requirements, reqNodeId, (r) => ({
					...r,
					questions: r.questions.map((qq, i) =>
						i === qIndex
							? {
									...qq,
									question: {
										...qq.question,
										choices: qq.question.choices.filter((_, ci) => ci !== choiceIndex)
									}
								}
							: qq
					)
				}))
			}))
		);
		markDirty();
	}

	// --- Reorder ---

	function reorderSections(fromIndex: number, toIndex: number) {
		if (fromIndex === toIndex) return;
		sections.update((s) => {
			const copy = [...s];
			const [moved] = copy.splice(fromIndex, 1);
			copy.splice(toIndex, 0, moved);
			// Update order_id on all sections
			return copy.map((sec, i) => ({
				...sec,
				node: { ...sec.node, order_id: i * 100 }
			}));
		});
		markDirty();
	}

	function reorderRequirements(parentNodeId: string, fromIndex: number, toIndex: number) {
		if (fromIndex === toIndex) return;

		sections.update((s) =>
			s.map((sec) => {
				if (sec.node.id === parentNodeId) {
					const reqs = [...sec.requirements];
					const [moved] = reqs.splice(fromIndex, 1);
					reqs.splice(toIndex, 0, moved);
					return {
						...sec,
						requirements: reqs.map((r, i) => ({
							...r,
							node: { ...r.node, order_id: i * 100 }
						}))
					};
				}
				return {
					...sec,
					requirements: updateRequirementById(sec.requirements, parentNodeId, (r) => {
						const kids = [...r.children];
						const [moved] = kids.splice(fromIndex, 1);
						kids.splice(toIndex, 0, moved);
						return {
							...r,
							children: kids.map((k, i) => ({
								...k,
								node: { ...k.node, order_id: i * 100 }
							}))
						};
					})
				};
			})
		);
		markDirty();
	}

	function reorderQuestions(reqNodeId: string, fromIndex: number, toIndex: number) {
		if (fromIndex === toIndex) return;
		sections.update((s) =>
			s.map((sec) => ({
				...sec,
				requirements: updateRequirementById(sec.requirements, reqNodeId, (r) => {
					const qs = [...r.questions];
					const [moved] = qs.splice(fromIndex, 1);
					qs.splice(toIndex, 0, moved);
					return {
						...r,
						questions: qs.map((q, i) => ({
							...q,
							question: { ...q.question, order: i * 100 }
						}))
					};
				})
			}))
		);
		markDirty();
	}

	function reorderChoices(reqNodeId: string, qIndex: number, fromIndex: number, toIndex: number) {
		if (fromIndex === toIndex) return;
		sections.update((s) =>
			s.map((sec) => ({
				...sec,
				requirements: updateRequirementById(sec.requirements, reqNodeId, (r) => ({
					...r,
					questions: r.questions.map((qq, i) => {
						if (i !== qIndex) return qq;
						const choices = [...qq.question.choices];
						const [moved] = choices.splice(fromIndex, 1);
						choices.splice(toIndex, 0, moved);
						return {
							...qq,
							question: {
								...qq.question,
								choices: choices.map((c, ci) => ({ ...c, order: ci * 100 }))
							}
						};
					})
				}))
			}))
		);
		markDirty();
	}

	function doUpdateFramework(patch: Record<string, unknown>) {
		framework.update((f) => ({ ...f, ...patch }) as Framework);
		markDirty();
	}

	function setActiveLanguage(lang: string | null) {
		activeLanguage.set(lang);
	}

	function addLanguage(lang: string) {
		const code = lang.trim().toLowerCase();
		if (!code) return;
		framework.update((f) => {
			const langs = new Set(f.available_languages ?? []);
			langs.add(code);
			return { ...f, available_languages: [...langs].sort() };
		});
		markDirty();
	}

	function removeLanguage(lang: string) {
		framework.update((f) => ({
			...f,
			available_languages: (f.available_languages ?? []).filter((l) => l !== lang)
		}));
		// Deselect if currently active
		const currentLang = get(activeLanguage);
		if (currentLang === lang) activeLanguage.set(null);
		markDirty();
	}

	function setBaseLocale(newLocale: string) {
		const fw = get(framework);
		const oldLocale = fw.locale ?? 'en';
		if (newLocale === oldLocale) return;

		// --- Swap framework meta fields ---
		const fwTrans = { ...(fw.translations ?? {}) };
		// Demote current base fields into translations[oldLocale]
		const demoted: Record<string, string> = {};
		if (fw.name) demoted.name = fw.name;
		if (fw.description) demoted.description = fw.description;
		if (fw.annotation) demoted.annotation = fw.annotation;
		fwTrans[oldLocale] = demoted;
		// Promote translations[newLocale] to base fields
		const promoted = fwTrans[newLocale] ?? {};
		delete fwTrans[newLocale];

		// Swap nested translations in scores_definition entries
		const swappedScores = swapJsonEntryTranslations(fw.scores_definition, oldLocale, newLocale, [
			'name',
			'description'
		]);
		// Swap nested translations in implementation_groups_definition entries
		const swappedIgs = swapJsonArrayTranslations(
			fw.implementation_groups_definition,
			oldLocale,
			newLocale,
			['name', 'description']
		);
		// Swap nested translations in outcomes_definition entries
		const swappedOutcomes = swapJsonArrayTranslations(
			fw.outcomes_definition as Record<string, unknown>[] | null,
			oldLocale,
			newLocale,
			['annotation']
		);

		// Update available_languages
		const langs = new Set(fw.available_languages ?? []);
		langs.delete(newLocale);
		langs.add(oldLocale);

		framework.update((f) => ({
			...f,
			locale: newLocale,
			name: promoted.name || f.name,
			description: promoted.description || f.description,
			annotation: promoted.annotation || f.annotation,
			translations: fwTrans,
			scores_definition: swappedScores,
			implementation_groups_definition: swappedIgs,
			outcomes_definition: swappedOutcomes as typeof f.outcomes_definition,
			available_languages: [...langs].sort()
		}));

		// --- Swap all node/question/choice fields ---
		sections.update((secs) =>
			secs.map((sec) => ({
				...sec,
				node: swapNodeFields(sec.node, oldLocale, newLocale),
				requirements: swapReqFields(sec.requirements, oldLocale, newLocale)
			}))
		);

		// If we were translating into the new base, deselect
		const currentLang = get(activeLanguage);
		if (currentLang === newLocale) activeLanguage.set(null);
		markDirty();
	}

	/** Swap base ↔ translation fields on a RequirementNode */
	function swapNodeFields(
		node: RequirementNode,
		oldLocale: string,
		newLocale: string
	): RequirementNode {
		const trans = { ...(node.translations ?? {}) };
		// Demote current base fields
		const demoted: Record<string, string> = {};
		if (node.name) demoted.name = node.name;
		if (node.description) demoted.description = node.description;
		if (node.annotation) demoted.annotation = node.annotation;
		if (node.typical_evidence) demoted.typical_evidence = node.typical_evidence;
		trans[oldLocale] = demoted;
		// Promote new locale
		const promoted = trans[newLocale] ?? {};
		delete trans[newLocale];
		return {
			...node,
			name: promoted.name || node.name,
			description: promoted.description || node.description,
			annotation: promoted.annotation || node.annotation,
			typical_evidence: promoted.typical_evidence || node.typical_evidence,
			translations: trans
		};
	}

	/** Swap base ↔ translation fields on a Question */
	function swapQuestionFields(q: Question, oldLocale: string, newLocale: string): Question {
		const trans = { ...(q.translations ?? {}) };
		const demoted: Record<string, string> = {};
		if (q.text) demoted.text = q.text;
		trans[oldLocale] = demoted;
		const promoted = trans[newLocale] ?? {};
		delete trans[newLocale];
		return {
			...q,
			text: promoted.text || q.text,
			translations: trans,
			choices: q.choices.map((c) => swapChoiceFields(c, oldLocale, newLocale))
		};
	}

	/** Swap base ↔ translation fields on a QuestionChoice */
	function swapChoiceFields(
		c: QuestionChoice,
		oldLocale: string,
		newLocale: string
	): QuestionChoice {
		const trans = { ...(c.translations ?? {}) };
		const demoted: Record<string, string> = {};
		if (c.value) demoted.value = c.value;
		if (c.description) demoted.description = c.description;
		trans[oldLocale] = demoted;
		const promoted = trans[newLocale] ?? {};
		delete trans[newLocale];
		return {
			...c,
			value: promoted.value || c.value,
			description: promoted.description || c.description,
			translations: trans
		};
	}

	/** Recursively swap fields on all requirements */
	function swapReqFields(
		reqs: BuilderRequirement[],
		oldLocale: string,
		newLocale: string
	): BuilderRequirement[] {
		return reqs.map((req) => ({
			...req,
			node: swapNodeFields(req.node, oldLocale, newLocale),
			questions: req.questions.map((bq) => ({
				...bq,
				question: swapQuestionFields(bq.question, oldLocale, newLocale)
			})),
			children: swapReqFields(req.children, oldLocale, newLocale)
		}));
	}

	/**
	 * Swap translations in a scores_definition JSON (handles both array and {scale:[...]} shapes).
	 * Each entry has name/description + nested translations.
	 */
	function swapJsonEntryTranslations(
		def: Record<string, unknown> | null,
		oldLocale: string,
		newLocale: string,
		fields: string[]
	): Record<string, unknown> | null {
		if (!def) return def;
		if (Array.isArray(def)) {
			return def.map((e) =>
				swapSingleEntryTranslations(e as Record<string, unknown>, oldLocale, newLocale, fields)
			) as unknown as Record<string, unknown>;
		}
		if ('scale' in def && Array.isArray(def.scale)) {
			return {
				...def,
				scale: (def.scale as Record<string, unknown>[]).map((e) =>
					swapSingleEntryTranslations(e, oldLocale, newLocale, fields)
				)
			};
		}
		return def;
	}

	/** Swap translations in an array of JSON objects (IG defs, outcome defs) */
	function swapJsonArrayTranslations(
		arr: Record<string, unknown>[] | null,
		oldLocale: string,
		newLocale: string,
		fields: string[]
	): Record<string, unknown>[] | null {
		if (!arr) return arr;
		return arr.map((e) => swapSingleEntryTranslations(e, oldLocale, newLocale, fields));
	}

	/** Swap base ↔ translation on a single JSON entry with a translations sub-dict */
	function swapSingleEntryTranslations(
		entry: Record<string, unknown>,
		oldLocale: string,
		newLocale: string,
		fields: string[]
	): Record<string, unknown> {
		const trans = { ...((entry.translations as Record<string, Record<string, string>>) ?? {}) };
		// Demote current base fields
		const demoted: Record<string, string> = {};
		for (const f of fields) {
			if (entry[f]) demoted[f] = entry[f] as string;
		}
		trans[oldLocale] = demoted;
		// Promote new locale
		const promoted = trans[newLocale] ?? {};
		delete trans[newLocale];
		const result = { ...entry, translations: trans };
		for (const f of fields) {
			if (promoted[f]) result[f] = promoted[f];
		}
		return result;
	}

	function getTranslationProgress(lang: string): { translated: number; total: number } {
		let total = 0;
		let translated = 0;
		const secs = get(sections);

		function checkNode(node: RequirementNode) {
			if (node.name) {
				total++;
				if (node.translations?.[lang]?.name) translated++;
			}
		}

		function walkReqs(reqs: BuilderRequirement[]) {
			for (const req of reqs) {
				checkNode(req.node);
				for (const bq of req.questions) {
					if (bq.question.text) {
						total++;
						if (bq.question.translations?.[lang]?.text) translated++;
					}
					for (const c of bq.question.choices) {
						if (c.value) {
							total++;
							if (c.translations?.[lang]?.value) translated++;
						}
					}
				}
				walkReqs(req.children);
			}
		}

		for (const sec of secs) {
			checkNode(sec.node);
			walkReqs(sec.requirements);
		}
		return { translated, total };
	}

	function copyFromBase(lang: string) {
		sections.update((secs) =>
			secs.map((sec) => ({
				...sec,
				node: copyNodeTranslations(sec.node, lang),
				requirements: copyReqTranslations(sec.requirements, lang)
			}))
		);
		markDirty();
	}

	function copyNodeTranslations(node: RequirementNode, lang: string): RequirementNode {
		const fields: Record<string, string> = {};
		if (node.name) fields.name = node.name;
		if (node.description) fields.description = node.description;
		if (node.annotation) fields.annotation = node.annotation;
		if (node.typical_evidence) fields.typical_evidence = node.typical_evidence;
		if (Object.keys(fields).length === 0) return node;
		const existing = node.translations?.[lang] ?? {};
		// Only copy fields that are not already translated
		const merged: Record<string, string> = { ...fields };
		for (const [k, v] of Object.entries(existing)) {
			if (v) merged[k] = v;
		}
		return { ...node, translations: { ...(node.translations ?? {}), [lang]: merged } };
	}

	function copyReqTranslations(reqs: BuilderRequirement[], lang: string): BuilderRequirement[] {
		return reqs.map((req) => ({
			...req,
			node: copyNodeTranslations(req.node, lang),
			questions: req.questions.map((bq) => ({
				...bq,
				question: copyQuestionTranslations(bq.question, lang)
			})),
			children: copyReqTranslations(req.children, lang)
		}));
	}

	function copyQuestionTranslations(q: Question, lang: string): Question {
		const fields: Record<string, string> = {};
		if (q.text) fields.text = q.text;
		if (Object.keys(fields).length === 0 && q.choices.length === 0) return q;
		const existing = q.translations?.[lang] ?? {};
		const merged: Record<string, string> = { ...fields };
		for (const [k, v] of Object.entries(existing)) {
			if (v) merged[k] = v;
		}
		return {
			...q,
			translations:
				Object.keys(merged).length > 0
					? { ...(q.translations ?? {}), [lang]: merged }
					: q.translations,
			choices: q.choices.map((c) => {
				const cFields: Record<string, string> = {};
				if (c.value) cFields.value = c.value;
				if (c.description) cFields.description = c.description;
				if (Object.keys(cFields).length === 0) return c;
				const cExisting = c.translations?.[lang] ?? {};
				const cMerged: Record<string, string> = { ...cFields };
				for (const [k, v] of Object.entries(cExisting)) {
					if (v) cMerged[k] = v;
				}
				return { ...c, translations: { ...(c.translations ?? {}), [lang]: cMerged } };
			})
		};
	}

	return {
		framework,
		sections,
		saving,
		errors,
		activeSection,
		hasPendingFlush,
		unsaved,
		unpublished,
		isScrolling,
		addSection,
		deleteSection,
		addRequirement,
		addSplashScreen,
		deleteRequirement,
		updateNode,
		addQuestion,
		updateQuestion,
		deleteQuestion,
		addChoice,
		updateChoice,
		deleteChoice,
		reorderSections,
		reorderRequirements,
		reorderQuestions,
		reorderChoices,
		updateFramework: doUpdateFramework,
		activeLanguage,
		setActiveLanguage,
		getTranslationProgress,
		copyFromBase,
		addLanguage,
		removeLanguage,
		setBaseLocale,
		flushDraft,
		publish,
		discard,
		destroy
	};
}

export function setBuilderContext(store: BuilderStore) {
	setContext(CONTEXT_KEY, store);
}

export function getBuilderContext(): BuilderStore {
	return getContext<BuilderStore>(CONTEXT_KEY);
}
