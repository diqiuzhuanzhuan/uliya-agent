"use client";

import { startTransition, useEffect, useState } from "react";

import { ChatPanel } from "@/components/ChatPanel";
import { ConfigPanel } from "@/components/ConfigPanel";
import { ThreadSidebar } from "@/components/ThreadSidebar";
import { TracePanel } from "@/components/TracePanel";
import { streamAgentEvents } from "@/lib/sse";
import {
  AgentConfig,
  AgentEvent,
  Message,
  ThreadSummary,
  TraceRecord,
  UploadItem,
} from "@/types/agent";


const backendBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

type TraceItem = {
  id: string;
  kind: string;
  content: string;
};

function createWelcomeMessage(): Message {
  return {
    id: crypto.randomUUID(),
    role: "assistant",
    content:
      "欢迎使用 Uliya Agent MVP。发送一条任务后，我会实时展示计划、工具调用、记忆和最终答案。",
  };
}

const defaultConfig: AgentConfig = {
  use_real_deepagents: false,
  deepagents_model: "gpt-4.1-mini",
  selected_tools: ["calculator", "web_search_mock", "file_reader_mock"],
  memory_enabled: true,
  retrieval_enabled: true,
  skills_prompt:
    "Future entry point for prompt packs, RAG policies, and reusable workflows.",
};

