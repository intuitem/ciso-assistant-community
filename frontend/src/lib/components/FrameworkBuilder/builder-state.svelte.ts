import { getContext, setContext } from 'svelte';
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

export class BuilderState {
	framework = $state<Framework>({} as Framework);
	sections = $state<BuilderSection[]>([]);
	saving = $state(false);
	errors = $state<Map<string, string>>(new Map());
	activeSection = $state<string>('');

	private folderId = '';
	private frameworkId = '';

	constructor(framework: Framework, nodes: RequirementNode[], questions: Question[]) {
		this.framework = framework;
		this.frameworkId = framework.id;
		this.folderId = typeof framework.folder === 'string' ? framework.folder : framework.folder.id;
		this.sections = this.buildTree(nodes, questions);
		if (this.sections.length > 0) {
			this.activeSection = this.sections[0].node.id;
		}
	}

	private buildTree(nodes: RequirementNode[], questions: Question[]): BuilderSection[] {
		// Group questions by requirement_node id
		const questionsByNode = new Map<string, Question[]>();
		for (const q of questions) {
			const nodeId =
				typeof q.requirement_node === 'string' ? q.requirement_node : q.requirement_node;
			if (!questionsByNode.has(nodeId)) {
				questionsByNode.set(nodeId, []);
			}
			questionsByNode.get(nodeId)!.push(q);
		}

		// Separate sections (non-assessable top-level) and requirements (assessable)
		const sections: RequirementNode[] = [];
		const requirementsByParent = new Map<string, RequirementNode[]>();

		for (const node of nodes) {
			if (!node.assessable && !node.parent_urn) {
				sections.push(node);
			} else if (node.parent_urn) {
				if (!requirementsByParent.has(node.parent_urn)) {
					requirementsByParent.set(node.parent_urn, []);
				}
				requirementsByParent.get(node.parent_urn)!.push(node);
			} else if (node.assessable && !node.parent_urn) {
				// Top-level assessable nodes — treat as their own section
				sections.push(node);
			}
		}

		// Sort sections by order_id
		sections.sort((a, b) => (a.order_id ?? 0) - (b.order_id ?? 0));

		return sections.map((sectionNode) => {
			const childNodes = (requirementsByParent.get(sectionNode.urn ?? '') ?? []).sort(
				(a, b) => (a.order_id ?? 0) - (b.order_id ?? 0)
			);

			const requirements: BuilderRequirement[] = childNodes.map((reqNode) => ({
				node: reqNode,
				questions: (questionsByNode.get(reqNode.id) ?? [])
					.sort((a, b) => a.order - b.order)
					.map((q) => ({ question: q }))
			}));

			// If the section itself is assessable (top-level assessable), show it as having questions directly
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

			return {
				node: sectionNode,
				requirements,
				collapsed: false
			};
		});
	}

	// --- Error helpers ---

	setError(key: string, message: string) {
		this.errors = new Map(this.errors).set(key, message);
		setTimeout(() => this.clearError(key), 5000);
	}

	clearError(key: string) {
		const next = new Map(this.errors);
		next.delete(key);
		this.errors = next;
	}

	// --- Section CRUD ---

	async addSection(afterIndex?: number) {
		const order =
			afterIndex !== undefined ? (afterIndex + 1) * 100 + 50 : this.sections.length * 100;
		const payload: Record<string, unknown> = {
			name: 'New Section',
			assessable: false,
			order_id: order,
			framework: this.frameworkId,
			folder: this.folderId
		};

		try {
			this.saving = true;
			const created = await apiCreate('requirement-nodes', payload);
			const newSection: BuilderSection = {
				node: created,
				requirements: [],
				collapsed: false
			};
			const idx = afterIndex !== undefined ? afterIndex + 1 : this.sections.length;
			this.sections = [...this.sections.slice(0, idx), newSection, ...this.sections.slice(idx)];
		} catch (e) {
			this.setError('add-section', (e as Error).message);
		} finally {
			this.saving = false;
		}
	}

	async deleteSection(sectionIndex: number) {
		const section = this.sections[sectionIndex];
		if (!section) return;

		try {
			this.saving = true;
			await apiDelete('requirement-nodes', section.node.id);
			this.sections = this.sections.filter((_, i) => i !== sectionIndex);
		} catch (e) {
			this.setError(`delete-section-${section.node.id}`, (e as Error).message);
		} finally {
			this.saving = false;
		}
	}

	// --- Requirement CRUD ---

