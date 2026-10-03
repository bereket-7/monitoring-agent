"use client";

import { useState, type FormEvent } from "react";

import { agentChat } from "@/lib/api";
import type { AgentChatResponse, ToolCallRecord } from "@/lib/types";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  confidence?: string;
  toolCalls?: ToolCallRecord[];
}

function toolLabel(call: ToolCallRecord): string {
  const mark =
    call.status === "success" ? "✓" : call.status === "denied" ? "✕" : "!";
  const human = call.name.replaceAll("_", " ");
  if (call.status === "success") {
    return `${mark} ${human}`;
  }
  return `${mark} ${human} (${call.status}${call.error ? `: ${call.error}` : ""})`;
}

export function AgentChat({
  dashboardUid,
  timeFrom,
  timeTo,
  filters,
  onResponse,
}: {
  dashboardUid: string;
  timeFrom: string;
  timeTo: string;
  filters: Record<string, string>;
  onResponse: (response: AgentChatResponse) => void;
}) {
  const [message, setMessage] = useState("Is the success rate on this dashboard correct?");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = message.trim();
    if (!trimmed || !dashboardUid || busy) {
      return;
    }

    setBusy(true);
    setError(null);
    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);

    try {
      const response = await agentChat({
        message: trimmed,
        dashboard_uid: dashboardUid,
        context: {
          time_range: { from: timeFrom, to: timeTo },
          filters,
        },
      });
      onResponse(response);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response.answer,
          confidence: response.confidence,
          toolCalls: response.tool_calls,
        },
      ]);
      setMessage("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Agent request failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="chat-panel" aria-labelledby="chat-title">
      <h2 id="chat-title" className="panel-title">
        AI Agent
      </h2>

      <ul className="message-list" aria-live="polite">
        {messages.length === 0 ? (
          <li className="empty">
            Ask a dashboard question. Tool progress and evidence-backed answers appear here — not
            hidden chain-of-thought.
          </li>
        ) : (
          messages.map((item, index) => (
            <li key={index} className="message" data-role={item.role}>
              <strong>{item.role === "user" ? "You" : "Agent"}</strong>
              <div>{item.content}</div>
              {item.confidence ? (
                <div className="empty">Confidence: {item.confidence} (evidence coverage)</div>
              ) : null}
              {item.toolCalls && item.toolCalls.length > 0 ? (
                <ul className="tool-list" aria-label="Tool progress">
                  <li>Analyzing dashboard...</li>
                  {item.toolCalls.map((call, callIndex) => (
                    <li key={`${call.name}-${callIndex}`} data-status={call.status}>
                      {toolLabel(call)}
                    </li>
                  ))}
                </ul>
              ) : null}
            </li>
          ))
        )}
      </ul>

      {error ? (
        <p className="status-line" data-tone="error" role="alert">
          {error}
        </p>
      ) : null}

      <form className="chat-form" onSubmit={onSubmit}>
        <label className="field" htmlFor="agent-message">
          <span className="panel-title" style={{ margin: 0 }}>
            Ask a question
          </span>
          <textarea
            id="agent-message"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            disabled={busy || !dashboardUid}
            placeholder={
              dashboardUid
                ? "Is the success rate on this dashboard correct?"
                : "Select a dashboard first"
            }
          />
        </label>
        <button className="primary-btn" type="submit" disabled={busy || !dashboardUid}>
          {busy ? "Investigating…" : "Ask"}
        </button>
      </form>
    </section>
  );
}
