'use client'

import { useState } from 'react'
import { ChevronDown, ChevronUp, Sparkles, TrendingUp, Users, Lightbulb, ArrowRight, CheckCircle } from 'lucide-react'

interface ResponseDisplayProps {
  response: string
  totalResults: number
}

export default function ResponseDisplay({ response, totalResults }: ResponseDisplayProps) {
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

  const { summary, insights, recommendations, companies } = parseResponse(response)

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

            {/* Recommendations */}
            {recommendations.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center space-x-2 mb-3">
                  <Sparkles className="text-purple-600" size={20} />
                  <h4 className="font-semibold text-gray-800">Recommendations</h4>
                </div>
                <div className="bg-purple-50 rounded-lg p-4 border border-purple-200">
                  <ul className="space-y-2">
                    {recommendations.map((rec, idx) => (
                      <li key={idx} className="flex items-start space-x-2">
                        <span className="text-purple-600 mt-1">→</span>
                        <span className="text-gray-700">{renderWithEmphasis(rec)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}

            {/* Raw Response Fallback */}
            {!summary && companies.length === 0 && insights.length === 0 && recommendations.length === 0 && (
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