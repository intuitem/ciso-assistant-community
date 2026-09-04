import typescriptEslint from '@typescript-eslint/eslint-plugin';
import intuitemSveltekit from './plugins/eslint/eslint-plugin-intuitem-sveltekit/index.js';
import globals from 'globals';
import tsParser from '@typescript-eslint/parser';
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
	...svelte.configs.recommended,
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
		// svelte-eslint-parser is assigned to these files by svelte.configs.recommended;
		// it delegates <script lang="ts"> and runes modules to the TS parser.
		files: ['**/*.svelte', '**/*.svelte.js', '**/*.svelte.ts'],

		languageOptions: {
			parserOptions: {
				parser: tsParser
			}
		}
	}
];
