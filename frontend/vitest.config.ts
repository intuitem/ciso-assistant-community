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
			$lib: path.resolve(__dirname, 'src/lib'),
			$paraglide: path.resolve(__dirname, 'src/paraglide'),
			'$app/environment': path.resolve(__dirname, 'vitest-mocks/app-environment.ts'),
			'$app/navigation': path.resolve(__dirname, 'vitest-mocks/app-navigation.ts'),
			'$app/forms': path.resolve(__dirname, 'vitest-mocks/app-forms.ts'),
			'$app/state': path.resolve(__dirname, 'vitest-mocks/app-state.ts'),
			'$app/stores': path.resolve(__dirname, 'vitest-mocks/app-stores.ts'),
			'$env/dynamic/public': path.resolve(__dirname, 'vitest-mocks/env-dynamic-public.ts')
		}
	}
});
