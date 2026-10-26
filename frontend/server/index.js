import '../build/index.js';

// adapter-node closes the server gracefully on SIGINT/SIGTERM; exit once it has rather than
// wait on timers the app may still hold
process.on('sveltekit:shutdown', () => process.exit(0));
