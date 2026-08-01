import { describe, expect, it } from "vitest";
import { decisions } from "./catalog";
import {
  applyDecision,
  deriveArchitecture,
  getNextDecision,
} from "./engine";
import type { AdvisorState } from "./types";

describe("architecture refinement engine", () => {
  it("starts with the first unresolved architecture decision", () => {
    expect(getNextDecision({ answers: {} })?.id).toBe("execution");
  });

  it("replaces unresolved execution placement with a hybrid runtime", () => {
    const state = applyDecision({ answers: {} }, "execution", "hybrid");
    const result = deriveArchitecture(state);
    const ids = new Set(result.components.map((item) => item.id));

    expect(ids.has("execution-placement")).toBe(false);
    expect(ids.has("local-runtime")).toBe(true);
    expect(ids.has("ephemeral-runtime")).toBe(true);
    expect(ids.has("persistent-runtime")).toBe(true);
  });

  it("adds model economics when adaptive routing is selected", () => {
    let state: AdvisorState = { answers: {} };
    state = applyDecision(state, "execution", "hybrid");
    state = applyDecision(state, "routing", "adaptive");
    const result = deriveArchitecture(state);

    expect(result.economics.cacheHitRate).toBe(18);
    expect(result.economics.costPerSuccessfulTask).toBeLessThan(0.5);
    expect(
      result.services.some((service) =>
        service.recommended.includes("Amazon ElastiCache for Valkey"),
      ),
    ).toBe(true);
  });

  it("never emits edges to removed components", () => {
    let state: AdvisorState = { answers: {} };
    for (const decision of decisions) {
      const recommended = decision.options.find((option) => option.recommended);
      state = applyDecision(
        state,
        decision.id,
        recommended?.id ?? decision.options[0].id,
      );
    }

    const result = deriveArchitecture(state);
    const ids = new Set(result.components.map((item) => item.id));
    for (const edge of result.edges) {
      expect(ids.has(edge.source)).toBe(true);
      expect(ids.has(edge.target)).toBe(true);
    }
  });

  it("rejects options that do not belong to a decision", () => {
    expect(() =>
      applyDecision({ answers: {} }, "execution", "not-a-real-option"),
    ).toThrow("Unknown option");
  });
});
