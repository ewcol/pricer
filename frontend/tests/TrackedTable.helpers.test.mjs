import test from 'node:test';
import assert from 'node:assert/strict';
import { driftLabel, formatTrackedDate, thumbnailAlt } from '../src/components/TrackedTable.helpers.js';

test('formatTrackedDate keeps tracked dates readable', () => {
  assert.equal(formatTrackedDate('2024-01-05T12:00:00Z'), 'Jan 5, 2024');
  assert.equal(formatTrackedDate('not-a-date'), 'not-a-date');
});

test('driftLabel formats tracked item drift cleanly', () => {
  assert.equal(driftLabel(0), '—');
  assert.equal(driftLabel(12.34), '+12.3%');
  assert.equal(driftLabel(-2.22), '-2.2%');
});

test('thumbnailAlt names tracked item thumbnails', () => {
  assert.equal(thumbnailAlt('Sony Walkman'), 'Thumbnail for Sony Walkman');
  assert.equal(thumbnailAlt(''), 'Tracked item thumbnail');
});
