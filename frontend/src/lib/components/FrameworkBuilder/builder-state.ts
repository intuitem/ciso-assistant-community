import { getContext, setContext } from 'svelte';
import { writable, type Writable } from 'svelte/store';
import { apiCreate, apiUpdate, apiDelete } from './builder-api';

// --- Types ---

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
	framework: string | { id: string };
	folder: { id: string; str: string } | string;
}

export interface Framework {
	id: string;
	name: string;
	description: string | null;
	folder: { id: string; str: string };
	library: { id: string; str: string } | null;
	min_score: number;
	max_score: number;
	scores_definition: Record<string, unknown>[] | null;
	implementation_groups_definition: Record<string, unknown>[] | null;
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
function findRequirement(
	reqs: BuilderRequirement[],
	nodeId: string
): BuilderRequirement | null {
	for (const req of reqs) {
		if (req.node.id === nodeId) return req;
		const found = findRequirement(req.children, nodeId);
		if (found) return found;
	}
	return null;
}

/** Remove a requirement by node ID from a recursive tree */
function removeRequirement(
	reqs: BuilderRequirement[],
	nodeId: string
): BuilderRequirement[] {
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

// --- State ---

const CONTEXT_KEY = 'framework-builder';

export interface BuilderStore {
	framework: Writable<Framework>;
	sections: Writable<BuilderSection[]>;
	saving: Writable<boolean>;
	errors: Writable<Map<string, string>>;
	activeSection: Writable<string>;
	addSection: (afterIndex?: number) => Promise<void>;
	deleteSection: (sectionIndex: number) => Promise<void>;
	addRequirement: (parentNodeId: string, parentUrn: string) => Promise<void>;
	deleteRequirement: (nodeId: string) => Promise<void>;
	updateNode: (nodeId: string, patch: Record<string, unknown>) => Promise<void>;
	addQuestion: (reqNodeId: string, type?: Question['type']) => Promise<void>;
	updateQuestion: (questionId: string, patch: Record<string, unknown>) => Promise<void>;
	deleteQuestion: (reqNodeId: string, qIndex: number) => Promise<void>;
	addChoice: (reqNodeId: string, qIndex: number) => Promise<void>;
	updateChoice: (choiceId: string, patch: Record<string, unknown>) => Promise<void>;
	deleteChoice: (reqNodeId: string, qIndex: number, choiceIndex: number) => Promise<void>;
	reorderSections: (fromIndex: number, toIndex: number) => Promise<void>;
	reorderRequirements: (parentNodeId: string, fromIndex: number, toIndex: number) => Promise<void>;
	reorderQuestions: (reqNodeId: string, fromIndex: number, toIndex: number) => Promise<void>;
	reorderChoices: (
		reqNodeId: string,
		qIndex: number,
		fromIndex: number,
		toIndex: number
	) => Promise<void>;
	updateFramework: (patch: Record<string, unknown>) => Promise<void>;
}

function buildTree(nodes: RequirementNode[], questions: Question[]): BuilderSection[] {
	const questionsByNode = new Map<string, Question[]>();
	for (const q of questions) {
		const nodeId =
			typeof q.requirement_node === 'string' ? q.requirement_node : q.requirement_node;
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
				requirements: [
					{ node: sectionNode, questions: directQuestions, children: [], depth: 0 }
				],
				collapsed: false
			};
		}

		const requirements = sectionNode.urn ? buildRequirements(sectionNode.urn, 0) : [];
		return { node: sectionNode, requirements, collapsed: false };
	});
}

