import { RuleTester } from 'eslint';
import * as secureRedirectRule from './secure-redirect.js';

const ruleTester = new RuleTester({});

ruleTester.run('open-redirect-detection', secureRedirectRule, {
	valid: [
		{
			code: 'redirect(301, "/internal/path")',
			filename: 'test.js'
		},
		{
			code: 'redirect(308, "https://example.com")',
			filename: 'test.js'
		},
		{
			code: 'redirect(302, getSecureRedirect(userProvidedUrl))',
			filename: 'test.js'
		},
		{
			code: 'redirect(303, getSecureRedirect(`/user/${userId}`))',
			filename: 'test.js'
		}
	],
	invalid: [
		{
			code: "redirect(200, '/internal/path')",
			errors: [
				{
					message: 'Invalid status code for redirect. Must be between 300 and 308.'
				}
			],
			filename: 'test.js'
		},
		{
			code: 'redirect(302, userProvidedUrl)',
			errors: [
				{
					message:
						'Potential open redirect vulnerability. Use getSecureRedirect() for dynamic URLs.'
				}
			],
			output: 'redirect(302, getSecureRedirect(userProvidedUrl))',
			filename: 'test.js'
		},
		{
			code: 'redirect(307, `/user/${userId}`)',
			errors: [
				{
					message:
						'Potential open redirect vulnerability in template literal. Use getSecureRedirect().'
				}
			],
			output: 'redirect(307, getSecureRedirect(`/user/${userId}`))',
			filename: 'test.js'
		},
		{
			code: 'redirect(302, someFunction())',
			errors: [
				{
					message:
						'Potential open redirect vulnerability. Use getSecureRedirect() for dynamic URLs.'
				}
			],
			output: 'redirect(302, getSecureRedirect(someFunction()))',
			filename: 'test.js'
		},
		{
			code: 'redirect(305, URL.createObjectURL(blob))',
			errors: [
				{
					message:
						'Potential open redirect vulnerability. Use getSecureRedirect() for dynamic URLs.'
				}
			],
			output: 'redirect(305, getSecureRedirect(URL.createObjectURL(blob)))',
			filename: 'test.js'
		}
	]
});

console.log('All tests passed!');
