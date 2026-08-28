/** System status, and the model switch.
 *
 *  The brief asks for the selected provider to be visible. Visible is the floor:
 *  an evaluator comparing a local model against a cloud one should be able to
 *  do it without editing `.env` and restarting, so the provider rows are also
 *  the control.
 *
 *  Only providers that are actually reachable can be selected. A provider with
 *  no key is shown, greyed, with the reason - hiding it would make the model
 *  toggle look narrower than it is, and disabling it without saying why is
 *  the kind of dead end that wastes ten minutes.
 *
 *  "Auto" is the default and defers to `LLM_FALLBACK_CHAIN`, so the fallback
 *  behaviour stays the norm rather than something you have to opt back into.
 */

import { useState } from "react";
import type { Health, ProviderName } from "../types";

interface Props {
  health: Health | null;
  /** null = follow the server's configured chain. */
  override: ProviderName | null;
  onSelect: (provider: ProviderName | null) => void;
  onRefresh: () => void;
}

export function StatusBar({ health, override, onSelect, onRefresh }: Props) {
  const [open, setOpen] = useState(false);

  if (!health) {
    return (
      <div className="status status--unknown">
        <span className="status__dot" aria-hidden="true" />
        <span>Connecting…</span>
      </div>
    );
  }

  const active = health.providers.find((p) => p.active);
  const shown = override
    ? health.providers.find((p) => p.name === override)
    : active;

  const label =
    health.status === "ok"
      ? "All systems ready"
      : health.status === "degraded"
        ? "Running degraded"
        : "Not ready";

  return (
    <div className="status-wrap">
      <button
        className={`status status--${health.status}`}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-label={`System status: ${label}. Model: ${shown?.name ?? "auto"}. Open to change.`}
      >
        <span className="status__dot" aria-hidden="true" />
        <span className="status__provider">
          {shown ? `${shown.name} · ${shown.model}` : health.active_provider}
        </span>
        {override && <span className="status__pinned">pinned</span>}
        <span className="status__caret" aria-hidden="true">
          ▾
        </span>
      </button>

      {open && (
        <div className="status__panel" role="dialog" aria-label="System status">
          <div className="status__row">
            <strong>{label}</strong>
            <button className="link-button" onClick={onRefresh}>
              Refresh
            </button>
          </div>

          {health.checks.length > 0 && (
            <ul className="status__checks">
              {health.checks.map((check) => (
                <li key={check}>{check}</li>
              ))}
            </ul>
          )}

          <h4 className="status__heading">Model</h4>
          <div className="status__models" role="radiogroup" aria-label="Model provider">
            <button
              role="radio"
              aria-checked={override === null}
              className={`model-option ${override === null ? "is-active" : ""}`}
              onClick={() => onSelect(null)}
            >
              <span className="model-option__name">Auto</span>
              <span className="model-option__detail">
                Follow the configured chain: {health.fallback_chain.join(" → ")}
              </span>
            </button>

            {health.providers.map((provider) => {
              const selectable = provider.configured && provider.reachable;
              const selected = override === provider.name;
              return (
                <button
                  key={provider.name}
                  role="radio"
                  aria-checked={selected}
                  disabled={!selectable}
                  title={
                    selectable
                      ? `Send the next message to ${provider.name}`
                      : provider.detail || "Not available"
                  }
                  className={`model-option ${selected ? "is-active" : ""} ${
                    selectable ? "" : "is-disabled"
                  }`}
                  onClick={() => selectable && onSelect(provider.name as ProviderName)}
                >
                  <span className="model-option__name">
                    {provider.name}
                    {provider.active && <em> · default</em>}
                  </span>
                  <span className="model-option__detail">{provider.model}</span>
                  {!selectable && provider.detail && (
                    <span className="model-option__why">{provider.detail}</span>
                  )}
                </button>
              );
            })}
          </div>

          {override && (
            <p className="status__line status__line--muted">
              Pinned to <strong>{override}</strong>. A pinned provider bypasses the
              fallback chain, so you see its own errors rather than a silent
              substitution.
            </p>
          )}

          <h4 className="status__heading">Knowledge base</h4>
          <p className="status__line">
            {health.corpus.documents} sources ({health.corpus.podcasts} episodes,{" "}
            {health.corpus.newsletters} posts) · {health.corpus.chunks} passages ·{" "}
            {health.corpus.embedded_chunks > 0
              ? "hybrid search"
              : "lexical search only"}
          </p>

          <p className="status__line status__line--muted">
            Database: {health.database ? "connected" : "unreachable"} · v
            {health.version}
          </p>
        </div>
      )}
    </div>
  );
}
