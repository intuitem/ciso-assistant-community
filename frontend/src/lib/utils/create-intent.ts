import { page } from '$app/state';
import { hasPermissionAnywhere } from './access-control';
import { NON_CREATABLE_URL_MODELS } from './crud';

/** Query parameter the command palette uses to ask a list page to open its create form. */
export const CREATE_INTENT_PARAM = 'create';

/** Palette-side: a fresh value each time, so re-running the command on the page it already
 * targets is a real navigation rather than a no-op. */
export function createIntentHref(listHref: string): string {
	return `${listHref}?${CREATE_INTENT_PARAM}=${Date.now().toString(36)}`;
}

interface CreateIntent {
	urlModel: string;
	/** Django model name, e.g. `riskassessment` — the permission codename suffix. */
	modelName: string;
	/** Opens the create form the page already owns. */
	open: () => void;
}

/**
 * The command palette creates by navigating to a list page with `?create`, so the form stays
 * owned by the page that has its schema, options and post-create refresh. Call from an
 * `$effect` — the page is not remounted when only the query string changes. The gates here
 * mirror the add button's, so a hand-typed URL cannot bypass them.
 */
export function consumeCreateIntent({ urlModel, modelName, open }: CreateIntent): void {
	if (!page.url.searchParams.has(CREATE_INTENT_PARAM)) return;
	// The outgoing page sees the incoming URL before it is torn down, so a list page navigating
	// to another list page would open its own form on top of the right one. Only the page the
	// intent is addressed to may act on it.
	if (page.url.pathname !== `/${urlModel}`) return;

	// Clean the address bar without a router navigation, as ModelTable does for its filters.
	// `page.url` keeps the parameter, which is harmless: the next command carries a new value
	// and so is a fresh navigation.
	const cleaned = new URL(page.url);
	cleaned.searchParams.delete(CREATE_INTENT_PARAM);
	history.replaceState(history.state, '', cleaned.pathname + cleaned.search);

	if (NON_CREATABLE_URL_MODELS.includes(urlModel)) return;
	if (!hasPermissionAnywhere(page.data.user, `add_${modelName}`)) return;
	open();
}
