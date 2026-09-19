// Offline contract check; mocks the Workflow runtime, not web research.
// Run: node scripts/check-research-workflows.mjs
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
async function run(file, args, responses) {
  const source = (await readFile(new URL(`../plugins/note/skills/${file}`, import.meta.url), 'utf8'))
    .replace('export const meta', 'const meta')
  const calls = [], logs = []
  const result = await new AsyncFunction('args', 'agent', 'phase', 'pipeline', 'parallel', 'log', source)(
    args,
    async (prompt, { label }) => {
      calls.push(label)
      assert.ok(Object.hasOwn(responses, label), `unexpected call: ${label}`)
      const value = responses[label]
      if (value instanceof Error) throw value
      return value
    },
    () => {},
    (items, first, second) => Promise.all(items.map(async (item) => second(await first(item), item))),
    (tasks) => Promise.all(tasks.map((task) => task())),
    (line) => logs.push(JSON.parse(line)),
  )
  assert.deepEqual(logs, result.execution.steps)
  assert.ok(Date.parse(result.execution.finished_at) >= Date.parse(result.execution.started_at))
  return { result, calls }
}

const news = 'track-news-analysis/workflow.js'
const watch = 'track-watch/weekly-workflow.js'
const found = { summary: 'Read source', facts: [], coverage: 'one source read' }
const critic = { missing: [{ topic: 'gap' }, { topic: 'later' }], overall: 'partial' }
const newsArgs = { event: 'fixture', today: '2026-09-19', lenses: ['a', 'b'].map((key) => ({ key, focus: key })) }

// Failed verification must retain the successful sweep; another failed sweep is visible.
const partial = await run(news, newsArgs, {
  'sweep:a': found, 'verify:a': new Error('verification timeout'),
  'sweep:b': null, critic, 'gap-filler': new Error('fetch failed'),
})
assert.deepEqual(partial.result.lenses, [{ lens: 'a', found, verify: null }])
assert.deepEqual(partial.result.execution.steps.filter((s) => s.status === 'failed').map((s) => s.id).sort(),
  ['gap-filler', 'sweep:b', 'verify:a'])
assert.ok(partial.result.execution.unreviewed.some((s) => s.id === 'verify:b'))
assert.equal(partial.result.filler, null)

// A zero limit must cause no gap-filler call; omitted claims remain explicit.
const limited = await run(news, { ...newsArgs, lenses: [newsArgs.lenses[0]], maxGapFills: 0 }, {
  'sweep:a': { ...found, facts: [{ claim: 'uncertain', confidence: 'low' }] },
  'verify:a': { checks: [], coverage: 'no selected claims' }, critic,
})
assert.ok(!limited.calls.includes('gap-filler'))
assert.equal(limited.result.execution.unreviewed.length, 3)
const failedCritic = await run(news, { ...newsArgs, lenses: [newsArgs.lenses[0]] }, {
  'sweep:a': found, 'verify:a': { checks: [] }, critic: null,
})
assert.ok(failedCritic.result.execution.unreviewed.some((s) => s.reason === 'critic failed'))

const watchArgs = { topic: 'fixture', today: '2026-09-19', stance: 'unknown', maxStress: 1,
  assumptions: [{ text: 'first', due: true }, { text: 'second', due: true }] }
const reviewed = await run(watch, watchArgs, {
  excavate: { hidden: [] }, 'stress:1': new Error('source unavailable'),
  forecast: { forecasts: [], coverage: 'insufficient evidence' }, critic: null,
})
assert.deepEqual(reviewed.result.stressed, [])
assert.equal(reviewed.result.execution.unreviewed[0].text, 'second')
assert.equal(reviewed.result.execution.steps.filter((s) => s.status === 'failed').length, 2)
const zero = await run(watch, { ...watchArgs, maxStress: 0 }, {
  excavate: null, forecast: { forecasts: [] }, critic: { missing: [], overall: 'partial' },
})
assert.ok(!zero.calls.some((label) => label.startsWith('stress:')))
assert.equal(zero.result.execution.unreviewed.length, 3)

const success = await run(watch, { ...watchArgs, assumptions: [watchArgs.assumptions[0]] }, {
  excavate: { hidden: [] }, 'stress:1': { holds: 'holds', evidence: 'fixture', break_scenario: 'change' },
  forecast: { forecasts: [] }, critic: { missing: [], overall: 'complete' },
})
assert.equal(success.result.stressed[0].text, 'first')
assert.ok(success.result.execution.steps.every((s) => s.status === 'succeeded'))
await assert.rejects(run(watch, { ...watchArgs, maxStress: -1 }, {}), /non-negative integer/)
await assert.rejects(run(news, { ...newsArgs, maxGapFills: 0.5 }, {}), /non-negative integer/)
console.log('Workflow checks passed: success, partial failure, null responses, limits, retained results.')
