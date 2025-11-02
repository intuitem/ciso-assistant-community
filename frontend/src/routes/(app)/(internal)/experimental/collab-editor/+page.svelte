<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { browser } from '$app/environment';

	// Props
	let { data } = $props();

	// Types
	interface User {
		id: string;
		name: string;
		email: string;
		color: string;
		cursorPosition: number;
		selectionStart: number;
		selectionEnd: number;
		lastActive: number;
	}

	interface Message {
		type: 'join' | 'leave' | 'cursor' | 'text' | 'selection';
		userId: string;
		userName?: string;
		userEmail?: string;
		userColor?: string;
		cursorPosition?: number;
		selectionStart?: number;
		selectionEnd?: number;
		text?: string;
		timestamp: number;
	}

	// User colors palette
	const USER_COLORS = [
		'#FF6B6B',
		'#4ECDC4',
		'#45B7D1',
		'#FFA07A',
		'#98D8C8',
		'#F7DC6F',
		'#BB8FCE',
		'#85C1E2'
	];

	// State
	let textContent = $state('');
	let textarea: HTMLTextAreaElement;
	let users = $state<User[]>([]);  // Changed from Map to Array for better reactivity
	let currentUser = $state<User | null>(null);
	let ws: WebSocket | null = null;
	let cleanupInterval: number;
	let reconnectInterval: number | null = null;
	let connectionStatus = $state<'connecting' | 'connected' | 'disconnected'>('disconnected');
	const STORAGE_KEY = 'collab-editor-content';

	// Get backend WebSocket URL
	// Note: Authentication token is httpOnly and automatically sent by browser
	const getBackendWsUrl = () => {
		if (!browser) return '';

		// In development, backend is typically on localhost:8000
		// In production, it should use the same host as the app
		const isDev = window.location.port === '5173' || window.location.port === '3000';

		if (isDev) {
			// Development: connect to backend on port 8000
			const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
			return `${protocol}//localhost:8000/ws/collab-editor/`;
		} else {
			// Production: use same host
			const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
			return `${protocol}//${window.location.host}/ws/collab-editor/`;
		}
	};
	const WS_URL = getBackendWsUrl();

	// Generate session ID (unique per tab)
	function generateSessionId() {
		return `session-${Math.random().toString(36).substr(2, 9)}-${Date.now()}`;
	}

	function getRandomColor() {
		return USER_COLORS[Math.floor(Math.random() * USER_COLORS.length)];
	}

	// Get user display name
	function getUserDisplayName() {
		if (data.user.first_name && data.user.last_name) {
			return `${data.user.first_name} ${data.user.last_name}`;
		} else if (data.user.first_name) {
			return data.user.first_name;
		} else if (data.user.email) {
			return data.user.email.split('@')[0];
		}
		return 'Anonymous User';
	}

	// Initialize user with actual user data
	function initializeUser() {
		const sessionId = generateSessionId();
		const userName = getUserDisplayName();
		const userEmail = data.user.email || 'unknown@example.com';
		const userColor = getRandomColor();

		currentUser = {
			id: sessionId,
			name: userName,
			email: userEmail,
			color: userColor,
			cursorPosition: 0,
			selectionStart: 0,
			selectionEnd: 0,
			lastActive: Date.now()
		};

		// Don't add self to users array - only remote users
	}

	// Load content from localStorage
	function loadContent() {
		if (browser) {
			const saved = localStorage.getItem(STORAGE_KEY);
			if (saved) {
				textContent = saved;
			}
		}
	}

	// Save content to localStorage
	function saveContent() {
		if (browser) {
			localStorage.setItem(STORAGE_KEY, textContent);
		}
	}

	// Clear content
	function clearContent() {
		textContent = '';
		saveContent();

		// Reset current user's cursor position
		if (currentUser) {
			currentUser.cursorPosition = 0;
			currentUser.selectionStart = 0;
			currentUser.selectionEnd = 0;
		}

		// Broadcast text clear
		broadcast({
			type: 'text',
			text: '',
			timestamp: Date.now()
		});

		// Broadcast cursor reset
		broadcast({
			type: 'cursor',
			cursor_position: 0,
			timestamp: Date.now()
		});
	}

	// Broadcast message via WebSocket
	function broadcast(message: any) {
		if (ws && ws.readyState === WebSocket.OPEN) {
			if (message.type === 'cursor') {
				console.log('📤 Sending cursor:', message.cursor_position);
			}
			ws.send(JSON.stringify(message));
		} else {
			console.error('❌ Cannot send - WebSocket not open. State:', ws?.readyState);
		}
	}

	// Connect to WebSocket
	function connectWebSocket() {
		if (!browser || !WS_URL) return;

		connectionStatus = 'connecting';
		console.log('Attempting to connect to WebSocket:', WS_URL);

		try {
			ws = new WebSocket(WS_URL);

			ws.onopen = () => {
				connectionStatus = 'connected';
				console.log('✅ WebSocket connected');

				// Clear any reconnect interval
				if (reconnectInterval) {
					clearInterval(reconnectInterval);
					reconnectInterval = null;
				}

				// Announce presence on connect
				broadcast({
					type: 'join',
					user_color: currentUser!.color,
					timestamp: Date.now()
				});
			};

			ws.onmessage = (event) => {
				try {
					const message = JSON.parse(event.data);
					handleMessage(message);
				} catch (e) {
					console.error('Error parsing message:', e);
				}
			};

			ws.onerror = (error) => {
				console.error('WebSocket error:', error);
				console.error('WebSocket readyState:', ws?.readyState);
			};

			ws.onclose = (event) => {
				connectionStatus = 'disconnected';
				console.log('WebSocket disconnected');
				console.log('Close code:', event.code, 'Reason:', event.reason);

				// Attempt to reconnect after 3 seconds
				if (!reconnectInterval) {
					reconnectInterval = window.setInterval(() => {
						console.log('Attempting to reconnect...');
						connectWebSocket();
					}, 3000);
				}
			};
		} catch (error) {
			console.error('Failed to create WebSocket:', error);
			connectionStatus = 'disconnected';
		}
	}

	// Handle incoming messages from WebSocket
	function handleMessage(message: any) {
		// Backend adds user_id, user_name, user_email to all messages
		const userId = message.user_id;

		// Ignore our own messages (shouldn't happen due to sender_channel check in backend)
		// Compare as strings since UUIDs come as strings from backend
		if (userId === String(data.user.id)) {
			return;
		}

		// Only log cursor messages for debugging
		if (message.type === 'cursor') {
			console.log('🔵 CURSOR UPDATE:', {
				from: message.user_name,
				position: message.cursor_position,
				userIdInArray: users.find(u => u.id === userId) ? 'FOUND' : 'NOT FOUND'
			});
		}

		switch (message.type) {
			case 'join':
				if (message.user_name && message.user_color && message.user_email) {
					// Check if user already exists
					const existingIndex = users.findIndex(u => u.id === userId);

					if (existingIndex >= 0) {
						// User already exists - just update color if it changed, but preserve cursor position
						// Don't send join reply - they already know about us
						users[existingIndex] = {
							...users[existingIndex],
							color: message.user_color,
							lastActive: message.timestamp || Date.now()
						};
					} else {
						// New user - add them
						const newUser: User = {
							id: userId,
							name: message.user_name,
							email: message.user_email,
							color: message.user_color,
							cursorPosition: 0,
							selectionStart: 0,
							selectionEnd: 0,
							lastActive: message.timestamp || Date.now()
						};
						users = [...users, newUser];
						console.log('✅ User joined:', message.user_name);

						// Always send our presence back to new users so they know about us
						// The backend prevents echo, so this won't cause infinite loops
						broadcast({
							type: 'join',
							user_color: currentUser!.color,
							timestamp: Date.now()
						});
					}
				}
				break;

			case 'leave':
				users = users.filter(u => u.id !== userId);
				break;

			case 'cursor':
				if (message.cursor_position !== undefined) {
					const userIndex = users.findIndex(u => u.id === userId);
					if (userIndex >= 0) {
						// Create new user object to trigger reactivity
						users[userIndex] = {
							...users[userIndex],
							cursorPosition: message.cursor_position,
							lastActive: message.timestamp || Date.now()
						};
						users = [...users]; // Trigger reactivity
						console.log('✅ Updated cursor to position:', message.cursor_position);
					} else {
						console.error('❌ User not found for cursor update. userId:', userId, 'users:', users.map(u => u.id));
					}
				}
				break;

			case 'selection':
				if (message.selection_start !== undefined && message.selection_end !== undefined) {
					const userIndex = users.findIndex(u => u.id === userId);
					if (userIndex >= 0) {
						// Create new user object to trigger reactivity
						users[userIndex] = {
							...users[userIndex],
							selectionStart: message.selection_start,
							selectionEnd: message.selection_end,
							lastActive: message.timestamp || Date.now()
						};
						users = [...users]; // Trigger reactivity
					}
				}
				break;

			case 'text':
				if (message.text !== undefined) {
					textContent = message.text;
					saveContent();

					// If text is cleared, reset all cursor positions
					if (message.text === '') {
						users = users.map(u => ({
							...u,
							cursorPosition: 0,
							selectionStart: 0,
							selectionEnd: 0,
							lastActive: message.timestamp || Date.now()
						}));
					} else {
						// Update lastActive for this user
						const userIndex = users.findIndex(u => u.id === userId);
						if (userIndex >= 0) {
							users[userIndex] = {
								...users[userIndex],
								lastActive: message.timestamp || Date.now()
							};
							users = [...users];
						}
					}
				}
				break;
		}
	}

	// Handle cursor position changes
	function handleSelectionChange() {
		if (!textarea || !currentUser) return;

		const cursorPosition = textarea.selectionStart;
		const selectionStart = textarea.selectionStart;
		const selectionEnd = textarea.selectionEnd;

		currentUser.cursorPosition = cursorPosition;
		currentUser.selectionStart = selectionStart;
		currentUser.selectionEnd = selectionEnd;

		broadcast({
			type: 'cursor',
			cursor_position: cursorPosition,
			timestamp: Date.now()
		});

		if (selectionStart !== selectionEnd) {
			broadcast({
				type: 'selection',
				selection_start: selectionStart,
				selection_end: selectionEnd,
				timestamp: Date.now()
			});
		}
	}

	// Throttle cursor updates to avoid flooding
	let lastCursorSend = 0;
	const CURSOR_THROTTLE_MS = 100; // Send cursor max once per 100ms

	// Handle text changes
	function handleInput() {
		if (!currentUser) return;

		saveContent(); // Save to localStorage

		// Update cursor position when typing
		if (textarea) {
			currentUser.cursorPosition = textarea.selectionStart;
		}

		broadcast({
			type: 'text',
			text: textContent,
			timestamp: Date.now()
		});

		// Also broadcast cursor position (throttled)
		const now = Date.now();
		if (now - lastCursorSend > CURSOR_THROTTLE_MS) {
			lastCursorSend = now;
			handleSelectionChange();
		}
	}

	// Clean up inactive users
	function cleanupInactiveUsers() {
		const now = Date.now();
		const timeout = 900000; // 15 minutes

		const before = users.length;
		users = users.filter(user => now - user.lastActive <= timeout);
		if (users.length < before) {
			console.log('🗑️ Cleaned up', before - users.length, 'inactive users');
		}
	}

	// Mirror element for accurate cursor positioning with text wrapping
	let mirrorDiv: HTMLDivElement | null = null;

	function initMirrorDiv() {
		if (!mirrorDiv && browser && textarea) {
			mirrorDiv = document.createElement('div');
			mirrorDiv.style.position = 'absolute';
			mirrorDiv.style.visibility = 'hidden';
			mirrorDiv.style.pointerEvents = 'none';
			mirrorDiv.style.whiteSpace = 'pre-wrap';
			mirrorDiv.style.wordWrap = 'break-word';
			mirrorDiv.style.overflow = 'hidden';
			document.body.appendChild(mirrorDiv);
		}
	}

	// Calculate cursor position in pixels with accurate text measurement and wrapping
	function getCursorCoordinates(position: number) {
		if (!textarea) return { top: 0, left: 0 };

		// Initialize mirror div
		initMirrorDiv();
		if (!mirrorDiv) return { top: 0, left: 0 };

		// Copy textarea styles to mirror div
		const computedStyle = window.getComputedStyle(textarea);
		mirrorDiv.style.font = computedStyle.font;
		mirrorDiv.style.fontSize = computedStyle.fontSize;
		mirrorDiv.style.fontFamily = computedStyle.fontFamily;
		mirrorDiv.style.fontWeight = computedStyle.fontWeight;
		mirrorDiv.style.lineHeight = computedStyle.lineHeight;
		mirrorDiv.style.letterSpacing = computedStyle.letterSpacing;
		mirrorDiv.style.padding = computedStyle.padding;
		mirrorDiv.style.border = computedStyle.border;
		mirrorDiv.style.boxSizing = computedStyle.boxSizing;

		// Set width to match textarea
		mirrorDiv.style.width = `${textarea.clientWidth}px`;

		const text = textarea.value;
		const beforeCursor = text.substring(0, position);

		// Create text content with a cursor marker
		const textNode = document.createTextNode(beforeCursor);
		const cursorSpan = document.createElement('span');
		cursorSpan.textContent = '|';
		cursorSpan.style.position = 'relative';

		// Clear and populate mirror div
		mirrorDiv.innerHTML = '';
		mirrorDiv.appendChild(textNode);
		mirrorDiv.appendChild(cursorSpan);

		// Get cursor span position
		const cursorRect = cursorSpan.getBoundingClientRect();
		const mirrorRect = mirrorDiv.getBoundingClientRect();

		const paddingLeft = parseInt(computedStyle.paddingLeft) || 0;
		const paddingTop = parseInt(computedStyle.paddingTop) || 0;

		// Calculate relative position
		const coordinates = {
			top: cursorRect.top - mirrorRect.top,
			left: cursorRect.left - mirrorRect.left
		};

		return coordinates;
	}

	onMount(() => {
		if (browser) {
			loadContent(); // Load saved content
			initializeUser();

			// Connect to WebSocket
			connectWebSocket();

			// Setup cleanup interval for inactive users
			cleanupInterval = window.setInterval(cleanupInactiveUsers, 2000);
		}
	});

	onDestroy(() => {
		if (browser) {
			// Close WebSocket
			if (ws) {
				ws.close();
			}

			// Clear intervals
			if (cleanupInterval) {
				clearInterval(cleanupInterval);
			}
			if (reconnectInterval) {
				clearInterval(reconnectInterval);
			}

			// Clean up mirror div
			if (mirrorDiv && mirrorDiv.parentNode) {
				mirrorDiv.parentNode.removeChild(mirrorDiv);
				mirrorDiv = null;
			}
		}
	});

	// Get active users (all remote users - we don't add self to the array)
	let activeUsers = $derived.by(() => {
		return users;
	});
