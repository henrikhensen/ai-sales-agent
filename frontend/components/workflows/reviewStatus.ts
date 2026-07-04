import type { WorkflowReviewStatus } from "@/lib/types";

export const REVIEW_STATUS_OPTIONS: { value: WorkflowReviewStatus; label: string }[] = [
  { value: "needs_review", label: "Needs Review" },
  { value: "reviewed", label: "Reviewed" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
  { value: "archived", label: "Archived" },
];

export const REVIEW_STATUS_TONE: Record<
  WorkflowReviewStatus,
  "neutral" | "positive" | "negative" | "warning" | "info"
> = {
  needs_review: "warning",
  reviewed: "info",
  approved: "positive",
  rejected: "negative",
  archived: "neutral",
};
