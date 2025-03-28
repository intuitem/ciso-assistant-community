import { paraglideVitePlugin } from '@inlang/paraglide-js';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vitest/config';

export default defineConfig({
	plugins: [
		paraglideVitePlugin({
			project: './project.inlang',
			outdir: './src/paraglide',
			outputStructure: 'locale-modules'
		}),
		sveltekit()
	],
	test: {
		include: ['{src}/**/*.{test,spec}.{js,ts}']
	}
});
