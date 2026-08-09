import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { type CardFilter, getAllSets, getCardByOracleId, searchCards } from "./api";

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe("api", () => {
  beforeEach(() => {
    mockFetch.mockClear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("searchCards", () => {
    it("should fetch cards with basic search text", async () => {
      // The API exposes the oracle_id grouping key as "id".
      const mockResponse = {
        cards: [
          {
            id: "oracle-1",
            name: "Black Lotus",
            mana_cost: "{0}",
            type_line: "Artifact",
          },
        ],
        cursor: null,
        has_more: false,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await searchCards("Black Lotus");

      expect(mockFetch).toHaveBeenCalledOnce();
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/cards/search/Black%20Lotus"),
        expect.objectContaining({
          method: "GET",
          headers: {
            "Content-Type": "application/json",
          },
        })
      );
      expect(result).toEqual({
        cards: [
          {
            id: "oracle-1",
            name: "Black Lotus",
            mana_cost: "{0}",
            type_line: "Artifact",
          },
        ],
        cursor: null,
        has_more: false,
      });
    });

    it("uses id when the API provides it", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          cards: [{ id: "oracle-abc", name: "Lightning Bolt" }],
          cursor: null,
          has_more: false,
        }),
      });

      const result = await searchCards("bolt");

      expect(result.cards[0].id).toBe("oracle-abc");
    });

    it("falls back to _id from an older API build, without leaking it", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          cards: [{ _id: "oracle-legacy", name: "Lightning Bolt" }],
          cursor: null,
          has_more: false,
        }),
      });

      const result = await searchCards("bolt");

      expect(result.cards[0].id).toBe("oracle-legacy");
      expect(result.cards[0]).not.toHaveProperty("_id");
    });

    // Issue #22. A card with neither id nor _id is a contract violation -
    // OracleCard requires id - but the fallback turned it into "" without a
    // word, and CardTile then rendered href="/card/". The card is still
    // returned so the page does not silently lose a result; what changes is
    // that the violation is now observable.
    it("warns rather than silently emitting an empty id", async () => {
      const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          cards: [{ name: "Propaganda // Propaganda" }],
          cursor: null,
          has_more: false,
        }),
      });

      const result = await searchCards("propaganda");

      expect(warn).toHaveBeenCalledOnce();
      expect(warn.mock.calls[0].join(" ")).toContain("Propaganda // Propaganda");
      expect(result.cards).toHaveLength(1);
      expect(result.cards[0].id).toBe("");
      warn.mockRestore();
    });

    it("does not warn for a card that has an id", async () => {
      const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          cards: [{ id: "oracle-abc", name: "Lightning Bolt" }],
          cursor: null,
          has_more: false,
        }),
      });

      await searchCards("bolt");

      expect(warn).not.toHaveBeenCalled();
      warn.mockRestore();
    });

    it("should include cursor parameter when provided", async () => {
      const mockResponse = {
        cards: [],
        cursor: "0.9:abc123",
        has_more: true,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      await searchCards("test", "0.9:abc123");

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("cursor=0.9%3Aabc123"),
        expect.any(Object)
      );
    });

    it("should include filter parameters as query params when provided", async () => {
      const mockResponse = {
        cards: [],
        cursor: null,
        has_more: false,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const filters: CardFilter = {
        sets: ["LEA", "LEB"],
        colors: ["W", "U"],
        color_operator: "and",
        cmc_min: 2,
        cmc_max: 5,
        types: ["Creature"],
        rarities: ["rare", "mythic"],
      };

      await searchCards("test", null, filters);

      // Check URL contains filter query params
      const callUrl = mockFetch.mock.calls[0][0];
      expect(callUrl).toContain("sets=LEA");
      expect(callUrl).toContain("sets=LEB");
      expect(callUrl).toContain("colors=W");
      expect(callUrl).toContain("colors=U");
      expect(callUrl).toContain("color_operator=and");
      expect(callUrl).toContain("cmc_min=2");
      expect(callUrl).toContain("cmc_max=5");
      expect(callUrl).toContain("types=Creature");
      expect(callUrl).toContain("rarities=rare");
      expect(callUrl).toContain("rarities=mythic");

      // Check request has no body
      const callOptions = mockFetch.mock.calls[0][1];
      expect(callOptions.body).toBeUndefined();
    });

    it("should not include undefined filter values in query params", async () => {
      const mockResponse = {
        cards: [],
        cursor: null,
        has_more: false,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const filters: CardFilter = {
        colors: ["W"],
      };

      await searchCards("test", null, filters);

      // Check URL only contains provided filter values
      const callUrl = mockFetch.mock.calls[0][0];
      expect(callUrl).toContain("colors=W");
      expect(callUrl).not.toContain("sets=");
      expect(callUrl).not.toContain("cmc_min=");
      expect(callUrl).not.toContain("rarities=");
    });

    it("should throw error when fetch fails", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        statusText: "Not Found",
      });

      await expect(searchCards("test")).rejects.toThrow("Failed to search cards: Not Found");
    });

    it("should use default API base URL", async () => {
      const mockResponse = {
        cards: [],
        cursor: null,
        has_more: false,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      await searchCards("test");

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("http://api:8000/cards/search"),
        expect.any(Object)
      );
    });
  });

  describe("getAllSets", () => {
    it("should fetch all sets successfully", async () => {
      const mockResponse = {
        sets: ["LEA", "LEB", "ARN", "ATQ"],
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await getAllSets();

      expect(mockFetch).toHaveBeenCalledOnce();
      expect(mockFetch).toHaveBeenCalledWith(
        "http://api:8000/sets",
        expect.objectContaining({
          method: "GET",
          headers: {
            "Content-Type": "application/json",
          },
        })
      );
      expect(result).toEqual(["LEA", "LEB", "ARN", "ATQ"]);
    });

    it("should throw error when fetch fails", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        statusText: "Internal Server Error",
      });

      await expect(getAllSets()).rejects.toThrow("Failed to fetch sets: Internal Server Error");
    });
  });

  describe("getCardByOracleId", () => {
    it("fetches the aggregated endpoint and normalises _id", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ id: "oracle-xyz", name: "Black Lotus" }),
      });

      const card = await getCardByOracleId("oracle-xyz");

      expect(mockFetch).toHaveBeenCalledWith(
        "http://api:8000/cards/oracle/oracle-xyz/aggregated",
        expect.objectContaining({ method: "GET" })
      );
      expect(card?.id).toBe("oracle-xyz");
      expect(card).not.toHaveProperty("_id");
    });

    it("returns null on 404 rather than throwing, so the page can notFound()", async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 404, statusText: "Not Found" });

      await expect(getCardByOracleId("missing")).resolves.toBeNull();
    });

    it("throws on other failures", async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 500, statusText: "Server Error" });

      await expect(getCardByOracleId("boom")).rejects.toThrow("Failed to fetch card: Server Error");
    });

    it("encodes the oracle id", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ id: "a b", name: "X" }),
      });

      await getCardByOracleId("a b");

      expect(mockFetch).toHaveBeenCalledWith(
        "http://api:8000/cards/oracle/a%20b/aggregated",
        expect.any(Object)
      );
    });
  });
});
