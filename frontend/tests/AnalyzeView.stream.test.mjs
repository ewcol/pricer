import assert from 'node:assert/strict';
import test from 'node:test';
import { createAnalyzeStreamParser } from '../src/views/AnalyzeView.stream.js';

test('parses streamed SSE events across chunk boundaries', () => {
  const events = [];
  const parser = createAnalyzeStreamParser((event) => events.push(event));

  parser.push('data: {"step":"vision","status":"running","label":"Gem');
  parser.push('ini vision identification"}\n\ndata: {"step":"vision","status":"done"}\n\n');
  parser.push('data: [DONE]\n\n');

  assert.deepEqual(events, [
    { step: 'vision', status: 'running', label: 'Gemini vision identification' },
    { step: 'vision', status: 'done' },
  ]);
  assert.equal(parser.done, true);
});

test('ignores non-data lines and flushes the final buffered event', () => {
  const events = [];
  const parser = createAnalyzeStreamParser((event) => events.push(event));

  parser.push(': keepalive\n');
  parser.push('data: {broken}\n\n');
  parser.push('data: {"step":"prices","status":"running"}');
  parser.flush();

  assert.deepEqual(events, [
    { step: 'prices', status: 'running' },
  ]);
});
