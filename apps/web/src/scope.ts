import type { Claim } from "./contracts";

/** Revision snapshots contain read-only IDs/version metadata; commands accept scope only. */
export function scopeInput(claim: Claim): Omit<Claim, "id"> {
  const {
    text,
    subject,
    geography,
    period,
    stage,
    measure,
    value,
    unit,
    currency,
    denominator,
    attribution,
  } = claim;
  return {
    text,
    subject,
    geography,
    period,
    stage,
    measure,
    value,
    unit,
    currency,
    denominator,
    attribution,
  };
}
