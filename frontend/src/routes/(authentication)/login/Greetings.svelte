<script lang="ts">
	import { m } from '$paraglide/messages';
	import Typewriter from 'sv-typewriter';
</script>

<div
	id="hellothere"
	class="flex flex-col justify-center items-center lg:w-3/5 text-gray-900 px-4 lg:px-0"
>
	<Typewriter mode="loopOnce" cursor={false} interval={50}>
		<div class="text-2xl unstyled text-center pb-4">
			<span class="text-2xl text-center">{m.helloThere()} </span>
			<span> {m.thisIsCisoAssistant()} </span>
		</div>
	</Typewriter>
	<Typewriter mode="cascade" cursor={false} interval={45} delay={5000}>
		<div class="text-2xl unstyled text-center">
			<span> {m.yourStreamlined()} </span>
			<span class="font-black"> {m.oneStopShop()} </span>
			<span> {m.forComplianceRiskManagement()} </span>
		</div>
	</Typewriter>
</div>
