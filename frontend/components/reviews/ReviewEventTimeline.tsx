import { Badge } from "@/components/ui/Badge";
import type { ReviewEvent, ReviewEventType } from "@/lib/types";

const EVENT_LABELS: Record<ReviewEventType, string> = {
  review_started: "Review gestartet",
  comment_added: "Kommentar hinzugefügt",
  approved: "Freigegeben (intern)",
  rejected: "Abgelehnt",
  changes_requested: "Änderungen angefordert",
  archived: "Archiviert",
};

function formatDate(value: string): string {
  return new Date(value).toLocaleString("de-DE");
}

interface ReviewEventTimelineProps {
  events: ReviewEvent[];
}

export function ReviewEventTimeline({ events }: ReviewEventTimelineProps) {
  if (events.length === 0) {
    return (
      <p className="text-sm text-slate-500">Noch keine Review-Ereignisse vorhanden.</p>
    );
  }

  return (
    <ul className="space-y-3">
      {events.map((event) => (
        <li key={event.id} className="border-l-2 border-slate-200 pl-3">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="neutral">{EVENT_LABELS[event.event_type] ?? event.event_type}</Badge>
            <span className="text-xs text-slate-500">{formatDate(event.created_at)}</span>
            {event.reviewer_name ? (
              <span className="text-xs text-slate-500">von {event.reviewer_name}</span>
            ) : null}
          </div>
          {event.previous_status || event.new_status ? (
            <p className="mt-1 text-xs text-slate-500">
              {event.previous_status ?? "—"} → {event.new_status ?? "—"}
            </p>
          ) : null}
          {event.comment ? (
            <p className="mt-1 text-sm text-slate-700">{event.comment}</p>
          ) : null}
        </li>
      ))}
    </ul>
  );
}
