import { getCSRFToken } from './django.js';
import { BACKEND_API_EXPOSED_URL } from '$lib/utils/constants';

const BASE_URL = `${BACKEND_API_EXPOSED_URL}`;

export const AuthProcess = Object.freeze({
	LOGIN: 'login',
	CONNECT: 'connect'
});

export const URLs = Object.freeze({
	REDIRECT_TO_PROVIDER: BASE_URL + '/iam/sso/redirect/'
});

function postForm(action, data) {
	const f = document.createElement('form');
	f.method = 'POST';
	f.action = action;

	for (const key in data) {
		const d = document.createElement('input');
		d.type = 'hidden';
		d.name = key;
		d.value = data[key];
		f.appendChild(d);
	}
	document.body.appendChild(f);
	f.submit();
}

export function redirectToProvider(providerId, callbackURL, process = AuthProcess.LOGIN) {
	postForm(URLs.REDIRECT_TO_PROVIDER, {
		provider: providerId,
		process,
		callback_url: callbackURL,
		csrfmiddlewaretoken: getCSRFToken()
	});
}
