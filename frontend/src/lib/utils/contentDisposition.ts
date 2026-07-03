// Content-Disposition is Latin-1 only, so a raw UTF-8 filename throws a
// ByteString error. Emit an ASCII-safe fallback plus an RFC 5987 filename*.
// The ASCII pass also drops CR/LF and quoting chars, blocking header injection.
export function contentDispositionHeader(fileName: string, disposition = 'attachment'): string {
	const asciiFileName = fileName.replace(/[^\x20-\x7E]/g, '-').replace(/[;"%\\]/g, '-');
	return `${disposition}; filename="${asciiFileName}"; filename*=utf-8''${encodeURIComponent(fileName)}`;
}
