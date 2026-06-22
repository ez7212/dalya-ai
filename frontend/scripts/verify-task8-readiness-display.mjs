import ts from 'typescript'
import { mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

const repoRoot = resolve(import.meta.dirname, '../..')
const frontendRoot = resolve(repoRoot, 'frontend')
const sourcePath = resolve(frontendRoot, 'src/components/readiness/deal-readiness.ts')
const compiledPath = resolve(repoRoot, '.omo/ulw-loop/evidence/task8-deal-readiness-presenter.mjs')
const edgeArtifactPath = resolve(repoRoot, '.omo/ulw-loop/evidence/task8-C002-readiness-empty-edge.txt')

function assertCheck(condition, label) {
  if (!condition) {
    throw new Error(label)
  }
  return { label, passed: true }
}

function compilePresenter() {
  const source = readFileSync(sourcePath, 'utf8')
  const output = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2022,
      strict: true,
    },
    fileName: sourcePath,
    reportDiagnostics: true,
  })

  const diagnostics = output.diagnostics ?? []
  if (diagnostics.length > 0) {
    const rendered = diagnostics.map((diagnostic) => ts.flattenDiagnosticMessageText(diagnostic.messageText, '\n')).join('\n')
    throw new Error(`Presenter transpilation diagnostics:\n${rendered}`)
  }

  mkdirSync(dirname(compiledPath), { recursive: true })
  writeFileSync(compiledPath, output.outputText)
}

compilePresenter()

const {
  buildDealReadinessDisplay,
  labelFromKey,
  normalizeDealReadiness,
} = await import(pathToFileURL(compiledPath).href)

const completePayload = {
  stage: 'viewing_ready',
  missing_fields: ['other_agent_status'],
  next_best_action: 'prepare_viewing_brief',
  next_best_action_reason: 'Viewing window is confirmed; validate access notes before proposing slots.',
  score: 82,
  priority_band: 'high',
  present_fields: {
    budget_max_aed: 2_500_000,
    financing: 'cash',
    viewing_availability: 'Saturday afternoon',
  },
}

const malformedPayload = {
  stage: { invalid: true },
  missing_fields: ['purpose', 123, '', 'viewing_availability'],
  next_best_action: 'ask_next_readiness_question',
  next_best_action_reason: ['not', 'text'],
  score: Number.NaN,
  priority_band: null,
  present_fields: ['wrong-shape'],
}

const complete = normalizeDealReadiness(completePayload)
const completeDisplay = buildDealReadinessDisplay(complete)
const malformed = normalizeDealReadiness(malformedPayload)
const malformedDisplay = buildDealReadinessDisplay(malformed)
const empty = normalizeDealReadiness(null)

const checks = [
  assertCheck(complete?.stage === 'viewing_ready', 'normal payload stage is preserved'),
  assertCheck(complete?.presentFields.budget_max_aed === 2_500_000, 'present_fields object is preserved as a record'),
  assertCheck(completeDisplay?.headline === 'Viewing ready · High priority · 82/100', 'display headline formats stage, priority, and score'),
  assertCheck(completeDisplay?.action === 'Prepare viewing brief', 'display action formats next best action'),
  assertCheck(completeDisplay?.reason === completePayload.next_best_action_reason, 'display reason uses next best action reason'),
  assertCheck(completeDisplay?.missingFields.join(', ') === 'Other agent status', 'display missing fields are formatted'),
  assertCheck(empty === null, 'null readiness metadata returns no summary'),
  assertCheck(malformed?.stage === null, 'malformed object stage is ignored'),
  assertCheck(malformed?.score === null, 'non-finite score is ignored'),
  assertCheck(Object.keys(malformed?.presentFields ?? {}).length === 0, 'array-shaped present_fields is ignored'),
  assertCheck(malformedDisplay?.action === 'Ask next readiness question', 'valid action survives malformed adjacent fields'),
  assertCheck(malformedDisplay?.reason === null, 'malformed reason is not stringified'),
  assertCheck(malformedDisplay?.missingFields.join(', ') === 'Purpose, Viewing availability', 'mixed missing_fields list is narrowed'),
  assertCheck(labelFromKey('ready_to_view') === 'Ready to view', 'label formatter is deterministic'),
]

const artifact = {
  scenario: 'Task 8 shared readiness presenter edge handling',
  invocation: 'cd frontend && node scripts/verify-task8-readiness-display.mjs',
  binaryObservable: {
    presenterChecks: checks.length,
    presentFieldsRecordPreserved: true,
    malformedMetadataNarrowed: true,
  },
  checks,
  artifacts: {
    compiledPresenter: compiledPath,
    edge: edgeArtifactPath,
  },
}

mkdirSync(dirname(edgeArtifactPath), { recursive: true })
writeFileSync(edgeArtifactPath, `${JSON.stringify({ ...artifact, criterion: 'C002 edge malformed/null metadata' }, null, 2)}\n`)
rmSync(compiledPath, { force: true })
console.log(JSON.stringify(artifact, null, 2))
