import type { User } from '$lib/utils/types';

/** Where a third-party user is sent when they ask for a page they may not open. */
export const THIRD_PARTY_HOME = '/auditee-dashboard';

/**
 * The app pages a third-party user may open, as route ids without their groups, so that
 * moving a page between folders does not change who may open it. Every other page under
 * `(app)` is refused: a new page stays internal until it is listed here. The backend still
 * decides what each page shows.
 */
export const THIRD_PARTY_PAGES: ReadonlySet<string> = new Set([
	'/',
	'/setup-mfa',
	'/auditee-dashboard',
	'/auditee-assessments/[id=uuid]',
	'/compliance-assessments/[id=uuid]',
	'/compliance-assessments/[id=uuid]/assignments',
	'/compliance-assessments/[id=uuid]/table-mode',
	'/evidences/[id=uuid]',
	'/evidence-revisions/[id=uuid]',
	'/requirement-assessments/[id=uuid]',
	'/requirement-assessments/[id=uuid]/edit',
	'/my-profile',
	'/my-profile/change-password',
	'/my-profile/settings',
	'/[model=thirdparty_urlmodels]',
	'/[model=thirdparty_urlmodels]/[id=uuid]',
	'/[model=thirdparty_urlmodels]/[id=uuid]/edit'
]);

/** `/(app)/evidences/[id=uuid]` → `/evidences/[id=uuid]` */
export function withoutGroups(routeId: string): string {
	return routeId.replace(/\/\([^)/]+\)/g, '') || '/';
}

/** Whether a third-party user may open the page at `routeId`. Only the app is restricted. */
export function thirdPartyMayOpen(routeId: string): boolean {
	if (routeId !== '/(app)' && !routeId.startsWith('/(app)/')) return true;
	return THIRD_PARTY_PAGES.has(withoutGroups(routeId));
}

type Viewer = Pick<User, 'is_third_party'> | null | undefined;

/** Whether `user` may open the page at `routeId`: a link to a page they may not open shows as text. */
export function canOpenPage(user: Viewer, routeId: string): boolean {
	return !user?.is_third_party || thirdPartyMayOpen(routeId);
}

/**
 * Whether `user` may open `/<urlModel>/<id>`. Only a model with its own detail route can be
 * listed for third parties; the generic `[model=internal_urlmodels]` one never is.
 */
export function canOpenObjectPage(user: Viewer, urlModel: string): boolean {
	return canOpenPage(user, `/(app)/${urlModel}/[id=uuid]`);
}
