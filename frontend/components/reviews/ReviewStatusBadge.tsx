import { Badge } from "@/components/ui/Badge";
import type { EmailDraftReviewStatus } from "@/lib/types";

export const EMAIL_REVIEW_STATUS_OPTIONS: {
  value: EmailDraftReviewStatus;
  label: string;
}[] = [
  { value: "needs_review", label: "Needs Review" },
  { value: "in_review", label: "In Review" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
  { value: "changes_requested", label: "Changes Requested" },
  { value: "archived", label: "Archived" },
];

export const EMAIL_REVIEW_STATUS_TONE: Record<
  EmailDraftReviewStatus,
  "neutral" | "positive" | "negative" | "warning" | "info"
> = {
  needs_review: "warning",
  in_review: "info",
  approved: "positive",
  rejected: "negative",
  changes_requested: "warning",
  archived: "neutral",
};

interface ReviewStatusBadgeProps {
  status: EmailDraftReviewStatus;
}

export function ReviewStatusBadge({ status }: ReviewStatusBadgeProps) {
  return <Badge tone={EMAIL_REVIEW_STATUS_TONE[status]}>{status}</Badge>;
}
