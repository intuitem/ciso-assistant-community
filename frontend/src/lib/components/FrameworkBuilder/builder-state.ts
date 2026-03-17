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
}

export interface BuilderQuestion {
	question: Question;
}

export interface BuilderSection {
	node: RequirementNode;
	requirements: BuilderRequirement[];
	collapsed: boolean;
}

// --- State ---

const CONTEXT_KEY = 'framework-builder';

export interface BuilderStore {
	framework: Writable<Framework>;
	sections: Writable<BuilderSection[]>;
	saving: Writable<boolean>;
	errors: Writable<Map<string, string>>;
	activeSection: Writable<string>;
	// Methods
	addSection: (afterIndex?: number) => Promise<void>;
	deleteSection: (sectionIndex: number) => Promise<void>;
	addRequirement: (sectionIndex: number, afterIndex?: number) => Promise<void>;
	deleteRequirement: (sectionIndex: number, reqIndex: number) => Promise<void>;
	updateNode: (nodeId: string, patch: Record<string, unknown>) => Promise<void>;
	addQuestion: (sectionIndex: number, reqIndex: number, type?: Question['type']) => Promise<void>;
	updateQuestion: (questionId: string, patch: Record<string, unknown>) => Promise<void>;
	deleteQuestion: (sectionIndex: number, reqIndex: number, qIndex: number) => Promise<void>;
	addChoice: (sectionIndex: number, reqIndex: number, qIndex: number) => Promise<void>;
	updateChoice: (choiceId: string, patch: Record<string, unknown>) => Promise<void>;
	deleteChoice: (
		sectionIndex: number,
		reqIndex: number,
		qIndex: number,
		choiceIndex: number
	) => Promise<void>;
	reorderSections: (fromIndex: number, toIndex: number) => Promise<void>;
	reorderRequirements: (sectionIndex: number, fromIndex: number, toIndex: number) => Promise<void>;
	reorderQuestions: (
		sectionIndex: number,
		reqIndex: number,
		fromIndex: number,
		toIndex: number
	) => Promise<void>;
	reorderChoices: (
		sectionIndex: number,
		reqIndex: number,
		qIndex: number,
		fromIndex: number,
		toIndex: number
	) => Promise<void>;
	updateFramework: (patch: Record<string, unknown>) => Promise<void>;
}