	async addRequirement(sectionIndex: number, afterIndex?: number) {
		const section = this.sections[sectionIndex];
		if (!section) return;

		const reqs = section.requirements;
		const order = afterIndex !== undefined ? (afterIndex + 1) * 100 + 50 : reqs.length * 100;

		const payload: Record<string, unknown> = {
			name: 'New Requirement',
			assessable: true,
			order_id: order,
			parent_urn: section.node.urn,
			framework: this.frameworkId,
			folder: this.folderId
		};

		try {
			this.saving = true;
			const created = await apiCreate('requirement-nodes', payload);
			const newReq: BuilderRequirement = { node: created, questions: [] };
			const idx = afterIndex !== undefined ? afterIndex + 1 : reqs.length;
			section.requirements = [...reqs.slice(0, idx), newReq, ...reqs.slice(idx)];
		} catch (e) {
			this.setError('add-requirement', (e as Error).message);
		} finally {
			this.saving = false;
		}
	}

	async deleteRequirement(sectionIndex: number, reqIndex: number) {
		const section = this.sections[sectionIndex];
		const req = section?.requirements[reqIndex];
		if (!req) return;

		try {
			this.saving = true;
			await apiDelete('requirement-nodes', req.node.id);
			section.requirements = section.requirements.filter((_, i) => i !== reqIndex);
		} catch (e) {
			this.setError(`delete-req-${req.node.id}`, (e as Error).message);
		} finally {
			this.saving = false;
		}
	}

	// --- Node update (auto-save on blur) ---

	async updateNode(nodeId: string, patch: Record<string, unknown>) {
		try {
			this.saving = true;
			await apiUpdate('requirement-nodes', nodeId, patch);
			this.clearError(`node-${nodeId}`);
		} catch (e) {
			this.setError(`node-${nodeId}`, (e as Error).message);
			throw e;
		} finally {
			this.saving = false;
		}
	}

	// --- Question CRUD ---

	async addQuestion(sectionIndex: number, reqIndex: number, type: Question['type'] = 'text') {
		const section = this.sections[sectionIndex];
		const req = section?.requirements[reqIndex];
		if (!req) return;

		const order = req.questions.length * 100;
		const urn = `urn:intuitem:risk:question:${crypto.randomUUID()}`;

		const payload: Record<string, unknown> = {
			urn,
			text: '',
			type,
			order,
			weight: 1,
			requirement_node: req.node.id,
			folder: this.folderId
		};

		try {
			this.saving = true;
			const created = await apiCreate('questions', payload);
			created.choices = created.choices ?? [];
			req.questions = [...req.questions, { question: created }];
		} catch (e) {
			this.setError('add-question', (e as Error).message);
		} finally {
			this.saving = false;
		}
	}

	async updateQuestion(questionId: string, patch: Record<string, unknown>) {
		try {
			this.saving = true;
			await apiUpdate('questions', questionId, patch);
			this.clearError(`question-${questionId}`);
		} catch (e) {
			this.setError(`question-${questionId}`, (e as Error).message);
			throw e;
		} finally {
			this.saving = false;
		}
	}

	async deleteQuestion(sectionIndex: number, reqIndex: number, qIndex: number) {
		const section = this.sections[sectionIndex];
		const req = section?.requirements[reqIndex];
		const q = req?.questions[qIndex];
		if (!q) return;

		try {
			this.saving = true;
			await apiDelete('questions', q.question.id);
			req.questions = req.questions.filter((_, i) => i !== qIndex);
		} catch (e) {
			this.setError(`delete-question-${q.question.id}`, (e as Error).message);
		} finally {
			this.saving = false;
		}
	}

	// --- Choice CRUD ---

	async addChoice(sectionIndex: number, reqIndex: number, qIndex: number) {
		const q = this.sections[sectionIndex]?.requirements[reqIndex]?.questions[qIndex];
		if (!q) return;

		const order = q.question.choices.length * 100;
		const payload: Record<string, unknown> = {
			value: '',
			order,
			question: q.question.id,
			folder: this.folderId
		};

		try {
			this.saving = true;
			const created = await apiCreate('question-choices', payload);
			q.question.choices = [...q.question.choices, created];
		} catch (e) {
			this.setError('add-choice', (e as Error).message);
		} finally {
			this.saving = false;
		}
	}

