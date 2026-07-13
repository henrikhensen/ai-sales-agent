interface JsonViewerProps {
  data: unknown;
}

export function JsonViewer({ data }: JsonViewerProps) {
  return (
    <pre className="max-h-96 overflow-auto rounded-none border border-white/10 bg-black/30 p-4 text-xs leading-relaxed text-muted/75">
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}
