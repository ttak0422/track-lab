export const meta = {
  name: 'watch-weekly-high',
  description: 'Weekly high review: excavate hidden assumptions, stress-test due ones, forecast with falsifiers',
  phases: [
    { title: 'Excavate', detail: '現在の見立てが暗黙に依存する前提の洗い出し' },
    { title: 'Stress', detail: '要点検の前提ごとに独立Web照合と崩壊シナリオ' },
    { title: 'Forecast', detail: '過去傾向からの予想(反証条件つき)' },
    { title: 'Critic', detail: '完全性チェック' },
  ],
}

// args: { topic, today, stance, week_digest, assumptions: [{text, checked, trigger, due}],
//         concerns?: [string], maxStress?: number }
if (!args || !args.topic || !args.today || !args.stance) {
  throw new Error('args.topic, args.today, args.stance are required')
}

const ASSUMPTIONS = args.assumptions || []
const MAX_STRESS = args.maxStress || 6

const WEB = `最初に ToolSearch で "select:WebSearch,WebFetch" を実行してツールを読み込むこと。今日は${args.today}。すべての事実に出典URLを付け、確証が持てないものは confidence を明示する。`

phase('Excavate')
const excavated = await agent(`あなたは敵対的な前提発掘エージェント。対象テーマ: ${args.topic}。
以下の「現在の見立て」と「今週の材料」が暗黙に依存している前提のうち、既知の前提レジスタに**まだ挙がっていないもの**を列挙せよ。
「この見立てが正しくあるためには何が真である必要があるか」を問い、自明視されているもの(制度・因果関係・データの信頼性・関係者の行動原理)ほど疑うこと。Webは使わなくてよい。
## 現在の見立て
${args.stance}
## 今週の材料
${args.week_digest || '(なし)'}
## 既知の前提レジスタ
${JSON.stringify(ASSUMPTIONS.map((a) => a.text))}`, {
  label: 'excavate',
  phase: 'Excavate',
  schema: {
    type: 'object',
    properties: {
      hidden: {
        type: 'array',
        items: {
          type: 'object',
          properties: {
            text: { type: 'string', description: '前提を一文で' },
            why_hidden: { type: 'string', description: 'なぜ自明視されてきたか' },
            risk: { type: 'string', enum: ['high', 'medium', 'low'], description: '崩れたときの影響度' },
            trigger: { type: 'string', description: '崩壊を示すシグナル' },
          },
          required: ['text', 'risk'],
          additionalProperties: false,
        },
      },
    },
    required: ['hidden'],
  },
})

phase('Stress')
const due = ASSUMPTIONS.filter((a) => a.due)
const fresh = ((excavated && excavated.hidden) || []).filter((h) => h.risk === 'high')
const targets = due
  .map((a) => ({ text: a.text, trigger: a.trigger || '', origin: 'register' }))
  .concat(fresh.map((h) => ({ text: h.text, trigger: h.trigger || '', origin: 'excavated' })))
  .slice(0, MAX_STRESS)
if (targets.length < due.length + fresh.length) {
  log(`stress対象を${MAX_STRESS}件に打ち切り(全${due.length + fresh.length}件)`)
}

const STRESS = {
  type: 'object',
  properties: {
    holds: { type: 'string', enum: ['holds', 'weakening', 'broken', 'unverifiable'] },
    evidence: { type: 'string', description: '現時点の根拠(出典URL含む)' },
    break_scenario: { type: 'string', description: '崩れた場合に何が起きるか' },
    response: { type: 'string', description: '崩れた場合にどう動くべきか' },
    next_trigger: { type: 'string', description: '再点検のトリガー(更新版)' },
  },
  required: ['holds', 'evidence', 'break_scenario', 'response'],
}

const stressed = await parallel(targets.map((t, i) => () =>
  agent(`あなたは前提の検証エージェント。${WEB}
対象テーマ: ${args.topic}。次の前提が現時点でも成り立つかを独立ソースで点検し、崩れた場合のシナリオと推奨対応まで出せ。
前提: ${t.text}
既知の崩壊トリガー: ${t.trigger || '(未定義)'}`, { label: `stress:${i + 1}`, phase: 'Stress', schema: STRESS })
    .then((v) => v && { ...t, ...v })))

phase('Forecast')
const stressDigest = stressed.filter(Boolean)
  .map((s) => `- [${s.holds}] ${s.text}: ${s.break_scenario}`).join('\n')
const forecast = await agent(`あなたは予想エージェント。${WEB}
対象テーマ: ${args.topic}。今週の材料・前提の点検結果・過去の傾向から、来週〜数カ月の変化予想を出せ。
**反証条件のない予想は出さないこと** — 各予想に「何が起きたらこの予想を捨てるか」を必ず付ける。過去の類似局面が根拠にあるなら明示する。
## 見立て
${args.stance}
## 今週の材料
${args.week_digest || '(なし)'}
## 前提の点検結果
${stressDigest || '(なし)'}`, {
  label: 'forecast',
  phase: 'Forecast',
  schema: {
    type: 'object',
    properties: {
      forecasts: {
        type: 'array',
        items: {
          type: 'object',
          properties: {
            claim: { type: 'string' },
            horizon: { type: 'string', description: '来週 / 1カ月 / 四半期 など' },
            basis: { type: 'string', description: '根拠(過去の類似局面があれば明示)' },
            falsifier: { type: 'string', description: '何が起きたらこの予想を捨てるか' },
            confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
          },
          required: ['claim', 'horizon', 'basis', 'falsifier'],
          additionalProperties: false,
        },
      },
    },
    required: ['forecasts'],
  },
})

phase('Critic')
const critic = await agent(`あなたは完全性チェッカー。テーマ「${args.topic}」の週次レビュー(high)の成果物を点検し、欠けている観点・矛盾・「反証条件が実質的に検証不能な予想」を挙げよ。
## 発掘された暗黙の前提
${JSON.stringify((excavated && excavated.hidden) || [])}
## 前提の点検結果
${stressDigest || '(なし)'}
## 予想
${JSON.stringify((forecast && forecast.forecasts) || [])}`, {
  label: 'critic',
  phase: 'Critic',
  schema: {
    type: 'object',
    properties: {
      missing: { type: 'array', items: { type: 'string' } },
      contradictions: { type: 'array', items: { type: 'string' } },
      weak_falsifiers: { type: 'array', items: { type: 'string' } },
      overall: { type: 'string' },
    },
    required: ['missing', 'overall'],
  },
})

return { excavated, stressed: stressDigest ? stressed.filter(Boolean) : [], forecast, critic }
