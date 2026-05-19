import { paraglideVitePlugin } from '@inlang/paraglide-js';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vitest/config';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
	build: {
		target: 'es2022'
	},
	optimizeDeps: {
		esbuildOptions: {
			target: 'es2022'
		}
	},
	plugins: [
		paraglideVitePlugin({
			project: './project.inlang',
			outdir: './src/paraglide',
			outputStructure: 'locale-modules',
			cookieName: 'LOCALE',
			strategy: ['custom-userPreference', 'cookie', 'custom-fallback', 'baseLocale']
		}),
		tailwindcss(),
		sveltekit()
	],
	test: {
		include: ['{src}/**/*.{test,spec}.{js,ts}']
	}
});
