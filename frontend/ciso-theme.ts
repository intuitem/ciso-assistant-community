import type { CustomThemeConfig } from '@skeletonlabs/tw-plugin';

export const cisoTheme: CustomThemeConfig = {
	name: 'ciso-theme',
	properties: {
		// =~= Theme Properties =~=
		'--theme-font-family-base': `system-ui`,
		'--theme-font-family-heading': `system-ui`,
		'--theme-font-color-base': '0 0 0',
		'--theme-font-color-dark': '255 255 255',
		'--theme-rounded-base': '8px',
		'--theme-rounded-container': '6px',
		'--theme-border-base': '1px',
		// =~= Theme On-X Colors =~=
		'--on-primary': '255 255 255',
		'--on-secondary': '255 255 255',
		'--on-tertiary': '255 255 255',
		'--on-success': '0 0 0',
		'--on-warning': '0 0 0',
		'--on-error': '0 0 0',
		'--on-surface': '0 0 0',
		// =~= Theme Colors  =~=
		// primary | #4F46E5
		'--color-primary-50': '229 227 251', // #e5e3fb
		'--color-primary-100': '220 218 250', // #dcdafa
		'--color-primary-200': '211 209 249', // #d3d1f9
		'--color-primary-300': '185 181 245', // #b9b5f5
		'--color-primary-400': '132 126 237', // #847eed
		'--color-primary-500': '79 70 229', // #4F46E5
		'--color-primary-600': '71 63 206', // #473fce
		'--color-primary-700': '59 53 172', // #3b35ac
		'--color-primary-800': '47 42 137', // #2f2a89
		'--color-primary-900': '39 34 112', // #272270
		// secondary | #2563eb
		'--color-secondary-50': '222 232 252', // #dee8fc
		'--color-secondary-100': '211 224 251', // #d3e0fb
		'--color-secondary-200': '201 216 250', // #c9d8fa
		'--color-secondary-300': '168 193 247', // #a8c1f7
		'--color-secondary-400': '102 146 241', // #6692f1
		'--color-secondary-500': '37 99 235', // #2563eb
		'--color-secondary-600': '33 89 212', // #2159d4
		'--color-secondary-700': '28 74 176', // #1c4ab0
		'--color-secondary-800': '22 59 141', // #163b8d
		'--color-secondary-900': '18 49 115', // #123173
		// tertiary | #e11d48
		'--color-tertiary-50': '251 221 228', // #fbdde4
		'--color-tertiary-100': '249 210 218', // #f9d2da
		'--color-tertiary-200': '248 199 209', // #f8c7d1
		'--color-tertiary-300': '243 165 182', // #f3a5b6
		'--color-tertiary-400': '234 97 127', // #ea617f
		'--color-tertiary-500': '225 29 72', // #e11d48
		'--color-tertiary-600': '203 26 65', // #cb1a41
		'--color-tertiary-700': '169 22 54', // #a91636
		'--color-tertiary-800': '135 17 43', // #87112b
		'--color-tertiary-900': '110 14 35', // #6e0e23
		// success | #84cc16
		'--color-success-50': '237 247 220', // #edf7dc
		'--color-success-100': '230 245 208', // #e6f5d0
		'--color-success-200': '224 242 197', // #e0f2c5
		'--color-success-300': '206 235 162', // #ceeba2
		'--color-success-400': '169 219 92', // #a9db5c
		'--color-success-500': '132 204 22', // #84cc16
		'--color-success-600': '119 184 20', // #77b814
		'--color-success-700': '99 153 17', // #639911
		'--color-success-800': '79 122 13', // #4f7a0d
		'--color-success-900': '65 100 11', // #41640b
		// warning | #EAB308
		'--color-warning-50': '252 244 218', // #fcf4da
		'--color-warning-100': '251 240 206', // #fbf0ce
		'--color-warning-200': '250 236 193', // #faecc1
		'--color-warning-300': '247 225 156', // #f7e19c
		'--color-warning-400': '240 202 82', // #f0ca52
		'--color-warning-500': '234 179 8', // #EAB308
		'--color-warning-600': '211 161 7', // #d3a107
		'--color-warning-700': '176 134 6', // #b08606
		'--color-warning-800': '140 107 5', // #8c6b05
		'--color-warning-900': '115 88 4', // #735804
		// error | #ef4444
		'--color-error-50': '253 227 227', // #fde3e3
		'--color-error-100': '252 218 218', // #fcdada
		'--color-error-200': '251 208 208', // #fbd0d0
		'--color-error-300': '249 180 180', // #f9b4b4
		'--color-error-400': '244 124 124', // #f47c7c
		'--color-error-500': '239 68 68', // #ef4444
		'--color-error-600': '215 61 61', // #d73d3d
		'--color-error-700': '179 51 51', // #b33333
		'--color-error-800': '143 41 41', // #8f2929
		'--color-error-900': '117 33 33', // #752121
		// surface | #94a3b8
		'--color-surface-50': '239 241 244', // #eff1f4
		'--color-surface-100': '234 237 241', // #eaedf1
		'--color-surface-200': '228 232 237', // #e4e8ed
		'--color-surface-300': '212 218 227', // #d4dae3
		'--color-surface-400': '180 191 205', // #b4bfcd
		'--color-surface-500': '148 163 184', // #94a3b8
		'--color-surface-600': '133 147 166', // #8593a6
		'--color-surface-700': '111 122 138', // #6f7a8a
		'--color-surface-800': '89 98 110', // #59626e
		'--color-surface-900': '73 80 90' // #49505a
	}
};
