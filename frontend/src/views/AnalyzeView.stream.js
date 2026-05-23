export function createAnalyzeStreamParser(onEvent) {
  let buffer = '';
  let done = false;

  const processLine = (line) => {
    if (done || !line.startsWith('data: ')) return;

    const raw = line.slice(6).trim();
    if (!raw) return;

    if (raw === '[DONE]') {
      done = true;
      return;
    }

    try {
      onEvent(JSON.parse(raw));
    } catch {
      // Ignore malformed stream frames; the next valid event can still update the timeline.
    }
  };

  return {
    push(chunk) {
      if (done) return;

      buffer += chunk;
      const lines = buffer.split('\n');
      buffer = lines.pop() ?? '';
      lines.forEach(processLine);
    },
    flush() {
      if (buffer) {
        processLine(buffer);
        buffer = '';
      }
    },
    get done() {
      return done;
    },
  };
}
