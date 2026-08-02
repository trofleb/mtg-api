import { describe, expect, it } from "vitest";
import { buildSearchParams, DEFAULT_QUERY, parseSearchParams } from "./search-params";

describe("parseSearchParams", () => {
  it("falls back to the default query when q is absent", () => {
    expect(parseSearchParams({}).query).toBe(DEFAULT_QUERY);
  });

  it("reads the query and cursor", () => {
    const state = parseSearchParams({ q: "bolt", cursor: "0.9:abc" });
    expect(state.query).toBe("bolt");
    expect(state.cursor).toBe("0.9:abc");
  });

  it("returns a null cursor when absent", () => {
    expect(parseSearchParams({ q: "bolt" }).cursor).toBeNull();
  });

  it("normalises a single repeated param into an array", () => {
    expect(parseSearchParams({ colors: "R" }).filters.colors).toEqual(["R"]);
    expect(parseSearchParams({ colors: ["R", "G"] }).filters.colors).toEqual(["R", "G"]);
  });

  it("leaves empty filters undefined rather than empty arrays", () => {
    const { filters } = parseSearchParams({ q: "bolt" });
    expect(filters.colors).toBeUndefined();
    expect(filters.sets).toBeUndefined();
    expect(filters.types).toBeUndefined();
    expect(filters.rarities).toBeUndefined();
  });

  it("ignores color_operator when no colors are selected", () => {
    const { filters } = parseSearchParams({ color_operator: "and" });
    expect(filters.color_operator).toBeUndefined();
  });

  it("keeps color_operator when colors are selected", () => {
    const { filters } = parseSearchParams({ colors: ["R"], color_operator: "and" });
    expect(filters.color_operator).toBe("and");
  });

  it("rejects an unrecognised color_operator", () => {
    const { filters } = parseSearchParams({ colors: ["R"], color_operator: "sideways" });
    expect(filters.color_operator).toBeUndefined();
  });

  it("drops cmc bounds that match the full range", () => {
    const { filters } = parseSearchParams({ cmc_min: "0", cmc_max: "16" });
    expect(filters.cmc_min).toBeUndefined();
    expect(filters.cmc_max).toBeUndefined();
  });

  it("keeps cmc bounds that narrow the range", () => {
    const { filters } = parseSearchParams({ cmc_min: "2", cmc_max: "5" });
    expect(filters.cmc_min).toBe(2);
    expect(filters.cmc_max).toBe(5);
  });

  it("ignores non-numeric cmc values", () => {
    const { filters } = parseSearchParams({ cmc_min: "abc" });
    expect(filters.cmc_min).toBeUndefined();
  });
});

describe("buildSearchParams", () => {
  it("round-trips through parseSearchParams", () => {
    const state = {
      query: "bolt",
      cursor: "0.9:abc",
      filters: {
        sets: ["LEA", "LEB"],
        colors: ["R"],
        color_operator: "and" as const,
        cmc_min: 2,
        cmc_max: 5,
        types: ["Instant"],
        rarities: ["rare"],
      },
    };

    const reparsed = parseSearchParams(
      Object.fromEntries(new URLSearchParams(buildSearchParams(state)).entries())
    );

    expect(reparsed.query).toBe("bolt");
    expect(reparsed.cursor).toBe("0.9:abc");
    expect(reparsed.filters.color_operator).toBe("and");
    expect(reparsed.filters.cmc_min).toBe(2);
    expect(reparsed.filters.cmc_max).toBe(5);
  });

  it("repeats multi-valued filters", () => {
    const qs = buildSearchParams({
      query: "bolt",
      cursor: null,
      filters: { sets: ["LEA", "LEB"] },
    });
    expect(qs).toContain("sets=LEA");
    expect(qs).toContain("sets=LEB");
  });

  it("omits the cursor when null", () => {
    const qs = buildSearchParams({ query: "bolt", cursor: null, filters: {} });
    expect(qs).not.toContain("cursor");
  });

  it("includes the cursor when set", () => {
    const qs = buildSearchParams({ query: "bolt", cursor: "0.9:abc", filters: {} });
    expect(qs).toContain("cursor=0.9");
  });

  it("encodes special characters in the query", () => {
    const qs = buildSearchParams({ query: "Black Lotus", cursor: null, filters: {} });
    expect(qs).toContain("q=Black+Lotus");
  });
});
