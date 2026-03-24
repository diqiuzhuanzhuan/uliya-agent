export type Role = "user" | "assistant";

export type Message = {
  id: string;
  role: Role;
  content: string;
};

export type AgentEvent =
  | { type: "run_started"; thread_id: string; message: string }
  | { type: "plan_created"; plan: TraceStep[] }
  | { type: "memory_snapshot"; items: MemoryItem[] }
  | { type: "retrieval_result"; items: UploadItem[] }
  | { type: "step_started"; step: TraceStep }
  | { type: "tool_call"; tool_name: string; arguments: Record<string, unknown> }
  | { type: "tool_result"; tool_name: string; arguments: Record<string, unknown>; output: string }
  | { type: "step_completed"; step: TraceStep }
  | { type: "answer_delta"; delta: string }
  | { type: "run_completed"; answer: string; memories: MemoryItem[] };

export type TraceStep = {
  id: string;
  title: string;
  kind: string;
  detail?: string;
  tool_name?: string;
  arguments?: Record<string, unknown>;
};

export type MemoryItem = {
  role: string;
  content: string;
  created_at: string;
};

export type AgentConfig = {
  use_real_deepagents: boolean;
  deepagents_model: string;
  selected_tools: string[];
  memory_enabled: boolean;
  retrieval_enabled: boolean;
  skills_prompt: string;
};

export type ThreadSummary = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type TraceRecord = {
  id: number;
  thread_id: string;
  run_id: string;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: string;
};

export type UploadItem = {
  id: number;
  thread_id: string | null;
  filename: string;
  stored_path: string;
  preview: string;
  created_at: string;
};
