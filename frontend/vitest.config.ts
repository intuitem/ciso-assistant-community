import { configDefaults, coverageConfigDefaults, defineConfig } from 'vitest/config';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { svelteTesting } from '@testing-library/svelte/vite';
import path from 'path';

// Only tests that render a component need Svelte's browser build; the rest
// keep the default resolution they have always run with.
const COMPONENT_TESTS = 'src/**/*.svelte.test.ts';

export default defineConfig({
	plugins: [svelte({ hot: !process.env.VITEST })],
	test: {
		globals: true,
		environment: 'jsdom',
		setupFiles: ['./vitest-setup.ts'],
		exclude: [...configDefaults.exclude, '**/tests/**'],
		coverage: {
			// Generated translation bundles are not application coverage targets.
			exclude: [...coverageConfigDefaults.exclude, 'src/paraglide/**']
		},
		projects: [
			{
				extends: true,
				test: {
					name: 'unit',
					exclude: [...configDefaults.exclude, '**/tests/**', COMPONENT_TESTS]
				}
			},
			{
				extends: true,
				plugins: [svelteTesting()],
				test: { name: 'component', include: [COMPONENT_TESTS] }
			}
		]
	},
	resolve: {
		alias: {
			// before '$app/env': string aliases also match as path prefixes
			'$app/env/public': path.resolve(__dirname, 'vitest-mocks/app-env-public.ts'),
			'$app/env': path.resolve(__dirname, 'vitest-mocks/app-env.ts'),
			'$app/navigation': path.resolve(__dirname, 'vitest-mocks/app-navigation.ts'),
			'$app/paths': path.resolve(__dirname, 'vitest-mocks/app-paths.ts'),
			'$app/forms': path.resolve(__dirname, 'vitest-mocks/app-forms.ts'),
			'$app/state': path.resolve(__dirname, 'vitest-mocks/app-state.ts')
		}
	}
});