</script>

<div class="container mx-auto p-8 max-w-6xl">
	<div class="mb-6">
		<div class="flex items-center justify-between mb-2">
			<h1 class="text-3xl font-bold">Collaborative Text Editor (Experimental)</h1>
			<div class="flex items-center gap-2">
				{#if connectionStatus === 'connected'}
					<span class="flex items-center gap-1 text-green-600 text-sm">
						<div class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
						Connected
					</span>
				{:else if connectionStatus === 'connecting'}
					<span class="flex items-center gap-1 text-yellow-600 text-sm">
						<div class="w-2 h-2 rounded-full bg-yellow-500 animate-pulse"></div>
						Connecting...
					</span>
				{:else}
					<span class="flex items-center gap-1 text-red-600 text-sm">
						<div class="w-2 h-2 rounded-full bg-red-500"></div>
						Disconnected
					</span>
				{/if}
			</div>
		</div>
		<p class="text-gray-600 mb-2">
			Real-time collaborative editing with WebSocket synchronization across different users and browsers.
		</p>
		<div class="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm">
			<p class="text-blue-800">
				<strong>✨ New:</strong> Now supports <strong>real cross-user collaboration</strong> using
				WebSockets! Open this page from different devices/browsers and collaborate in real-time.
			</p>
		</div>
	</div>

	<div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
		<!-- Main editor area -->
		<div class="lg:col-span-3">
			<div class="card p-4 bg-white shadow-lg">
				<div class="flex items-center justify-between mb-4">
					<div class="flex items-center gap-2">
						<div class="w-3 h-3 rounded-full" style="background-color: {currentUser?.color}"></div>
						<span class="font-medium">You are: {currentUser?.name}</span>
					</div>
					<div class="text-sm text-gray-500">
						{activeUsers.length} other {activeUsers.length === 1 ? 'user' : 'users'} online
						<span class="text-xs text-red-500">(raw: {users.length})</span>
					</div>
				</div>

				<div class="relative">
					<textarea
						bind:this={textarea}
						bind:value={textContent}
						oninput={handleInput}
						onselect={handleSelectionChange}
						onkeyup={handleSelectionChange}
						onclick={handleSelectionChange}
						class="w-full h-96 p-4 border border-gray-300 rounded-lg font-mono text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary-500"
						placeholder="Start typing... Open this page in multiple tabs to collaborate!"
					></textarea>

					<!-- Remote cursors overlay -->
					<div class="absolute top-0 left-0 pointer-events-none w-full h-full p-4">
						{#each activeUsers as user (user.id)}
							{@const coords = getCursorCoordinates(user.cursorPosition)}
							<div
								class="absolute w-0.5 h-5 animate-pulse"
								style="background-color: {user.color}; top: {coords.top}px; left: {coords.left}px;"
							>
								<div
									class="absolute -top-6 left-0 whitespace-nowrap text-xs px-2 py-1 rounded shadow-lg text-white"
									style="background-color: {user.color};"
								>
									{user.name}
								</div>
							</div>
						{/each}
					</div>
				</div>

				<div class="mt-4 flex items-center justify-between">
					<div class="text-sm text-gray-500">
						Character count: {textContent.length} | Cursor position: {currentUser?.cursorPosition ||
							0}
					</div>
					<button
						onclick={clearContent}
						class="px-3 py-1 text-sm bg-red-500 hover:bg-red-600 text-white rounded transition-colors"
					>
						<i class="fa-solid fa-trash"></i> Clear All
					</button>
				</div>
			</div>
		</div>

		<!-- Users sidebar -->
		<div class="lg:col-span-1">
			<div class="card p-4 bg-white shadow-lg">
				<h2 class="text-lg font-semibold mb-4">Active Users</h2>

				<!-- Current user -->
				<div class="mb-4 pb-4 border-b border-gray-200">
					<div class="flex items-center gap-3">
						<div class="w-8 h-8 rounded-full flex items-center justify-center text-white font-semibold" style="background-color: {currentUser?.color}">
							{currentUser?.name.charAt(0)}
						</div>
						<div class="flex-1">
							<div class="font-medium">{currentUser?.name}</div>
							<div class="text-xs text-gray-500">{currentUser?.email}</div>
							<div class="text-xs text-green-600">You (this tab)</div>
						</div>
						<div class="w-2 h-2 rounded-full bg-green-500"></div>
					</div>
				</div>

				<!-- Other users -->
				{#if activeUsers.length > 0}
					<div class="space-y-3">
						{#each activeUsers as user (user.id)}
							<div class="flex items-center gap-3">
								<div
									class="w-8 h-8 rounded-full flex items-center justify-center text-white font-semibold"
									style="background-color: {user.color}"
								>
									{user.name.charAt(0)}
								</div>
								<div class="flex-1">
									<div class="font-medium text-sm">{user.name}</div>
									<div class="text-xs text-gray-500">{user.email}</div>
									<div class="text-xs text-gray-400">Cursor: {user.cursorPosition}</div>
								</div>
								<div class="w-2 h-2 rounded-full bg-green-500"></div>
							</div>
						{/each}
					</div>
				{:else}
					<p class="text-sm text-gray-500 italic">No other users online</p>
					<p class="text-xs text-gray-400 mt-2">
						Share this page with colleagues or open in a different browser to collaborate!
					</p>
				{/if}
			</div>

			<!-- Instructions -->
			<div class="card p-4 bg-blue-50 mt-4">
				<h3 class="text-sm font-semibold mb-2 text-blue-900">How to test:</h3>
				<ol class="text-xs text-blue-800 space-y-1 list-decimal list-inside">
					<li>Open this page in different browsers or devices</li>
					<li>Share the link with team members</li>
					<li>Type and see updates appear in real-time</li>
					<li>Watch cursor positions of other users</li>
					<li>Each user gets a unique color</li>
				</ol>
			</div>

			<!-- Technical Info -->
			<div class="card p-4 bg-gray-50 mt-4">
				<h3 class="text-sm font-semibold mb-2 text-gray-900">Technical Details:</h3>
				<ul class="text-xs text-gray-700 space-y-1">
					<li><strong>Protocol:</strong> WebSocket</li>
					<li><strong>Backend:</strong> Django Channels</li>
					<li><strong>Sync:</strong> Cross-user, cross-browser</li>
					<li><strong>Storage:</strong> localStorage</li>
					<li><strong>User:</strong> {data.user.email}</li>
					<li><strong>Status:</strong> <span class={connectionStatus === 'connected' ? 'text-green-600' : 'text-red-600'}>{connectionStatus}</span></li>
				</ul>
			</div>
		</div>
	</div>
</div>

<style>
	@keyframes pulse {
		0%,
		100% {
			opacity: 1;
		}
		50% {
			opacity: 0.5;
		}
	}

	.animate-pulse {
		animation: pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite;
	}
</style>