export function createBuilderState(
	frameworkData: Framework,
	nodes: RequirementNode[],
	questions: Question[]
): BuilderStore {
	const folderId =
		typeof frameworkData.folder === 'string' ? frameworkData.folder : frameworkData.folder.id;
	const frameworkId = frameworkData.id;

	const framework = writable<Framework>(frameworkData);
	const initialSections = buildTree(nodes, questions);
	const sections = writable<BuilderSection[]>(initialSections);
	const saving = writable(false);
	const errors = writable<Map<string, string>>(new Map());
	const activeSection = writable<string>(initialSections[0]?.node.id ?? '');

	function setError(key: string, message: string) {
		errors.update((m) => new Map(m).set(key, message));
		setTimeout(() => clearError(key), 5000);
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
	function updateAllRequirements(
		fn: (req: BuilderRequirement) => BuilderRequirement
	) {
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

	// --- Section CRUD ---

	async function addSection(afterIndex?: number) {
		const currentSections = get(sections);
		const order =
			afterIndex !== undefined
				? (afterIndex + 1) * 100 + 50
				: currentSections.length * 100;

		try {
			saving.set(true);
			const created = await apiCreate('requirement-nodes', {
				urn: `urn:intuitem:risk:req_node:${crypto.randomUUID()}`,
				name: 'New Section',
				assessable: false,
				order_id: order,
				framework: frameworkId,
				folder: folderId
			});
			const newSection: BuilderSection = {
				node: created,
				requirements: [],
				collapsed: false
			};
			const idx = afterIndex !== undefined ? afterIndex + 1 : currentSections.length;
			sections.update((s) => [...s.slice(0, idx), newSection, ...s.slice(idx)]);
		} catch (e) {
			setError('add-section', (e as Error).message);
		} finally {
			saving.set(false);
		}
	}

	async function deleteSection(sectionIndex: number) {
		const section = get(sections)[sectionIndex];
		if (!section) return;
		try {
			saving.set(true);
			await apiDelete('requirement-nodes', section.node.id);
			sections.update((s) => s.filter((_, i) => i !== sectionIndex));
		} catch (e) {
			setError(`delete-section-${section.node.id}`, (e as Error).message);
		} finally {
			saving.set(false);
		}
	}

	// --- Requirement CRUD (node ID-based) ---

	async function addRequirement(parentNodeId: string, parentUrn: string) {
		const parentReq = findReqGlobal(parentNodeId);
		const siblings = parentReq ? parentReq.children : (() => {
			for (const sec of get(sections)) {
				if (sec.node.id === parentNodeId) return sec.requirements;
			}
			return [];
		})();
		const parentDepth = parentReq ? parentReq.depth : -1;
		const order = siblings.length * 100;

		try {
			saving.set(true);
			const created = await apiCreate('requirement-nodes', {
				urn: `urn:intuitem:risk:req_node:${crypto.randomUUID()}`,
				name: 'New Requirement',
				assessable: true,
				order_id: order,
				parent_urn: parentUrn,
				framework: frameworkId,
				folder: folderId
			});
			const newReq: BuilderRequirement = {
				node: created,
				questions: [],
				children: [],
				depth: parentDepth + 1
			};

			if (parentReq) {
				// Adding as child of a requirement
				sections.update((s) =>
					s.map((sec) => ({
						...sec,
						requirements: addChildToRequirement(sec.requirements, parentNodeId, newReq)
					}))
				);
			} else {
				// Adding as direct child of a section
				sections.update((s) =>
					s.map((sec) =>
						sec.node.id === parentNodeId
							? { ...sec, requirements: [...sec.requirements, newReq] }
							: sec
					)
				);
			}
		} catch (e) {
			setError('add-requirement', (e as Error).message);
		} finally {
			saving.set(false);
		}
	}

	async function deleteRequirement(nodeId: string) {
		try {
			saving.set(true);
			await apiDelete('requirement-nodes', nodeId);
			sections.update((s) =>
				s.map((sec) => ({
					...sec,
					requirements: removeRequirement(sec.requirements, nodeId)
				}))
			);
		} catch (e) {
			setError(`delete-req-${nodeId}`, (e as Error).message);
		} finally {
			saving.set(false);
		}
	}

	// --- Node update ---

	async function updateNode(nodeId: string, patch: Record<string, unknown>) {
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
		try {
			saving.set(true);
			await apiUpdate('requirement-nodes', nodeId, patch);
			clearError(`node-${nodeId}`);
		} catch (e) {
			setError(`node-${nodeId}`, (e as Error).message);
			throw e;
		} finally {
			saving.set(false);
		}
	}

	// --- Question CRUD (node ID-based) ---

	async function addQuestion(reqNodeId: string, type: Question['type'] = 'text') {
		const req = findReqGlobal(reqNodeId);
		if (!req) return;
		const order = req.questions.length * 100;
		const urn = `urn:intuitem:risk:question:${crypto.randomUUID()}`;

		try {
			saving.set(true);
			const created = await apiCreate('questions', {
				urn,
				text: '',
				type,
				order,
				weight: 1,
				requirement_node: reqNodeId,
				folder: folderId
			});
			created.choices = created.choices ?? [];
			sections.update((s) =>
				s.map((sec) => ({
					...sec,
					requirements: updateRequirementById(sec.requirements, reqNodeId, (r) => ({
						...r,
						questions: [...r.questions, { question: created }]
					}))
				}))
			);
		} catch (e) {
			setError('add-question', (e as Error).message);
		} finally {
			saving.set(false);
		}
	}

	async function updateQuestion(questionId: string, patch: Record<string, unknown>) {
		updateAllRequirements((req) => ({
			...req,
			questions: req.questions.map((q) => ({
				...q,
				question:
					q.question.id === questionId ? { ...q.question, ...patch } : q.question
			}))
		}));
		try {
			saving.set(true);
			await apiUpdate('questions', questionId, patch);
			clearError(`question-${questionId}`);
		} catch (e) {
			setError(`question-${questionId}`, (e as Error).message);
			throw e;
		} finally {
			saving.set(false);
		}
	}

	async function deleteQuestion(reqNodeId: string, qIndex: number) {
		const req = findReqGlobal(reqNodeId);
		const q = req?.questions[qIndex];
		if (!q) return;
		try {
			saving.set(true);
			await apiDelete('questions', q.question.id);
			sections.update((s) =>
				s.map((sec) => ({
					...sec,
					requirements: updateRequirementById(sec.requirements, reqNodeId, (r) => ({
						...r,
						questions: r.questions.filter((_, i) => i !== qIndex)
					}))
				}))
			);
		} catch (e) {
			setError(`delete-question-${q.question.id}`, (e as Error).message);
		} finally {
			saving.set(false);
		}
	}

	// --- Choice CRUD (node ID-based) ---

	async function addChoice(reqNodeId: string, qIndex: number) {
		const req = findReqGlobal(reqNodeId);
		const q = req?.questions[qIndex];
		if (!q) return;
		const order = q.question.choices.length * 100;

		try {
			saving.set(true);
			const created = await apiCreate('question-choices', {
				value: '',
				order,
				question: q.question.id,
				folder: folderId
			});
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
											choices: [...qq.question.choices, created]
										}
									}
								: qq
						)
					}))
				}))
			);
		} catch (e) {
			setError('add-choice', (e as Error).message);
		} finally {
			saving.set(false);
		}
	}

	async function updateChoice(choiceId: string, patch: Record<string, unknown>) {
		updateAllRequirements((req) => ({
			...req,
			questions: req.questions.map((q) => ({
				...q,
				question: {
					...q.question,
					choices: q.question.choices.map((c) =>
						c.id === choiceId ? { ...c, ...patch } : c
					)
				}
			}))
		}));
		try {
			saving.set(true);
			await apiUpdate('question-choices', choiceId, patch);
			clearError(`choice-${choiceId}`);
		} catch (e) {
			setError(`choice-${choiceId}`, (e as Error).message);
			throw e;
		} finally {
			saving.set(false);
		}
	}

	async function deleteChoice(reqNodeId: string, qIndex: number, choiceIndex: number) {
		const req = findReqGlobal(reqNodeId);
		const choice = req?.questions[qIndex]?.question.choices[choiceIndex];
		if (!choice) return;
		try {
			saving.set(true);
			await apiDelete('question-choices', choice.id);
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
											choices: qq.question.choices.filter(
												(_, ci) => ci !== choiceIndex
											)
										}
									}
								: qq
						)
					}))
				}))
			);
		} catch (e) {
			setError(`delete-choice-${choice.id}`, (e as Error).message);
		} finally {
			saving.set(false);
		}
	}

	// --- Reorder ---

	async function reorderSections(fromIndex: number, toIndex: number) {
		if (fromIndex === toIndex) return;
		sections.update((s) => {
			const copy = [...s];
			const [moved] = copy.splice(fromIndex, 1);
			copy.splice(toIndex, 0, moved);
			return copy;
		});
		try {
			saving.set(true);
			const current = get(sections);
			await Promise.all(
				current.map((s, i) =>
					apiUpdate('requirement-nodes', s.node.id, { order_id: i * 100 })
				)
			);
		} catch (e) {
			setError('reorder-sections', (e as Error).message);
		} finally {
			saving.set(false);
		}
	}

	async function reorderRequirements(
		parentNodeId: string,
		fromIndex: number,
		toIndex: number
	) {
		if (fromIndex === toIndex) return;

		// Reorder could be at section level or inside a requirement
		sections.update((s) =>
			s.map((sec) => {
				if (sec.node.id === parentNodeId) {
					const reqs = [...sec.requirements];
					const [moved] = reqs.splice(fromIndex, 1);
					reqs.splice(toIndex, 0, moved);
					return { ...sec, requirements: reqs };
				}
				return {
					...sec,
					requirements: updateRequirementById(sec.requirements, parentNodeId, (r) => {
						const kids = [...r.children];
						const [moved] = kids.splice(fromIndex, 1);
						kids.splice(toIndex, 0, moved);
						return { ...r, children: kids };
					})
				};
			})
		);

		try {
			saving.set(true);
			// Find the reordered list to persist order_ids
			const parentReq = findReqGlobal(parentNodeId);
			const reorderedList = parentReq
				? parentReq.children
				: get(sections).find((s) => s.node.id === parentNodeId)?.requirements ?? [];
			await Promise.all(
				reorderedList.map((r, i) =>
					apiUpdate('requirement-nodes', r.node.id, { order_id: i * 100 })
				)
			);
		} catch (e) {
			setError('reorder-requirements', (e as Error).message);
		} finally {
			saving.set(false);
		}
	}

	async function reorderQuestions(reqNodeId: string, fromIndex: number, toIndex: number) {
		if (fromIndex === toIndex) return;
		sections.update((s) =>
			s.map((sec) => ({
				...sec,
				requirements: updateRequirementById(sec.requirements, reqNodeId, (r) => {
					const qs = [...r.questions];
					const [moved] = qs.splice(fromIndex, 1);
					qs.splice(toIndex, 0, moved);
					return { ...r, questions: qs };
				})
			}))
		);
		try {
			saving.set(true);
			const req = findReqGlobal(reqNodeId);
			if (req) {
				await Promise.all(
					req.questions.map((q, i) =>
						apiUpdate('questions', q.question.id, { order: i * 100 })
					)
				);
			}
		} catch (e) {
			setError('reorder-questions', (e as Error).message);
		} finally {
			saving.set(false);
		}
	}

	async function reorderChoices(
		reqNodeId: string,
		qIndex: number,
		fromIndex: number,
		toIndex: number
	) {
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
						return { ...qq, question: { ...qq.question, choices } };
					})
				}))
			}))
		);
		try {
			saving.set(true);
			const req = findReqGlobal(reqNodeId);
			const choices = req?.questions[qIndex]?.question.choices;
			if (choices) {
				await Promise.all(
					choices.map((c, i) =>
						apiUpdate('question-choices', c.id, { order: i * 100 })
					)
				);
			}
		} catch (e) {
			setError('reorder-choices', (e as Error).message);
		} finally {
			saving.set(false);
		}
	}

	async function doUpdateFramework(patch: Record<string, unknown>) {
		try {
			saving.set(true);
			await apiUpdate('frameworks', frameworkId, patch);
			framework.update((f) => ({ ...f, ...patch }) as Framework);
			clearError('framework');
		} catch (e) {
			setError('framework', (e as Error).message);
			throw e;
		} finally {
			saving.set(false);
		}
	}

	return {
		framework,
		sections,
		saving,
		errors,
		activeSection,
		addSection,
		deleteSection,
		addRequirement,
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
		updateFramework: doUpdateFramework
	};
}

export function setBuilderContext(store: BuilderStore) {
	setContext(CONTEXT_KEY, store);
}

export function getBuilderContext(): BuilderStore {
	return getContext<BuilderStore>(CONTEXT_KEY);
}
