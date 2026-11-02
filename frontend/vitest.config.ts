import { configDefaults, defineConfig } from 'vitest/config';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import path from 'path';

export default defineConfig({
	plugins: [svelte({ hot: !process.env.VITEST })],
	test: {
		globals: true,
		environment: 'jsdom',
		setupFiles: ['./vitest-setup.ts'],
		exclude: [...configDefaults.exclude, '**/tests/**']
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
