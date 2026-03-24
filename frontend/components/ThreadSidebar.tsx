"use client";

import { ThreadSummary } from "@/types/agent";

type ThreadSidebarProps = {
  activeThreadId: string | null;
  items: ThreadSummary[];
  onCreateThread: () => void;
  onSelectThread: (threadId: string) => void;
};

export function ThreadSidebar({
  activeThreadId,
  items,
  onCreateThread,
  onSelectThread,
}: ThreadSidebarProps) {
  return (
    <section className="panel sidebar-panel">
      <div className="panel-header">
        <h2 className="panel-title">会话</h2>
        <p className="panel-subtitle">管理多线程任务，并随时切回历史上下文。</p>
      </div>

      <div className="sidebar-body">
        <button className="button button-secondary" onClick={onCreateThread} type="button">
          新建会话
        </button>

        <div className="thread-list">
          {items.length === 0 ? (
            <p className="trace-content">还没有会话。</p>
          ) : (
            items.map((item) => (
              <button
                key={item.id}
                className={`thread-item ${item.id === activeThreadId ? "active" : ""}`}
                onClick={() => onSelectThread(item.id)}
                type="button"
              >
                <strong>{item.title}</strong>
                <span>{new Date(item.updated_at).toLocaleString("zh-CN")}</span>
              </button>
            ))
          )}
        </div>
      </div>
    </section>
  );
}
