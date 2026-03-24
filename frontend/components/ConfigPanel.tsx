"use client";

import { UploadsPanel } from "@/components/UploadsPanel";
import { AgentConfig, UploadItem } from "@/types/agent";

const TOOLS = ["calculator", "web_search_mock", "file_reader_mock"];

type ConfigPanelProps = {
  busy: boolean;
  config: AgentConfig;
  uploads: UploadItem[];
  onChange: (next: AgentConfig) => void;
  onUpload: (file: File) => void;
};

export function ConfigPanel({
  busy,
  config,
  uploads,
  onChange,
  onUpload,
}: ConfigPanelProps) {
  const toggleTool = (tool: string) => {
    const nextTools = config.selected_tools.includes(tool)
      ? config.selected_tools.filter((item) => item !== tool)
      : [...config.selected_tools, tool];

    onChange({ ...config, selected_tools: nextTools });
  };

  return (
    <section className="panel config-panel">
      <div className="panel-header">
        <h2 className="panel-title">配置区</h2>
        <p className="panel-subtitle">
          先保留一个清晰的扩展入口，后续可以把 RAG、上传、认证和更多工具接进来。
        </p>
      </div>

      <div className="config-body">
        <div className="config-group">
          <span className="config-label">工具开关</span>
          <div className="tag-row">
            {TOOLS.map((tool) => (
              <button
                key={tool}
                className={`tag ${config.selected_tools.includes(tool) ? "active" : ""}`}
                onClick={() => toggleTool(tool)}
                type="button"
              >
                {tool}
              </button>
            ))}
          </div>
        </div>

        <div className="config-group">
          <label className="checkbox-row">
            <input
              checked={config.memory_enabled}
              onChange={(event) =>
                onChange({ ...config, memory_enabled: event.target.checked })
              }
              type="checkbox"
            />
            启用 SQLite 基础记忆
          </label>
          <label className="checkbox-row">
            <input
              checked={config.use_real_deepagents}
              onChange={(event) =>
                onChange({ ...config, use_real_deepagents: event.target.checked })
              }
              type="checkbox"
            />
            预留真实 Deep Agents SDK 切换位
          </label>
          <label className="checkbox-row">
            <input
              checked={config.retrieval_enabled}
              onChange={(event) =>
                onChange({ ...config, retrieval_enabled: event.target.checked })
              }
              type="checkbox"
            />
            启用上传资料检索入口
          </label>
        </div>

        <div className="config-group">
          <label className="config-label" htmlFor="deepagents-model">
            Deep Agents 模型
          </label>
          <input
            className="input"
            id="deepagents-model"
            value={config.deepagents_model}
            onChange={(event) =>
              onChange({ ...config, deepagents_model: event.target.value })
            }
            placeholder="gpt-4.1-mini"
          />
        </div>

        <div className="config-group">
          <label className="config-label" htmlFor="skills-prompt">
            Skills 扩展入口
          </label>
          <textarea
            className="textarea"
            id="skills-prompt"
            value={config.skills_prompt}
            onChange={(event) =>
              onChange({ ...config, skills_prompt: event.target.value })
            }
            placeholder="例如：优先使用产品需求分析 skill。"
          />
        </div>

        <UploadsPanel busy={busy} items={uploads} onUpload={onUpload} />
      </div>
    </section>
  );
}
