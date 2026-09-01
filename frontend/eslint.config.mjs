import typescriptEslint from '@typescript-eslint/eslint-plugin';
import intuitemSveltekit from './plugins/eslint/eslint-plugin-intuitem-sveltekit/index.js';
import globals from 'globals';
import tsParser from '@typescript-eslint/parser';
import parser from 'svelte-eslint-parser';
import svelte from 'eslint-plugin-svelte';
import prettier from 'eslint-config-prettier';
import js from '@eslint/js';

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
			'**/yarn.lock'
		]
	},
	js.configs.recommended,
	...typescriptEslint.configs['flat/recommended'],
	...svelte.configs['flat/recommended'],
	prettier,
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
			'eslint-plugin-intuitem-sveltekit/secure-redirect': 'error'
		}
	},
	{
		files: ['**/*.svelte'],

		languageOptions: {
			parser: parser,
			ecmaVersion: 5,
			sourceType: 'script',

			parserOptions: {
				parser: '@typescript-eslint/parser'
			}
		}
	}
];
