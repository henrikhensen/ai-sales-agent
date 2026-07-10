"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { ApiError, getEntityQualityScores } from "@/lib/api";
import type { QualityEntityType, QualityScore } from "@/lib/types";

const SCORE_LEVEL_TONE: Record<string, "positive" | "warning" | "negative" | "neutral"> = {
  excellent: "positive",
  good: "positive",
  acceptable: "neutral",
  weak: "warning",
  poor: "negative",
  blocked: "negative",
};

interface QualityScoreBadgeProps {
  entityType: QualityEntityType;
  entityId: string | null | undefined;
}

/**
 * Compact, read-only quality score indicator for an entity detail view.
 * Silently renders nothing if scoring isn't available/no score exists yet —
 * a missing score is not an error, just "not scored yet".
 */
export function QualityScoreBadge({ entityType, entityId }: QualityScoreBadgeProps) {
  const [score, setScore] = useState<QualityScore | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    if (!entityId) {
      setScore(null);
      setLoaded(true);
      return;
    }
    setLoaded(false);
    getEntityQualityScores(entityType, entityId)
      .then((result) => {
        if (!cancelled) {
          setScore(result.items[0] ?? null);
        }
      })
      .catch((err) => {
        if (!cancelled && !(err instanceof ApiError)) {
          throw err;
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoaded(true);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [entityType, entityId]);

  if (!loaded || !score) {
    return null;
  }

  return (
    <span className="inline-flex items-center gap-2">
      <Badge tone={SCORE_LEVEL_TONE[score.score_level] ?? "neutral"}>
        Quality: {score.score_total} ({score.score_level})
      </Badge>
      {score.warnings.length > 0 ? (
        <Badge tone="warning">{score.warnings.length} Warnung(en)</Badge>
      ) : null}
      <a
        href="/quality/feedback"
        className="text-xs text-brand-700 underline hover:no-underline"
      >
        Feedback geben
      </a>
    </span>
  );
}
