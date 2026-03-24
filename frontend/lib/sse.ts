import { AgentEvent } from "@/types/agent";

type StreamOptions = {
  url: string;
  body: unknown;
  onEvent: (event: AgentEvent) => void;
};

export async function streamAgentEvents({ url, body, onEvent }: StreamOptions) {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!response.ok || !response.body) {
    throw new Error("Failed to start stream.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";

    for (const frame of frames) {
      const eventLine = frame
        .split("\n")
        .find((line) => line.startsWith("event:"));
      const dataLine = frame
        .split("\n")
        .find((line) => line.startsWith("data:"));

      if (eventLine?.includes("agent_event") && dataLine) {
        onEvent(JSON.parse(dataLine.slice(5).trim()) as AgentEvent);
      }
    }
  }
}
