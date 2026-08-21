export const meta = {
  name: 'news-multi-lens-research',
  description: 'ニュース事象を独立したレンズで調査し、主要な主張を検証し、欠落を見つける',
  phases: [
    { title: 'Sweep', detail: 'レンズごとに 1 体の Web 調査エージェント' },
    { title: 'Verify', detail: '各レンズを独立ソースと照合する敵対的な突き合わせ' },
    { title: 'Gaps', detail: '完全性チェッカー、その上位の欠落を埋める' },
  ],
}

// args: { event: string (required), today: string YYYY-MM-DD (required),
//         lenses?: [{key, focus}], maxGapFills?: number }
if (!args || !args.event || !args.today) {
  throw new Error('args.event and args.today are required')
}

const DEFAULT_LENSES = [
  { key: 'facts', focus: '事実関係・定量データ。何が・いつ・どの規模で起きたか。数値は一次報道から正確に。「最大」「初」等の形容の根拠を過去事例と比較して検証する。' },
  { key: 'domestic', focus: '国内要因。政策・政治・経済指標・世論など、事象の国内側の文脈と伏線(前1〜2週間)。' },
  { key: 'international', focus: '海外要因。関係国の動き・市場・地政学など、事象の国外側の文脈。同日の周辺国・関連市場の反応。' },
  { key: 'keyperson', focus: 'キーパーソンの発言・政策。日時つきタイムライン、正確な引用(原文+和訳)、発言媒体。事象そのものへの言及が確認できない場合はその非存在も記録。' },
  { key: 'aftermath', focus: '前後の推移。事象前後の日次データ(数値系列があれば daily_closes に)、その後の展開、専門家の分析・見通し、過去の類似事例との比較。' },
]

const LENSES = (args.lenses && args.lenses.length ? args.lenses : DEFAULT_LENSES)
const MAX_GAP_FILLS = args.maxGapFills || 3

const COMMON = `あなたはWeb調査エージェント。最初に ToolSearch で "select:WebSearch,WebFetch" を実行してツールを読み込むこと。今日は${args.today}。
対象事象: ${args.event}
依頼文に含まれる前提は検証対象であり、事実として引き継がないこと。
日本語と英語の両方で検索し、一次情報を優先する。すべての事実に出典URLを付ける。数値は正確に転記する。
確証が持てない情報は confidence を下げて明示する。
最終出力はStructuredOutputで返す。summaryは日本語で具体的・詳細に(数値・固有名詞・日付を含める)。`

const FACTS = {
  type: 'object',
  properties: {
    summary: { type: 'string', description: '日本語での詳細な要約。数値・固有名詞・日付を必ず含める' },
    facts: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          claim: { type: 'string', description: '一文の事実。数値は具体的に' },
          date: { type: 'string', description: 'YYYY-MM-DD' },
          source_url: { type: 'string' },
          source_name: { type: 'string' },
          confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
        },
        required: ['claim', 'source_url', 'confidence'],
        additionalProperties: false,
      },
    },
    quotes: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          who: { type: 'string' },
          when: { type: 'string' },
          quote_original: { type: 'string' },
          quote_ja: { type: 'string' },
          medium: { type: 'string' },
          source_url: { type: 'string' },
        },
        required: ['who', 'quote_ja', 'source_url'],
        additionalProperties: false,
      },
    },
    daily_closes: {
      type: 'array',
      description: '日次の数値系列が得られた場合のみ',
      items: {
        type: 'object',
        properties: {
          date: { type: 'string' },
          close: { type: 'number' },
          change: { type: 'number' },
          change_pct: { type: 'number' },
        },
        required: ['date'],
        additionalProperties: false,
      },
    },
  },
  required: ['summary', 'facts'],
}

const VERIFY = {
  type: 'object',
  properties: {
    checks: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          claim: { type: 'string' },
          verdict: { type: 'string', enum: ['confirmed', 'corrected', 'unverified', 'refuted'] },
          correction: { type: 'string', description: 'corrected/refuted の場合の正しい内容' },
          source_url: { type: 'string', description: '照合に使った独立ソース' },
        },
        required: ['claim', 'verdict'],
        additionalProperties: false,
      },
    },
    notes: { type: 'string' },
  },
  required: ['checks'],
}

phase('Sweep')
const lensResults = await pipeline(
  LENSES,
  (l) => agent(COMMON + `\nレンズ: ${l.focus}`, { label: 'sweep:' + l.key, phase: 'Sweep', schema: FACTS }),
  (found, l) => {
    if (!found) return null
    const keyFacts = (found.facts || []).filter((f) => f.confidence !== 'low').slice(0, 12)
    const keyQuotes = (found.quotes || []).slice(0, 5)
    return agent(`あなたは懐疑的な検証エージェント。最初に ToolSearch で "select:WebSearch,WebFetch" を実行してツールを読み込むこと。今日は${args.today}。
別の調査者が「${args.event}」について集めた以下の主張を、元の出典とは別の独立ソースで照合し、反証を試みよ。数値の食い違い、日付のずれ、引用の改変を特に疑うこと。確認できなければ unverified とする。
主張リスト:
${JSON.stringify(keyFacts, null, 1)}
引用リスト:
${JSON.stringify(keyQuotes, null, 1)}`, { label: 'verify:' + l.key, phase: 'Verify', schema: VERIFY })
      .then((v) => ({ lens: l.key, found, verify: v }))
  },
)

phase('Gaps')
const ok = lensResults.filter(Boolean)
const digest = ok.map((r) => `## ${r.lens}\n${r.found.summary}`).join('\n\n')
const critic = await agent(`あなたは完全性チェッカー。以下は「${args.event}」を複数レンズで調査した要約である。
多角的な分析noteを書くために欠けている観点・未回答の疑問・矛盾している記述を挙げよ。特に: 主因の一貫した説明ができるか、数値に矛盾はないか、時系列に穴はないか。
${digest}`, {
  label: 'critic',
  phase: 'Gaps',
  schema: {
    type: 'object',
    properties: {
      missing: {
        type: 'array',
        items: {
          type: 'object',
          properties: { topic: { type: 'string' }, why: { type: 'string' } },
          required: ['topic'],
          additionalProperties: false,
        },
      },
      contradictions: { type: 'array', items: { type: 'string' } },
      overall: { type: 'string' },
    },
    required: ['missing', 'overall'],
  },
})

let filler = null
if (critic && critic.missing && critic.missing.length > 0) {
  filler = await agent(COMMON + `
以下は調査の欠落として指摘された観点である。上位${MAX_GAP_FILLS}件までをWebSearch/WebFetchで調査して埋めよ。矛盾の指摘があれば、どちらが正しいか一次情報で決着させよ。
欠落: ${JSON.stringify(critic.missing.slice(0, MAX_GAP_FILLS))}
矛盾: ${JSON.stringify((critic && critic.contradictions) || [])}`, { label: 'gap-filler', phase: 'Gaps', schema: FACTS })
}

return { lenses: ok, critic, filler }
