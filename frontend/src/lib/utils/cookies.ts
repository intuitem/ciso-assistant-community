function getCookieDict(): { [key: string]: string } {
	let cookies = {};
	document.cookie.split(';').forEach((cookie_string) => {
		cookie_string = cookie_string.trim(); // Remove possible whitespaces
		const cookie_key = cookie_string.split('=')[0];
		const cookie_value = cookie_string.substring(cookie_key.length + 1);
		cookies[cookie_key] = cookie_value;
	});
	return cookies;
}

function getCookie(cookie_name: string): string | undefined {
	const cookie_dict = getCookieDict();
	for (const [_cookie_name, _cookie_value] of Object.entries(cookie_dict)) {
		if (_cookie_name === cookie_name) {
			return _cookie_value;
		}
	}
}

function setCookie(
	cookie_name: string,
	cookie_value: string,
	secure: boolean = true,
	samesite_lax: boolean = true,
	path: string = '/'
) {
	let cookie_info = [`${cookie_name}=${cookie_value}`];
	if (secure) cookie_info.push('Secure');
	if (samesite_lax) cookie_info.push('SameSite=Lax');
	cookie_info.push(`path=${path}`);

	document.cookie = cookie_info.join('; ');
}

function deleteCookie(cookie_name: string) {
	document.cookie = cookie_name + '=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
}

export { setCookie, getCookie, deleteCookie };
