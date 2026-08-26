import js from '@eslint/js';
import typescriptEslint from '@typescript-eslint/eslint-plugin';
import tsParser from '@typescript-eslint/parser';
import svelte from 'eslint-plugin-svelte';
import svelteParser from 'svelte-eslint-parser';
import prettier from 'eslint-config-prettier';
import globals from 'globals';
import intuitemSveltekit from './plugins/eslint/eslint-plugin-intuitem-sveltekit/index.js';

export default [
	{
		ignores: [
			'**/.DS_Store',
			'**/node_modules',
			'build',
			'.svelte-kit',
			'package',
			'**/.env',
			'**/.env.*',
			'!**/.env.example',
			'tests/reports/*',
			'tests/results/*',
			'**/pnpm-lock.yaml',
			'**/package-lock.json',
			'**/yarn.lock',
			// paraglide output is generated; it self-ignores via an emitted
			// .gitignore, which ESLint does not read.
			'**/paraglide'
		]
	},
	js.configs.recommended,
	...typescriptEslint.configs['flat/recommended'],
	...svelte.configs['flat/recommended'],
	prettier,
	...svelte.configs['flat/prettier'],
	{
		plugins: {
			'eslint-plugin-intuitem-sveltekit': intuitemSveltekit
		},

		languageOptions: {
			globals: {
				...globals.browser,
				...globals.node
			},

			parser: tsParser,
			ecmaVersion: 2020,
			sourceType: 'module',

			parserOptions: {
				extraFileExtensions: ['.svelte']
			}
		},

		rules: {
			'eslint-plugin-intuitem-sveltekit/secure-redirect': 'error',
			'@typescript-eslint/no-unused-expressions': [
				'error',
				{ allowShortCircuit: true, allowTernary: true }
			],
			'@typescript-eslint/ban-ts-comment': [
				'error',
				{ 'ts-ignore': 'allow-with-description', minimumDescriptionLength: 10 }
			]
		}
	},
	{
		files: ['**/*.svelte'],

		languageOptions: {
			parser: svelteParser,

			parserOptions: {
				parser: tsParser
			}
		},

		rules: {
			// TypeScript resolves identifiers in .svelte files; typescript-eslint's
			// eslint-recommended override only turns this off for **/*.ts.
			'no-undef': 'off',
			// `prop = $bindable()` in a $props() destructuring reads as a dead
			// assignment to this rule; Svelte's binding machinery uses the value.
			'no-useless-assignment': 'off'
		}
	},
	{
		files: ['tests/**'],

		rules: {
			// Playwright requires fixture functions to destructure their first
			// argument; `async ({}, use)` is mandatory, not an oversight.
			'no-empty-pattern': 'off',
			// Test helpers use namespaces purely to group related page objects.
			'@typescript-eslint/no-namespace': 'off'
		}
	},
	{
		// Pre-existing backlog, surfaced when the config was repaired for ESLint 10.
		// Kept visible as warnings so `lint` stays an enforceable gate; promote each
		// back to 'error' as it is burned down.
		rules: {
			'@typescript-eslint/no-explicit-any': 'warn',
			'@typescript-eslint/no-unused-vars': 'warn',
			'svelte/require-each-key': 'warn',
			'svelte/no-navigation-without-resolve': 'warn',
			'svelte/prefer-svelte-reactivity': 'warn'
		}
	}
];