	async updateChoice(choiceId: string, patch: Record<string, unknown>) {
		try {
			this.saving = true;
			await apiUpdate('question-choices', choiceId, patch);
			this.clearError(`choice-${choiceId}`);
		} catch (e) {
			this.setError(`choice-${choiceId}`, (e as Error).message);
			throw e;
		} finally {
			this.saving = false;
		}
	}

	async deleteChoice(sectionIndex: number, reqIndex: number, qIndex: number, choiceIndex: number) {
		const q = this.sections[sectionIndex]?.requirements[reqIndex]?.questions[qIndex];
		const choice = q?.question.choices[choiceIndex];
		if (!choice) return;

		try {
			this.saving = true;
			await apiDelete('question-choices', choice.id);
			q.question.choices = q.question.choices.filter((_, i) => i !== choiceIndex);
		} catch (e) {
			this.setError(`delete-choice-${choice.id}`, (e as Error).message);
		} finally {
			this.saving = false;
		}
	}

	// --- Reorder helpers ---

	async reorderSections(fromIndex: number, toIndex: number) {
		if (fromIndex === toIndex) return;
		const newSections = [...this.sections];
		const [moved] = newSections.splice(fromIndex, 1);
		newSections.splice(toIndex, 0, moved);
		this.sections = newSections;

		// Update order_id for all affected sections
		const updates = newSections.map((s, i) => ({
			id: s.node.id,
			order: i * 100
		}));

		try {
			this.saving = true;
			await Promise.all(
				updates.map((u) => apiUpdate('requirement-nodes', u.id, { order_id: u.order }))
			);
		} catch (e) {
			this.setError('reorder-sections', (e as Error).message);
		} finally {
			this.saving = false;
		}
	}

	async reorderRequirements(sectionIndex: number, fromIndex: number, toIndex: number) {
		if (fromIndex === toIndex) return;
		const section = this.sections[sectionIndex];
		if (!section) return;

		const newReqs = [...section.requirements];
		const [moved] = newReqs.splice(fromIndex, 1);
		newReqs.splice(toIndex, 0, moved);
		section.requirements = newReqs;

		try {
			this.saving = true;
			await Promise.all(
				newReqs.map((r, i) => apiUpdate('requirement-nodes', r.node.id, { order_id: i * 100 }))
			);
		} catch (e) {
			this.setError('reorder-requirements', (e as Error).message);
		} finally {
			this.saving = false;
		}
	}

	async reorderQuestions(
		sectionIndex: number,
		reqIndex: number,
		fromIndex: number,
		toIndex: number
	) {
		if (fromIndex === toIndex) return;
		const req = this.sections[sectionIndex]?.requirements[reqIndex];
		if (!req) return;

		const newQuestions = [...req.questions];
		const [moved] = newQuestions.splice(fromIndex, 1);
		newQuestions.splice(toIndex, 0, moved);
		req.questions = newQuestions;

		try {
			this.saving = true;
			await Promise.all(
				newQuestions.map((q, i) => apiUpdate('questions', q.question.id, { order: i * 100 }))
			);
		} catch (e) {
			this.setError('reorder-questions', (e as Error).message);
		} finally {
			this.saving = false;
		}
	}

	async reorderChoices(
		sectionIndex: number,
		reqIndex: number,
		qIndex: number,
		fromIndex: number,
		toIndex: number
	) {
		if (fromIndex === toIndex) return;
		const q = this.sections[sectionIndex]?.requirements[reqIndex]?.questions[qIndex];
		if (!q) return;

		const newChoices = [...q.question.choices];
		const [moved] = newChoices.splice(fromIndex, 1);
		newChoices.splice(toIndex, 0, moved);
		q.question.choices = newChoices;

		try {
			this.saving = true;
			await Promise.all(
				newChoices.map((c, i) => apiUpdate('question-choices', c.id, { order: i * 100 }))
			);
		} catch (e) {
			this.setError('reorder-choices', (e as Error).message);
		} finally {
			this.saving = false;
		}
	}

	// --- Framework metadata ---

	async updateFramework(patch: Record<string, unknown>) {
		try {
			this.saving = true;
			await apiUpdate('frameworks', this.frameworkId, patch);
			Object.assign(this.framework, patch);
			this.clearError('framework');
		} catch (e) {
			this.setError('framework', (e as Error).message);
			throw e;
		} finally {
			this.saving = false;
		}
	}
}

export function setBuilderContext(state: BuilderState) {
	setContext(CONTEXT_KEY, state);
}

export function getBuilderContext(): BuilderState {
	return getContext<BuilderState>(CONTEXT_KEY);
}
