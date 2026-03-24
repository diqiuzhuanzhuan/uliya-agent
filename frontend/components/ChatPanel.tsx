"use client";

import { FormEvent } from "react";

import { Message } from "@/types/agent";

type ChatPanelProps = {
  draft: string;
  messages: Message[];
  busy: boolean;
  threadTitle: string;
  onDraftChange: (value: string) => void;
  onSubmit: () => void;
};

export function ChatPanel({
  draft,
  messages,
  busy,
  threadTitle,
  onDraftChange,
  onSubmit,
}: ChatPanelProps) {
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit();
  };

  return (
    <section className="panel chat-panel">
      <div className="panel-header">
        <h1 className="panel-title">Universal Agent Console</h1>
        <p className="panel-subtitle">
          {threadTitle || "面向通用 Agent Web App 的 MVP，实时展示对话、计划、工具调用与最终答案。"}
        </p>
      </div>

      <div className="messages">
        {messages.map((message) => (
          <article key={message.id} className={`message ${message.role}`}>
            {message.content}
          </article>
        ))}
      </div>

      <form className="composer" onSubmit={handleSubmit}>
        <textarea
          value={draft}
          onChange={(event) => onDraftChange(event.target.value)}
          placeholder="输入任务，例如：帮我规划一个可扩展的 agent 系统，并顺便计算 24*(5+3)。"
        />

        <div className="toolbar">
          <span className="status-line">
            {busy ? "Agent 正在流式执行..." : "后端将通过 SSE 推送轨迹与答案。"}
          </span>
          <button className="button" type="submit" disabled={busy || !draft.trim()}>
            {busy ? "运行中" : "发送"}
          </button>
        </div>
      </form>
    </section>
  );
}
