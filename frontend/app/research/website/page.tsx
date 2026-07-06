"use client";

import { useState } from "react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { ApiError, researchWebsite } from "@/lib/api";
import type { WebsiteResearchResponse } from "@/lib/types";

const MAX_PAGES_OPTIONS = [
  { value: "1", label: "1 Seite" },
  { value: "2", label: "2 Seiten" },
  { value: "3", label: "3 Seiten" },
];

export default function WebsiteResearchPage() {
  const [url, setUrl] = useState("");
  const [maxPages, setMaxPages] = useState("1");
  const [includeSameDomainLinks, setIncludeSameDomainLinks] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<WebsiteResearchResponse | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await researchWebsite({
        url: url.trim(),
        max_pages: Number(maxPages),
        include_same_domain_links: includeSameDomainLinks,
      });
      setResult(response);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <RequireAuth>
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Website Research</h1>
          <p className="mt-1 text-sm text-slate-600">
            Ruft eine öffentlich zugängliche Website ab und extrahiert daraus
            lesbaren Text — als eigenständiges Analysewerkzeug, unabhängig von
            den KI-Agenten.
          </p>
        </div>

        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          <ul className="list-inside list-disc space-y-1">
            <li>Website Research ruft nur die vom Nutzer eingegebene öffentliche URL ab.</li>
            <li>Es findet kein LLM Call statt.</li>
            <li>Es entstehen keine KI-API-Kosten.</li>
            <li>Kein LinkedIn Scraping.</li>
            <li>Keine automatische Kontaktaufnahme.</li>
          </ul>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card title="Eingaben">
            <form className="space-y-4" onSubmit={handleSubmit}>
              <Input
                label="Website-URL *"
                type="url"
                required
                placeholder="https://acme.example.com"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                hint="Nur öffentlich erreichbare http(s)-URLs. Localhost, private und interne Adressen werden vom Backend abgelehnt."
              />
              <Select
                label="Max. Seiten"
                value={maxPages}
                options={MAX_PAGES_OPTIONS}
                onChange={(e) => setMaxPages(e.target.value)}
                hint="Reserviert für ein späteres Crawling verlinkter Seiten — in dieser Phase wird immer nur die angegebene URL abgerufen."
              />
              <label className="flex items-start gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  className="mt-0.5 h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                  checked={includeSameDomainLinks}
                  onChange={(e) => setIncludeSameDomainLinks(e.target.checked)}
                />
                <span>
                  Links derselben Domain einbeziehen
                  <span className="block text-xs text-slate-500">
                    Reserviert für später, hat aktuell keine Wirkung — es wird
                    trotzdem nur die angegebene URL abgerufen.
                  </span>
                </span>
              </label>
              <Button type="submit" loading={loading}>
                Website analysieren
              </Button>
            </form>
          </Card>

          <Card title="Ergebnis">
            {loading ? (
              <p className="text-sm text-slate-500">Website wird abgerufen…</p>
            ) : error ? (
              <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                {error}
              </div>
            ) : result ? (
              <div className="space-y-4">
                <dl className="space-y-2 text-sm">
                  <div className="flex justify-between gap-4">
                    <dt className="text-slate-500">URL</dt>
                    <dd className="break-all text-right font-mono text-xs text-slate-900">
                      {result.url}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt className="text-slate-500">Final URL</dt>
                    <dd className="break-all text-right font-mono text-xs text-slate-900">
                      {result.final_url}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt className="text-slate-500">Domain</dt>
                    <dd className="font-mono text-slate-900">{result.domain}</dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt className="text-slate-500">Title</dt>
                    <dd className="text-right text-slate-900">{result.title ?? "—"}</dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt className="text-slate-500">Meta Description</dt>
                    <dd className="text-right text-slate-900">
                      {result.meta_description ?? "—"}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt className="text-slate-500">Text Length</dt>
                    <dd className="text-slate-900">{result.text_length} Zeichen</dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt className="text-slate-500">Pages Fetched</dt>
                    <dd className="text-slate-900">{result.pages_fetched}</dd>
                  </div>
                </dl>

                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                    Sources Used
                  </p>
                  <ul className="mt-1 space-y-1">
                    {result.sources_used.map((source) => (
                      <li key={source} className="break-all font-mono text-xs text-slate-700">
                        {source}
                      </li>
                    ))}
                  </ul>
                </div>

                {result.warnings.length > 0 ? (
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                      Warnings
                    </p>
                    <div className="mt-1 flex flex-col gap-1">
                      {result.warnings.map((warning) => (
                        <Badge key={warning} tone="warning">
                          {warning}
                        </Badge>
                      ))}
                    </div>
                  </div>
                ) : null}

                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                    Extracted Text
                  </p>
                  <div className="mt-1 max-h-96 overflow-y-auto whitespace-pre-wrap rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
                    {result.extracted_text || "Kein Text extrahiert."}
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-sm text-slate-500">Noch keine Website analysiert.</p>
            )}
          </Card>
        </div>
      </div>
    </RequireAuth>
  );
}
