export type SseHandler = (event: string, data: Record<string, unknown>) => void;

/**
 * Parse standard SSE blocks (event + data lines) from a fetch Response body.
 */
export async function consumeSse(response: Response, onEvent: SseHandler): Promise<void> {
  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("No response body");
  }
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const block = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);

      let eventName = "message";
      const dataParts: string[] = [];
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) {
          eventName = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          dataParts.push(line.slice(5).trimStart());
        }
      }
      const dataStr = dataParts.join("\n");
      if (!dataStr) continue;
      try {
        onEvent(eventName, JSON.parse(dataStr) as Record<string, unknown>);
      } catch {
        onEvent(eventName, { raw: dataStr });
      }
    }
  }
}
