import type { PageLoad } from './$types';
import * as m from '$paraglide/messages';

export const load: PageLoad = async () => {
	return { title: m.myProfile() };
};
