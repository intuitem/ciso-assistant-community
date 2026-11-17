// adapter-node 6 dropped the runtime ORIGIN variable (paths.origin is build-time only), but our
// deployments set ORIGIN on prebuilt images. Feed it through PROTOCOL_HEADER/HOST_HEADER instead,
// overwriting whatever the client sent in those headers.
const origin = process.env.ORIGIN ? new URL(process.env.ORIGIN) : null;
if (origin) {
	process.env.PROTOCOL_HEADER = 'x-ciso-origin-protocol';
	process.env.HOST_HEADER = 'x-ciso-origin-host';
	delete process.env.PORT_HEADER;
}

// Dynamic import: adapter-node reads the env above when the module loads
const { server } = await import('../build/index.js');

if (origin) {
	const protocol = origin.protocol.slice(0, -1);
	server.prependListener('request', (req) => {
		req.headers['x-ciso-origin-protocol'] = protocol;
		req.headers['x-ciso-origin-host'] = origin.host;
	});
}

// adapter-node closes the server gracefully on SIGINT/SIGTERM; exit once it has rather than
// wait on timers the app may still hold
process.on('sveltekit:shutdown', () => process.exit(0));
