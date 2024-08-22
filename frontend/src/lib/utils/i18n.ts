import * as m from '$paraglide/messages.js';

export function safeTranslate(key: string, params = {}, options = {}): string {
	if (Object.hasOwn(m, key)) {
		return m[key](params, options);
	}
	return key;
}
