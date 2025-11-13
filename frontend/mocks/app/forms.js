// Source - https://stackoverflow.com/a
// Posted by Sondge
// Retrieved 2025-11-13, License - CC BY-SA 4.0

import { vi } from 'vitest';

const goto = vi.fn();
const invalidate = vi.fn();
const invalidateAll = vi.fn();

module.exports = {
    goto,
    invalidate,
    invalidateAll
};