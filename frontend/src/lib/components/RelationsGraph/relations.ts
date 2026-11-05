/** Models that offer a relations graph. The relations live in backend/core/neighborhood.py. */
const CURATED = new Set(['applied-controls', 'risk-scenarios', 'assets', 'document-containers']);

export function hasRelationGraph(urlModel: string | undefined): boolean {
	return Boolean(urlModel && CURATED.has(urlModel));
}
