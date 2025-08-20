'use client'

import { useState } from 'react'
import { ChevronDown, ChevronUp, Sparkles, TrendingUp, Users, Lightbulb, ArrowRight, CheckCircle } from 'lucide-react'

interface ResponseDisplayProps {
  response: string
  totalResults: number
  matches?: any[]
  query?: string
  filterOnly?: boolean
}

export default function ResponseDisplay({ response, totalResults, matches = [], query, filterOnly }: ResponseDisplayProps) {
  const [expanded, setExpanded] = useState(true)

  // Parse the response to extract insights and recommendations
  const parseResponse = (text: string) => {
    const lines = text.split('\n').filter(line => line.trim())
    const insights: string[] = []
    const recommendations: string[] = []
    const companies: string[] = []
    let summary = ''
    
    lines.forEach(line => {
      const trimmedLine = line.trim()
      // Check for company suggestions (lines starting with - or •)
      if (trimmedLine.match(/^[-•]\s*(.+)/)) {
        const company = trimmedLine.replace(/^[-•]\s*/, '')
        companies.push(company)
      } else if (trimmedLine.toLowerCase().includes('recommend') || trimmedLine.toLowerCase().includes('suggest')) {
        recommendations.push(trimmedLine)
      } else if (trimmedLine.toLowerCase().includes('insight') || trimmedLine.toLowerCase().includes('trend')) {
        insights.push(trimmedLine)
      } else if (!summary && trimmedLine.length > 20) {
        summary = trimmedLine
      }
    })

    return { summary, insights, recommendations, companies }
  }

  const { summary, insights, recommendations: aiRecommendations, companies } = parseResponse(response)

  // Derive concise recommendations directly from actual matches to avoid LLM drift
  const derivedRecommendations: string[] = Array.isArray(matches)
    ? matches.slice(0, 5).map((m: any) => {
        const meta = m?.metadata || m || {}
        const type = (m?.type || meta?.type || '').toString()
        const name = (meta?.name || meta?.company || meta?.id || '').toString()
        if (!name) return 'Top match'
        if (type === 'Person') {
          const role = (meta?.role || '').toString()
          const company = (meta?.company || '').toString()
          return `${name}${role ? ` — ${role}` : ''}${company ? ` @ ${company}` : ''}`
        }
        if (type === 'Repository') {
          const company = (meta?.company?.name || meta?.company || '').toString()
          return `${name}${company ? ` (${company})` : ''}`
        }
        return name
      })
    : []

  // Build natural-language recommendation sentences from matches
  const buildContextPhrase = (q?: string) => {
    const ql = (q || '').toLowerCase()
    // Try to extract a domain after 'in '
    const inIdx = ql.indexOf(' in ')
    if (inIdx >= 0) {
      const after = ql.slice(inIdx + 4).trim()
      if (after) {
        const end = after.search(/[.,;]|$/)
        const raw = after.slice(0, end).trim()
        if (raw) {
          // Title-case simple tokens like 'edtech'
          const pretty = raw.split(/\s+/).map(w => w.length > 2 ? w[0].toUpperCase() + w.slice(1) : w.toUpperCase()).join(' ')
          return ` in the ${pretty} field`
        }
      }
    }
    return ''
  }

  const buildRecommendationSentences = (): string[] => {
    const names: string[] = []
    const investors: string[] = []
    const others: string[] = []
    if (!Array.isArray(matches)) return []
    const unique = new Set<string>()
    for (const m of matches) {
      const meta = (m?.metadata || m || {}) as any
      const type = (m?.type || meta?.type || '').toString()
      const name = (meta?.name || meta?.company || meta?.id || '').toString()
      if (!name || unique.has(name)) continue
      unique.add(name)
      const role = (meta?.role || '').toLowerCase()
      if (type === 'Person' && (role.includes('investor') || role.includes('vc') || role.includes('venture'))) {
        investors.push(name)
      } else {
        names.push(name)
      }
    }
    // If we have multiple investors, prioritize recommending outreach to them
    const context = buildContextPhrase(query)
    const sentences: string[] = []
    const primaryList = investors.length ? investors : names
    if (primaryList.length > 0) {
      const head = primaryList.slice(0, 2)
      const rest = primaryList.slice(2, 5)
      const headText = head.length === 1 ? head[0] : `${head[0]} and ${head[1]}`
      const restText = rest.length ? `, as well as ${rest.join(', ')}` : ''
      const who = investors.length ? 'for potential investment opportunities or partnerships' : 'for potential opportunities'
      sentences.push(`Consider reaching out to ${headText}${restText} ${who}${context}.`)
    }
    // If there are additional distinct entities beyond the first group, add a second sentence
    const secondaryPool = investors.length ? names : []
    if (secondaryPool.length > 0) {
      const sec = secondaryPool.slice(0, 3)
      const secText = sec.length === 1 ? sec[0] : sec.length === 2 ? `${sec[0]} and ${sec[1]}` : `${sec[0]}, ${sec[1]}, and ${sec[2]}`
      sentences.push(`Also, keep an eye on ${secText}, as their activities could shape the landscape${context}.`)
    }
    return sentences
  }
  const recommendationSentences = filterOnly ? [] : buildRecommendationSentences()

  // Render simple markdown emphasis (**bold**, *italic*, __bold__, _italic_) as React elements
  const renderWithEmphasis = (text: string) => {
    if (!text) return text
    const elements: React.ReactNode[] = []
    let remaining = text
    let keyIndex = 0
    const pattern = /(\*\*[^*]+\*\*|__[^_]+__|\*[^*]+\*|_[^_]+_)/
    while (remaining.length > 0) {
      const match = remaining.match(pattern)
      if (!match || match.index === undefined) {
        elements.push(remaining)
        break
      }
      const before = remaining.slice(0, match.index)
      if (before) elements.push(before)
      const token = match[0]
      const isBold = token.startsWith('**') || token.startsWith('__')
      const content = token.slice(isBold ? 2 : 1, isBold ? token.length - 2 : token.length - 1)
      elements.push(
        isBold ? (
          <strong key={`b-${keyIndex++}`}>{content}</strong>
        ) : (
          <em key={`i-${keyIndex++}`}>{content}</em>
        )
      )
      remaining = remaining.slice(match.index + token.length)
    }
    return elements
  }

  return (
    <div className="w-full max-w-6xl mx-auto mb-8">
      {/* Main Response Card */}
      <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Sparkles className="text-white" size={24} />
              <h3 className="text-xl font-semibold text-white">AI Intelligence Report</h3>
            </div>
            <div className="flex items-center space-x-4">
              <span className="bg-white/20 backdrop-blur-sm px-3 py-1 rounded-full text-white text-sm font-medium">
                {totalResults} matches found
              </span>
              <button
                onClick={() => setExpanded(!expanded)}
                className="text-white hover:bg-white/20 p-2 rounded-lg transition-colors"
              >
                {expanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
              </button>
            </div>
          </div>
        </div>

        {/* Content */}
        {expanded && (
          <div className="p-6 space-y-6">
            {/* Summary Section */}
            {summary && (
              <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-5 border border-blue-100">
                <div className="flex items-start space-x-3">
                  <div className="bg-blue-100 p-2 rounded-lg">
                    <Lightbulb className="text-blue-600" size={20} />
                  </div>
                  <div>
                    <h4 className="font-semibold text-gray-800 mb-2">Summary</h4>
                    <p className="text-gray-700 leading-relaxed">{renderWithEmphasis(summary)}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Company Suggestions */}
            {companies.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center space-x-2 mb-3">
                  <Users className="text-indigo-600" size={20} />
                  <h4 className="font-semibold text-gray-800">Suggested Companies</h4>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {companies.map((company, idx) => (
                    <div
                      key={idx}
                      className="group bg-gray-50 hover:bg-indigo-50 rounded-lg p-4 border border-gray-200 hover:border-indigo-300 transition-all cursor-pointer"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-start space-x-3">
                          <CheckCircle className="text-green-500 mt-1 flex-shrink-0" size={16} />
                          <p className="text-gray-700 font-medium">{renderWithEmphasis(company)}</p>
                        </div>
                        <ArrowRight className="text-gray-400 group-hover:text-indigo-600 group-hover:translate-x-1 transition-all" size={16} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Insights Section */}
            {insights.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center space-x-2 mb-3">
                  <TrendingUp className="text-green-600" size={20} />
                  <h4 className="font-semibold text-gray-800">Key Insights</h4>
                </div>
                <div className="bg-green-50 rounded-lg p-4 border border-green-200">
                  <ul className="space-y-2">
                    {insights.map((insight, idx) => (
                      <li key={idx} className="flex items-start space-x-2">
                        <span className="text-green-600 mt-1">•</span>
                        <span className="text-gray-700">{renderWithEmphasis(insight)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}

            {/* Recommendations (from matches only, natural-language bullets) */}
            {recommendationSentences.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center space-x-2 mb-3">
                  <Sparkles className="text-purple-600" size={20} />
                  <h4 className="font-semibold text-gray-800">Recommendations</h4>
                </div>
                <div className="bg-purple-50 rounded-lg p-4 border border-purple-200">
                  <ul className="space-y-2">
                    {recommendationSentences.map((rec, idx) => (
                      <li key={idx} className="flex items-start space-x-2">
                        <span className="text-purple-600 mt-1">•</span>
                        <span className="text-gray-700">{renderWithEmphasis(rec)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}

            {/* Raw Response Fallback */}
            {!summary && companies.length === 0 && insights.length === 0 && aiRecommendations.length === 0 && (
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-gray-700 whitespace-pre-wrap">{response}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}