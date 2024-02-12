import { sveltekit } from '@sveltejs/kit/vite';
import { paraglide } from '@inlang/paraglide-js-adapter-vite';
import { defineConfig } from 'vitest/config';

export default defineConfig({
	plugins: [
		sveltekit(),
		paraglide({
			project: './project.inlang',
			outdir: './src/paraglide'
		})
	],
	test: {
		include: ['{src}/**/*.{test,spec}.{js,ts}']
	}
});
