// Shared node/edge visual constants for the builder canvas and the read-only
// library graph preview. The two build their flow nodes from different data
// shapes (live domain vs export shape), so their mappers stay separate — but
// the edge styling and node-type labels are identical and live here.
import { MarkerType } from '@xyflow/svelte';
import { m } from '$paraglide/messages';

export const EDGE_STYLE = 'stroke: var(--color-surface-500); stroke-width: 2;';
export const EDGE_MARKER = { type: MarkerType.ArrowClosed, color: 'var(--color-surface-600)' };

export const NODE_TYPE_LABELS: Record<string, () => string> = {
	trigger: m.workflowNodeTrigger,
	end: m.workflowNodeEnd,
	task: m.workflowNodeTask,
	condition: m.workflowNodeCondition,
	loop: m.workflowNodeLoop,
	action: m.workflowNodeAction,
	subprocess: m.workflowNodeSubprocess,
	event: m.workflowNodeEvent
};
