import secureRedirectRule from './secure-redirect.js';

const plugin = {
	meta: {
		name: 'eslint-plugin-intuitem-sveltekit',
		version: '0.1.0'
	},
	configs: {},
	rules: {
		'secure-redirect': secureRedirectRule
	},
	processors: {}
};

export default plugin;
