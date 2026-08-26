import { RuleTester } from 'eslint';
import * as secureRedirectRule from './secure-redirect.js';

const ruleTester = new RuleTester({});

const DYNAMIC = 'Potential open redirect vulnerability. Use getSecureRedirect() for dynamic URLs.';
const TEMPLATE =
	'Potential open redirect vulnerability in template literal. Use getSecureRedirect().';

ruleTester.run('open-redirect-detection', secureRedirectRule, {
	valid: [
		{ code: 'redirect(301, "/internal/path")', filename: 'test.js' },
		{ code: 'redirect(308, "https://example.com")', filename: 'test.js' },
		{ code: 'redirect(302, getSecureRedirect(userProvidedUrl))', filename: 'test.js' },
		{ code: 'redirect(303, getSecureRedirect(`/user/${userId}`))', filename: 'test.js' },

		// A literal prefix of "/" + word char pins the result to this origin.
		{ code: 'redirect(307, `/user/${userId}`)', filename: 'test.js' },
		{ code: 'redirect(302, `/calendar/${year}/${month}`)', filename: 'test.js' },
		{ code: 'redirect(302, `/login?next=${pathname}`)', filename: 'test.js' },

		// getSecureRedirect() reached through a variable, not just inline.
		{
			code: 'const next = getSecureRedirect(raw); redirect(302, next);',
			filename: 'test.js'
		},
		// ...and combined with a fallback.
		{
			code: 'const next = getSecureRedirect(raw) || "/"; redirect(302, next);',
			filename: 'test.js'
		},
		{
			code: 'redirect(302, getSecureRedirect(raw) ?? `/users/${id}`);',
			filename: 'test.js'
		},
		{
			code: 'redirect(302, isAuditee ? "/auditee-dashboard" : "/analytics");',
			filename: 'test.js'
		}
	],
	invalid: [
		{
			code: "redirect(200, '/internal/path')",
			errors: [{ message: 'Invalid status code for redirect. Must be between 300 and 308.' }],
			filename: 'test.js'
		},
		{
			code: 'redirect(302, userProvidedUrl)',
			errors: [{ message: DYNAMIC }],
			output: 'redirect(302, getSecureRedirect(userProvidedUrl))',
			filename: 'test.js'
		},
		{
			code: 'redirect(302, someFunction())',
			errors: [{ message: DYNAMIC }],
			output: 'redirect(302, getSecureRedirect(someFunction()))',
			filename: 'test.js'
		},
		{
			code: 'redirect(305, URL.createObjectURL(blob))',
			errors: [{ message: DYNAMIC }],
			output: 'redirect(305, getSecureRedirect(URL.createObjectURL(blob)))',
			filename: 'test.js'
		},

		// `/${x}` can resolve to `//evil.com` -- a protocol-relative open redirect.
		{
			code: 'redirect(302, `/${target}`)',
			errors: [{ message: TEMPLATE }],
			output: 'redirect(302, getSecureRedirect(`/${target}`))',
			filename: 'test.js'
		},
		{
			code: 'redirect(302, `//${target}`)',
			errors: [{ message: TEMPLATE }],
			output: 'redirect(302, getSecureRedirect(`//${target}`))',
			filename: 'test.js'
		},
		// Interpolation before any literal prefix controls the whole URL.
		{
			code: 'redirect(302, `${base}/path`)',
			errors: [{ message: TEMPLATE }],
			output: 'redirect(302, getSecureRedirect(`${base}/path`))',
			filename: 'test.js'
		},
		// A reassigned variable cannot be trusted even if it starts out sanitized.
		{
			code: 'let next = getSecureRedirect(raw); next = raw; redirect(302, next);',
			errors: [{ message: DYNAMIC }],
			output:
				'let next = getSecureRedirect(raw); next = raw; redirect(302, getSecureRedirect(next));',
			filename: 'test.js'
		},
		// One safe branch is not enough.
		{
			code: 'redirect(302, cond ? "/analytics" : userProvidedUrl);',
			errors: [{ message: DYNAMIC }],
			output: 'redirect(302, getSecureRedirect(cond ? "/analytics" : userProvidedUrl));',
			filename: 'test.js'
		}
	]
});

console.log('All tests passed!');
