export interface AnalyzeStreamEvent {
  step?: string;
  status?: string;
  label?: string;
  data?: Record<string, unknown>;
}

export interface AnalyzeStreamParser {
  push(chunk: string): void;
  flush(): void;
  readonly done: boolean;
}

export function createAnalyzeStreamParser(
  onEvent: (event: AnalyzeStreamEvent) => void,
): AnalyzeStreamParser;