export default function HomePage() {
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [messages, setMessages] = useState<Message[]>([createWelcomeMessage()]);
  const [traceItems, setTraceItems] = useState<TraceItem[]>([]);
  const [config, setConfig] = useState<AgentConfig>(defaultConfig);
  const [threads, setThreads] = useState<ThreadSummary[]>([]);
  const [uploads, setUploads] = useState<UploadItem[]>([]);

  useEffect(() => {
    const boot = async () => {
      const [configResponse, threadsResponse] = await Promise.all([
        fetch(`${backendBaseUrl}/config`),
        fetch(`${backendBaseUrl}/threads`),
      ]);

      if (configResponse.ok) {
        const data = (await configResponse.json()) as { defaultConfig: AgentConfig };
        setConfig(data.defaultConfig);
      }

      if (threadsResponse.ok) {
        const data = (await threadsResponse.json()) as { items: ThreadSummary[] };
        setThreads(data.items);
        if (data.items[0]) {
          setActiveThreadId(data.items[0].id);
          return;
        }
      }

      await createThread();
    };

    void boot();
  }, []);

  useEffect(() => {
    if (!activeThreadId) {
      return;
    }

    const hydrateThread = async () => {
      const [messagesResponse, tracesResponse, uploadsResponse] = await Promise.all([
        fetch(`${backendBaseUrl}/threads/${activeThreadId}/messages`),
        fetch(`${backendBaseUrl}/threads/${activeThreadId}/traces`),
        fetch(`${backendBaseUrl}/uploads?thread_id=${activeThreadId}`),
      ]);

      if (messagesResponse.ok) {
        const data = (await messagesResponse.json()) as {
          items: Array<{ role: "user" | "assistant"; content: string; created_at: string }>;
        };
        setMessages(
          data.items.length
            ? data.items.map((item) => ({
                id: `${item.created_at}-${item.role}`,
                role: item.role,
                content: item.content,
              }))
            : [createWelcomeMessage()],
        );
      }

      if (tracesResponse.ok) {
        const data = (await tracesResponse.json()) as { items: TraceRecord[] };
        setTraceItems(
          data.items.map((item) => ({
            id: `${item.id}`,
            kind: item.event_type,
            content: JSON.stringify(item.payload, null, 2),
          })),
        );
      }

      if (uploadsResponse.ok) {
        const data = (await uploadsResponse.json()) as { items: UploadItem[] };
        setUploads(data.items);
      }
    };

    void hydrateThread();
  }, [activeThreadId]);

  const refreshThreads = async () => {
    const response = await fetch(`${backendBaseUrl}/threads`);
    if (!response.ok) {
      return;
    }
    const data = (await response.json()) as { items: ThreadSummary[] };
    setThreads(data.items);
  };

  const createThread = async () => {
    const response = await fetch(`${backendBaseUrl}/threads`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ title: "New thread" }),
    });

    if (!response.ok) {
      return;
    }

    const nextThread = (await response.json()) as ThreadSummary;
    startTransition(() => {
      setThreads((current) => [nextThread, ...current]);
      setActiveThreadId(nextThread.id);
      setMessages([createWelcomeMessage()]);
      setTraceItems([]);
      setUploads([]);
    });
  };

  const pushTrace = (kind: string, content: string) => {
    setTraceItems((current) => [
      {
        id: crypto.randomUUID(),
        kind,
        content,
      },
      ...current,
    ]);
  };

  const handleAgentEvent = (event: AgentEvent) => {
    switch (event.type) {
      case "run_started":
        pushTrace("run_started", `Thread ${event.thread_id}\n${event.message}`);
        setMessages((current) => [
          ...current,
          { id: crypto.randomUUID(), role: "assistant", content: "" },
        ]);
        break;
      case "plan_created":
        pushTrace(
          "plan_created",
          event.plan.map((step) => `${step.title} (${step.kind})`).join("\n"),
        );
        break;
      case "memory_snapshot":
        pushTrace(
          "memory_snapshot",
          event.items.length
            ? event.items.map((item) => `[${item.role}] ${item.content}`).join("\n")
            : "No memory items yet.",
        );
        break;
      case "retrieval_result":
        pushTrace(
          "retrieval_result",
          event.items.map((item) => `${item.filename}\n${item.preview}`).join("\n\n"),
        );
        break;
      case "step_started":
        pushTrace("step_started", event.step.title);
        break;
      case "tool_call":
        pushTrace(
          "tool_call",
          `${event.tool_name}\n${JSON.stringify(event.arguments, null, 2)}`,
        );
        break;
      case "tool_result":
        pushTrace("tool_result", `${event.tool_name}\n${event.output}`);
        break;
      case "step_completed":
        pushTrace("step_completed", event.step.title);
        break;
      case "answer_delta":
        setMessages((current) => {
          const next = [...current];
          const lastMessage = next[next.length - 1];
          if (lastMessage && lastMessage.role === "assistant") {
            lastMessage.content += event.delta;
          }
          return next;
        });
        break;
      case "run_completed":
        pushTrace("run_completed", "Agent execution completed.");
        setBusy(false);
        void refreshThreads();
        break;
    }
  };

  const handleSubmit = async () => {
    const content = draft.trim();
    if (!content || busy || !activeThreadId) {
      return;
    }

    setBusy(true);
    setDraft("");
    setMessages((current) => [
      ...current,
      { id: crypto.randomUUID(), role: "user", content },
    ]);

    try {
      await streamAgentEvents({
        url: `${backendBaseUrl}/chat/stream`,
        body: {
          thread_id: activeThreadId,
          message: content,
          config,
        },
        onEvent: handleAgentEvent,
      });
    } catch (error) {
      setBusy(false);
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: `Stream failed: ${(error as Error).message}`,
        },
      ]);
    }
  };

  const handleUpload = async (file: File) => {
    if (!activeThreadId) {
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${backendBaseUrl}/uploads?thread_id=${activeThreadId}`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      return;
    }

    const item = (await response.json()) as UploadItem;
    setUploads((current) => [item, ...current]);
  };

  const activeThread = threads.find((thread) => thread.id === activeThreadId) ?? null;

  return (
    <main className="shell">
      <div className="shell-grid">
        <ThreadSidebar
          activeThreadId={activeThreadId}
          items={threads}
          onCreateThread={() => void createThread()}
          onSelectThread={setActiveThreadId}
        />
        <ChatPanel
          draft={draft}
          messages={messages}
          busy={busy}
          threadTitle={activeThread?.title ?? ""}
          onDraftChange={setDraft}
          onSubmit={handleSubmit}
        />
        <div className="right-column">
          <TracePanel items={traceItems} />
          <ConfigPanel
            busy={busy}
            config={config}
            uploads={uploads}
            onChange={setConfig}
            onUpload={handleUpload}
          />
        </div>
      </div>
    </main>
  );
}
