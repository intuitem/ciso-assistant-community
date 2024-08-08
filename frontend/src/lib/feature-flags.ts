import { env } from '$env/dynamic/private';

export interface FeatureFlags {
	enterprise: boolean;
}

export function loadFeatureFlags(): FeatureFlags {
	return {
		enterprise: env.FF_ENTERPRISE === 'true'
	};
}
