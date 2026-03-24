"use client";

type TraceItem = {
  id: string;
  kind: string;
  content: string;
};

type TracePanelProps = {
  items: TraceItem[];
};

export function TracePanel({ items }: TracePanelProps) {
  return (
    <section className="panel trace-panel">
      <div className="panel-header">
        <h2 className="panel-title">任务轨迹</h2>
        <p className="panel-subtitle">
          这里显示 Deep Agent 风格的 plan、steps、tool calls 与 memory snapshot。
        </p>
      </div>

      <div className="trace-list">
        {items.length === 0 ? (
          <p className="trace-content">等待一次运行开始。</p>
        ) : (
          items.map((item) => (
            <article className="trace-item" key={item.id}>
              <span className="trace-kind">{item.kind}</span>
              <p className="trace-content">{item.content}</p>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
