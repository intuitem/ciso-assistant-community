import { describe, expect, it } from "vitest";
import type { IExecuteFunctions, IHttpRequestOptions } from "n8n-workflow";
import { DomainHandler } from "./DomainHandler";

const TOTAL = 450;

function run(params: Record<string, unknown>, serverMax = 200) {
  const urls: string[] = [];
  const executeFunctions = {
    getNodeParameter: (name: string, _i: number, fallback?: unknown) =>
      name in params ? params[name] : fallback,
    getNode: () => ({ name: "CA" }),
    helpers: {
      httpRequestWithAuthentication: async (
        _type: string,
        { url }: IHttpRequestOptions,
      ) => {
        urls.push(url);
        const q = new URL(url).searchParams;
        const offset = Number(q.get("offset") ?? 0);
        const limit = Math.min(Number(q.get("limit")), serverMax);
        const end = Math.min(offset + limit, TOTAL);
        const results = Array.from({ length: end - offset }, (_, k) => ({
          id: offset + k,
        }));
        return { count: TOTAL, next: end < TOTAL ? "/next" : null, results };
      },
    },
  } as unknown as IExecuteFunctions;
  const context = {
    executeFunctions,
    credentials: { baseUrl: "http://ca/api", patKey: "t", skipTLS: false },
    itemIndex: 0,
  };
  return new DomainHandler()
    .execute("list", context)
    .then((out) => ({ out, urls }));
}

const ids = (out: { results?: unknown }) =>
  (out.results as { id: number }[]).map((r) => r.id);

describe("list pagination", () => {
  it("returnAll pages through every row once, in order", async () => {
    const { out, urls } = await run({ returnAll: true });
    expect(urls).toHaveLength(3);
    expect(out.count).toBe(TOTAL);
    expect(ids(out)).toEqual([...Array(TOTAL).keys()]);
  });

  it("limit stops early and asks only for what is missing", async () => {
    const { out, urls } = await run({ returnAll: false, limit: 250 });
    expect(ids(out)).toEqual([...Array(250).keys()]);
    expect(urls.map((u) => new URL(u).searchParams.get("limit"))).toEqual([
      "200",
      "50",
    ]);
  });

  it("follows next when the server clamps the page size", async () => {
    const { out, urls } = await run({ returnAll: true }, 100);
    expect(urls).toHaveLength(5);
    expect(ids(out)).toEqual([...Array(TOTAL).keys()]);
  });
});
