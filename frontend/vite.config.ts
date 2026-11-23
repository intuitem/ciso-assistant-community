import adapter from '@sveltejs/adapter-node';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';
import { paraglideVitePlugin } from '@inlang/paraglide-js';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vitest/config';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
	plugins: [
		paraglideVitePlugin({
			project: './project.inlang',
			outdir: './src/paraglide',
			outputStructure: 'locale-modules',
			cookieName: 'LOCALE',
			strategy: ['custom-userPreference', 'cookie', 'custom-fallback', 'baseLocale']
		}),
		tailwindcss(),
		sveltekit({
			preprocess: vitePreprocess(),
			adapter: adapter()
		})
	],
	environments: {
		ssr: {
			build: {
				// SvelteKit defaults SSR sourcemaps to on; node runs without --enable-source-maps, so they'd ship unused.
				sourcemap: false,
				// Vite leaves SSR unminified; paraglide's messages chunk alone is ~39 MB of JSDoc and whitespace.
				// No mangling, so server stack traces keep function names.
				minify: 'oxc',
				rolldownOptions: { output: { minify: { compress: true, mangle: false } } }
			}
		}
	},
	optimizeDeps: {
		// @svelte-put/qr exports ./svg/QR.svelte under the "svelte" condition only.
		// Vite 8's dep scanner doesn't apply it, so scope the condition to the
		// scanner rather than resolve.conditions (which would break SSR node/browser).
		rolldownOptions: {
			resolve: {
				conditionNames: ['svelte', 'module', 'browser', 'import', 'default']
			}
		}
	},
	test: {
		include: ['{src}/**/*.{test,spec}.{js,ts}']
	}
});
