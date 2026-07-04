// Shared helpers for turning simple textarea input (one item per line) into
// the optional string-list fields the agent request schemas expect.

export function linesToList(value: string): string[] | undefined {
  const items = value
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
  return items.length > 0 ? items : undefined;
}

export function listToLines(value: string[] | null | undefined): string {
  return value ? value.join("\n") : "";
}

export function emptyToUndefined(value: string): string | undefined {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : undefined;
}
