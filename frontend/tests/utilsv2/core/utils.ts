/** Returns true if the code is runned with the enterprise version. */
export function isEnterpriseMode(): boolean {
	return process.env.IS_ENTERPRISE === '1';
}
