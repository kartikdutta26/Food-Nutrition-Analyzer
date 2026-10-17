import assert from 'node:assert/strict';
import test from 'node:test';
import { createRequestSequence } from './requestSequence.js';

test('only the latest started request is current', () => {
  const sequence = createRequestSequence();
  const firstRequest = sequence.next();

  assert.equal(sequence.isCurrent(firstRequest), true);

  const secondRequest = sequence.next();
  assert.equal(sequence.isCurrent(firstRequest), false);
  assert.equal(sequence.isCurrent(secondRequest), true);
});