function buildTree(nodes: RequirementNode[], questions: Question[]): BuilderSection[] {
	// Map questions by requirement_node id
	const questionsByNode = new Map<string, Question[]>();
	for (const q of questions) {
		const nodeId = typeof q.requirement_node === 'string' ? q.requirement_node : q.requirement_node;
		if (!questionsByNode.has(nodeId)) {
			questionsByNode.set(nodeId, []);
		}
		questionsByNode.get(nodeId)!.push(q);
	}

	// Build parent_urn -> children lookup
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

	// Recursively collect all descendant nodes that have questions or are assessable
	function collectRequirements(parentUrn: string): BuilderRequirement[] {
		const children = childrenByUrn.get(parentUrn) ?? [];
		const result: BuilderRequirement[] = [];

		for (const child of children) {
			const nodeQuestions = (questionsByNode.get(child.id) ?? [])
				.sort((a, b) => a.order - b.order)
				.map((q) => ({ question: q }));

			// If this node has questions or is assessable, show it as a requirement
			if (nodeQuestions.length > 0 || child.assessable) {
				result.push({ node: child, questions: nodeQuestions });
			}

			// Also collect from deeper descendants
			if (child.urn) {
				result.push(...collectRequirements(child.urn));
			}
		}

		return result;
	}

	// Top-level sections: non-assessable with no parent, or assessable with no parent
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
				requirements: [{ node: sectionNode, questions: directQuestions }],
				collapsed: false
			};
		}

		const requirements = sectionNode.urn ? collectRequirements(sectionNode.urn) : [];

		return {
			node: sectionNode,
			requirements,
			collapsed: false
		};
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

	// Helper to read current store value synchronously
	function get<T>(store: Writable<T>): T {
		let value: T;
		store.subscribe((v) => (value = v))();
		return value!;
	}

	async function addSection(afterIndex?: number) {
		const currentSections = get(sections);
		const order =
			afterIndex !== undefined ? (afterIndex + 1) * 100 + 50 : currentSections.length * 100;

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

	async function addRequirement(sectionIndex: number, afterIndex?: number) {
		const section = get(sections)[sectionIndex];
		if (!section) return;
		const reqs = section.requirements;
		const order = afterIndex !== undefined ? (afterIndex + 1) * 100 + 50 : reqs.length * 100;

		try {
			saving.set(true);
			const created = await apiCreate('requirement-nodes', {
				urn: `urn:intuitem:risk:req_node:${crypto.randomUUID()}`,
				name: 'New Requirement',
				assessable: true,
				order_id: order,
				parent_urn: section.node.urn,
				framework: frameworkId,
				folder: folderId
			});
			const newReq: BuilderRequirement = { node: created, questions: [] };
			const idx = afterIndex !== undefined ? afterIndex + 1 : reqs.length;
			sections.update((s) => {
				const copy = [...s];
				copy[sectionIndex] = {
					...copy[sectionIndex],
					requirements: [...reqs.slice(0, idx), newReq, ...reqs.slice(idx)]
				};
				return copy;
			});
		} catch (e) {
			setError('add-requirement', (e as Error).message);
		} finally {
			saving.set(false);
		}
	}

	async function deleteRequirement(sectionIndex: number, reqIndex: number) {
		const section = get(sections)[sectionIndex];
		const req = section?.requirements[reqIndex];
		if (!req) return;
		try {
			saving.set(true);
			await apiDelete('requirement-nodes', req.node.id);
			sections.update((s) => {
				const copy = [...s];
				copy[sectionIndex] = {
					...copy[sectionIndex],
					requirements: copy[sectionIndex].requirements.filter((_, i) => i !== reqIndex)
				};
				return copy;
			});
		} catch (e) {
			setError(`delete-req-${req.node.id}`, (e as Error).message);
		} finally {
			saving.set(false);
		}
	}

	async function updateNode(nodeId: string, patch: Record<string, unknown>) {
		// Optimistic local update
		sections.update((s) =>
			s.map((sec) => ({
				...sec,
				node: sec.node.id === nodeId ? { ...sec.node, ...patch } : sec.node,
				requirements: sec.requirements.map((req) => ({
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

	async function addQuestion(
		sectionIndex: number,
		reqIndex: number,
		type: Question['type'] = 'text'
	) {
		const section = get(sections)[sectionIndex];
		const req = section?.requirements[reqIndex];
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
				requirement_node: req.node.id,
				folder: folderId
			});
			created.choices = created.choices ?? [];
			sections.update((s) => {
				const copy = [...s];
				const reqCopy = { ...copy[sectionIndex].requirements[reqIndex] };
				reqCopy.questions = [...reqCopy.questions, { question: created }];
				copy[sectionIndex] = {
					...copy[sectionIndex],
					requirements: copy[sectionIndex].requirements.map((r, i) =>
						i === reqIndex ? reqCopy : r
					)
				};
				return copy;
			});
		} catch (e) {
			setError('add-question', (e as Error).message);
		} finally {
			saving.set(false);
		}
	}

	async function updateQuestion(questionId: string, patch: Record<string, unknown>) {
		// Optimistic local update
		sections.update((s) =>
			s.map((sec) => ({
				...sec,
				requirements: sec.requirements.map((req) => ({
					...req,
					questions: req.questions.map((q) => ({
						...q,
						question: q.question.id === questionId ? { ...q.question, ...patch } : q.question
					}))
				}))
			}))
		);
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

	async function deleteQuestion(sectionIndex: number, reqIndex: number, qIndex: number) {
		const section = get(sections)[sectionIndex];
		const q = section?.requirements[reqIndex]?.questions[qIndex];
		if (!q) return;
		try {
			saving.set(true);
			await apiDelete('questions', q.question.id);
			sections.update((s) => {
				const copy = [...s];
				const reqCopy = { ...copy[sectionIndex].requirements[reqIndex] };
				reqCopy.questions = reqCopy.questions.filter((_, i) => i !== qIndex);
				copy[sectionIndex] = {
					...copy[sectionIndex],
					requirements: copy[sectionIndex].requirements.map((r, i) =>
						i === reqIndex ? reqCopy : r
					)
				};
				return copy;
			});
		} catch (e) {
			setError(`delete-question-${q.question.id}`, (e as Error).message);
		} finally {
			saving.set(false);
		}
	}

	async function addChoice(sectionIndex: number, reqIndex: number, qIndex: number) {
		const section = get(sections)[sectionIndex];
		const q = section?.requirements[reqIndex]?.questions[qIndex];
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
			sections.update((s) => {
				const copy = [...s];
				const reqCopy = { ...copy[sectionIndex].requirements[reqIndex] };
				const qCopy = { ...reqCopy.questions[qIndex] };
				qCopy.question = {
					...qCopy.question,
					choices: [...qCopy.question.choices, created]
				};
				reqCopy.questions = reqCopy.questions.map((qq, i) => (i === qIndex ? qCopy : qq));
				copy[sectionIndex] = {
					...copy[sectionIndex],
					requirements: copy[sectionIndex].requirements.map((r, i) =>
						i === reqIndex ? reqCopy : r
					)
				};
				return copy;
			});
		} catch (e) {
			setError('add-choice', (e as Error).message);
		} finally {
			saving.set(false);
		}
	}

	async function updateChoice(choiceId: string, patch: Record<string, unknown>) {
		// Optimistic local update
		sections.update((s) =>
			s.map((sec) => ({
				...sec,
				requirements: sec.requirements.map((req) => ({
					...req,
					questions: req.questions.map((q) => ({
						...q,
						question: {
							...q.question,
							choices: q.question.choices.map((c) => (c.id === choiceId ? { ...c, ...patch } : c))
						}
					}))
				}))
			}))
		);
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

	async function deleteChoice(
		sectionIndex: number,
		reqIndex: number,
		qIndex: number,
		choiceIndex: number
	) {
		const section = get(sections)[sectionIndex];
		const choice =
			section?.requirements[reqIndex]?.questions[qIndex]?.question.choices[choiceIndex];
		if (!choice) return;
		try {
			saving.set(true);
			await apiDelete('question-choices', choice.id);
			sections.update((s) => {
				const copy = [...s];
				const reqCopy = { ...copy[sectionIndex].requirements[reqIndex] };
				const qCopy = { ...reqCopy.questions[qIndex] };
				qCopy.question = {
					...qCopy.question,
					choices: qCopy.question.choices.filter((_, i) => i !== choiceIndex)
				};
				reqCopy.questions = reqCopy.questions.map((qq, i) => (i === qIndex ? qCopy : qq));
				copy[sectionIndex] = {
					...copy[sectionIndex],
					requirements: copy[sectionIndex].requirements.map((r, i) =>
						i === reqIndex ? reqCopy : r
					)
				};
				return copy;
			});
		} catch (e) {
			setError(`delete-choice-${choice.id}`, (e as Error).message);
		} finally {
			saving.set(false);
		}
	}

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
				current.map((s, i) => apiUpdate('requirement-nodes', s.node.id, { order_id: i * 100 }))
			);
		} catch (e) {
			setError('reorder-sections', (e as Error).message);
		} finally {
			saving.set(false);
		}
	}

	async function reorderRequirements(sectionIndex: number, fromIndex: number, toIndex: number) {
		if (fromIndex === toIndex) return;
		sections.update((s) => {
			const copy = [...s];
			const reqs = [...copy[sectionIndex].requirements];
			const [moved] = reqs.splice(fromIndex, 1);
			reqs.splice(toIndex, 0, moved);
			copy[sectionIndex] = { ...copy[sectionIndex], requirements: reqs };
			return copy;
		});
		try {
			saving.set(true);
			const reqs = get(sections)[sectionIndex].requirements;
			await Promise.all(
				reqs.map((r, i) => apiUpdate('requirement-nodes', r.node.id, { order_id: i * 100 }))
			);
		} catch (e) {
			setError('reorder-requirements', (e as Error).message);
		} finally {
			saving.set(false);
		}
	}

	async function reorderQuestions(
		sectionIndex: number,
		reqIndex: number,
		fromIndex: number,
		toIndex: number
	) {
		if (fromIndex === toIndex) return;
		sections.update((s) => {
			const copy = [...s];
			const req = { ...copy[sectionIndex].requirements[reqIndex] };
			const qs = [...req.questions];
			const [moved] = qs.splice(fromIndex, 1);
			qs.splice(toIndex, 0, moved);
			req.questions = qs;
			copy[sectionIndex] = {
				...copy[sectionIndex],
				requirements: copy[sectionIndex].requirements.map((r, i) => (i === reqIndex ? req : r))
			};
			return copy;
		});
		try {
			saving.set(true);
			const qs = get(sections)[sectionIndex].requirements[reqIndex].questions;
			await Promise.all(
				qs.map((q, i) => apiUpdate('questions', q.question.id, { order: i * 100 }))
			);
		} catch (e) {
			setError('reorder-questions', (e as Error).message);
		} finally {
			saving.set(false);
		}
	}

	async function reorderChoices(
		sectionIndex: number,
		reqIndex: number,
		qIndex: number,
		fromIndex: number,
		toIndex: number
	) {
		if (fromIndex === toIndex) return;
		sections.update((s) => {
			const copy = [...s];
			const req = { ...copy[sectionIndex].requirements[reqIndex] };
			const qItem = { ...req.questions[qIndex] };
			const choices = [...qItem.question.choices];
			const [moved] = choices.splice(fromIndex, 1);
			choices.splice(toIndex, 0, moved);
			qItem.question = { ...qItem.question, choices };
			req.questions = req.questions.map((q, i) => (i === qIndex ? qItem : q));
			copy[sectionIndex] = {
				...copy[sectionIndex],
				requirements: copy[sectionIndex].requirements.map((r, i) => (i === reqIndex ? req : r))
			};
			return copy;
		});
		try {
			saving.set(true);
			const choices =
				get(sections)[sectionIndex].requirements[reqIndex].questions[qIndex].question.choices;
			await Promise.all(
				choices.map((c, i) => apiUpdate('question-choices', c.id, { order: i * 100 }))
			);
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
