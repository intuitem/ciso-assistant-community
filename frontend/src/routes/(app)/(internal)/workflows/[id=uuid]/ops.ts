// The workflow editor talks to the backend through a single frontend
// passthrough endpoint (/workflows/<id>/ops). One place owns that URL shape and
// the JSON POST envelope so the panels and canvas can't drift.

export function buildOpsUrl(workflowId: string, action: string): string {
	return `/workflows/${workflowId}/ops?action=${action}`;
}

export function postOps(
	workflowId: string,
	action: string,
	body: Record<string, unknown> = {}
): Promise<Response> {
	return fetch(buildOpsUrl(workflowId, action), {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});
}
