import { page } from '$app/state';
import { hasPermissionAnywhere } from './access-control';
import { NON_CREATABLE_URL_MODELS } from './crud';

export const CREATE_INTENT_PARAM = 'create';

/** Fresh value each time: re-running the command on the page it targets must still navigate. */
export function createIntentHref(listHref: string): string {
	return `${listHref}?${CREATE_INTENT_PARAM}=${Date.now().toString(36)}`;
}

interface CreateIntent {
	urlModel: string;
	/** Django model name, e.g. `riskassessment` — the permission codename suffix. */
	modelName: string;
	open: () => void;
}

/** Call from an `$effect`, not `onMount`: a query-string change does not remount the page. */
export function consumeCreateIntent({ urlModel, modelName, open }: CreateIntent): void {
	if (!page.url.searchParams.has(CREATE_INTENT_PARAM)) return;
	// The outgoing page sees the incoming URL before teardown; only the addressee may act.
	if (page.url.pathname !== `/${urlModel}`) return;

	// Raw replaceState, as ModelTable does for filters. `page.url` keeps the stale param,
	// which is harmless — the next command carries a new one.
	const cleaned = new URL(page.url);
	cleaned.searchParams.delete(CREATE_INTENT_PARAM);
	history.replaceState(history.state, '', cleaned.pathname + cleaned.search);

	// Same gates as the add button, so a hand-typed URL cannot bypass them.
	if (NON_CREATABLE_URL_MODELS.includes(urlModel)) return;
	if (!hasPermissionAnywhere(page.data.user, `add_${modelName}`)) return;
	open();
}
