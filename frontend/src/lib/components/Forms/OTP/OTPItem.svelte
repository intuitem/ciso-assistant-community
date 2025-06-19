<script lang="ts">
	interface Props {
		input?: null | HTMLInputElement;
		index: number;
		value: string;
		codes: string[];
		inputs: (null | HTMLInputElement)[];
		className: string;
		num: boolean;
		style: string;
		placeholder: string;
	}

	let {
		input = $bindable(null),
		index,
		value = $bindable(),
		codes = $bindable(),
		inputs,
		className,
		num,
		style,
		placeholder
	}: Props = $props();

	let key: string;

	function shiftFocus(key: string) {
		if (
			(!/[0-9]/.test(key) && num && key) ||
			key === 'ArrowRight' ||
			key === 'ArrowLeft' ||
			key === 'Backspace'
		)
			return;
		if (value === ' ') {
			value = '';
			return;
		}
		if (index !== inputs.length - 1) (inputs[index + 1] as HTMLInputElement).focus();
	}

	function keyDownHandler(e: KeyboardEvent) {
		if (e.ctrlKey && e.key === 'z') {
			e.preventDefault();
		}
		key = e.key;
		if (value.length >= 1 && !e.ctrlKey) shiftFocus(key);
	}

	function typeHandler(e: KeyboardEvent) {
		if (value.length >= 1 || (!/[0-9]/.test(e.key) && num)) {
			e.preventDefault();
		}
	}

	function changeHandler(e: Event) {
		const val = (e.target as HTMLInputElement).value;
		if (/[0-9]/.test(val) || !num || !val) {
			codes = codes.map((c, i) => {
				if (i < index) {
					return c === '' ? ' ' : c;
				} else if (i === index) {
					return val[0];
				}
				return c;
			});
			// value = val[0];
			if (!val) {
				const len = codes.length;
				const filtered = codes.filter((_, i) => i !== index);
				codes = [...filtered, ...Array(len - filtered.length).fill('')];
			}
			shiftFocus(key);
		}
	}

	function keyUpHandler(e: KeyboardEvent) {
		if ((e.key === 'Backspace' || e.key === 'ArrowLeft') && index !== 0) {
			inputs[index - 1]?.focus();
		} else if (e.key === 'ArrowRight' && index !== inputs.length - 1) {
			inputs[index + 1]?.focus();
		}
	}

	function pasteHandler(e: ClipboardEvent) {
		e.preventDefault();
		const paste = e.clipboardData?.getData('text');
		if (!paste) return;
		let pasteValue = paste.replace(num ? /[^0-9]/g : '', '').slice(0, codes.length - index);
		const newCodes = [
			...codes.slice(0, index),
			...pasteValue.split(''),
			...codes.slice(index + pasteValue.length)
		];
		codes = newCodes;
	}
</script>

<input
	class="{className} input w-24 h-24 text-4xl text-center"
	bind:this={input}
	onkeydown={keyDownHandler}
	onkeyup={keyUpHandler}
	onkeypress={typeHandler}
	oninput={changeHandler}
	onpaste={pasteHandler}
	{style}
	{value}
	{placeholder}
/>
