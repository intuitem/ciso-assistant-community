import { BASE_API_URL } from '$lib/utils/constants';
import { match as isUuid } from '../../../../../params/uuid';
import type { PageServerLoad } from './$types';
import type { DomainTreeFeed } from './feed';

export const load: PageServerLoad = async ({ fetch, url }) => {
	const frameworkId = url.searchParams.get('framework');
	const campaignId = url.searchParams.get('campaign');

	if (!frameworkId) return { frameworkId: null, campaignId, feed: null, error: null };
	if (!isUuid(frameworkId) || (campaignId && !isUuid(campaignId)))
		return { frameworkId, campaignId, feed: null, error: 'Invalid framework or campaign.' };

	const query = campaignId ? `?campaign=${campaignId}` : '';
	const res = await fetch(`${BASE_API_URL}/frameworks/${frameworkId}/domain_tree/${query}`);
	if (!res.ok)
		return {
			frameworkId,
			campaignId,
			feed: null,
			error: `The domain tree could not be loaded (${res.status}).`
		};
	return { frameworkId, campaignId, feed: (await res.json()) as DomainTreeFeed, error: null };
};
