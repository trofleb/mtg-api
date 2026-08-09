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

  // Issue #28. cmc_min/cmc_max are declared int on the API, so a fractional
  // bound comes back 422 - and because searchCards runs inside a server
  // component, that 422 is rendered to the user as a 500 page rather than as
  // a search. The slider only ever produces integers, so a fraction is a
  // hand-edited or stale URL; round it rather than dropping the filter the
  // URL plainly asks for.
  it("rounds a fractional cmc bound to the integer the API accepts", () => {
    const { filters } = parseSearchParams({ cmc_min: "1.5", cmc_max: "5.2" });
    expect(filters.cmc_min).toBe(2);
    expect(filters.cmc_max).toBe(5);
    expect(Number.isInteger(filters.cmc_min)).toBe(true);
    expect(Number.isInteger(filters.cmc_max)).toBe(true);
  });

  it("never emits a non-integer cmc bound, whatever the URL says", () => {
    for (const raw of ["0.1", "3.9", "-2.5", "1e2.5", "15.999"]) {
      const { filters } = parseSearchParams({ cmc_min: raw, cmc_max: raw });
      for (const value of [filters.cmc_min, filters.cmc_max]) {
        if (value !== undefined) expect(Number.isInteger(value)).toBe(true);
      }
    }
  });

  // 0.4 rounds to 0, which is CMC_MIN, so the bound stops narrowing the range
  // and is dropped - the same treatment "0" already gets.
  it("drops a fraction that rounds back onto the full range", () => {
    const { filters } = parseSearchParams({ cmc_min: "0.4", cmc_max: "15.7" });
    expect(filters.cmc_min).toBeUndefined();
    expect(filters.cmc_max).toBeUndefined();
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
