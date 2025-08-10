'use client'

import { useState, useEffect } from 'react'
import { Company, CompanyScore } from '@/lib/types'
import { X, TrendingUp, Users, Brain, Clock, Code } from 'lucide-react'

interface CompanyDetailProps {
  company: Company
  onClose: () => void
}

export default function CompanyDetail({ company, onClose }: CompanyDetailProps) {
  const [score, setScore] = useState<CompanyScore | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchCompanyScore()
  }, [company.id])

  // Close on ESC key
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose()
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [onClose])

  const fetchCompanyScore = async () => {
    try {
      const response = await fetch(`/api/backend/score/${company.id}`, {
        headers: {
          'ngrok-skip-browser-warning': 'true',
          'Accept': 'application/json',
        },
      })
      if (response.ok) {
        const data = await response.json()
        setScore(data)
      }
    } catch (error) {
      console.error('Error fetching score:', error)
    } finally {
      setLoading(false)
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 8) return 'text-green-600'
    if (score >= 6) return 'text-blue-600'
    if (score >= 4) return 'text-yellow-600'
    return 'text-red-600'
  }

  const scoreIcons = {
    founder_score: Users,
    network_score: TrendingUp,
    market_score: Brain,
    technical_score: Code,
    timing_score: Clock,
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b p-6 flex justify-between items-start">
          <div>
            <h2 className="text-3xl font-bold text-gray-800">{company.metadata.name}</h2>
            {company.metadata.batch && (
              <span className="text-lg text-gray-600">YC {company.metadata.batch}</span>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-full transition-all"
          >
            <X size={24} />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Company Info */}
          <div className="space-y-4">
            {company.metadata.description && (
              <p className="text-gray-700 text-lg">{company.metadata.description}</p>
            )}
            
            <div className="grid grid-cols-2 gap-4">
              {company.metadata.location && (
                <div>
                  <span className="text-sm text-gray-500">Location</span>
                  <p className="font-medium">{company.metadata.location}</p>
                </div>
              )}
              {company.metadata.website && (
                <div>
                  <span className="text-sm text-gray-500">Website</span>
                  <p className="font-medium">
                    <a
                      href={company.metadata.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline"
                    >
                      {company.metadata.website}
                    </a>
                  </p>
                </div>
              )}
            </div>

            {company.metadata.industries && company.metadata.industries.length > 0 && (
              <div>
                <span className="text-sm text-gray-500">Industries</span>
                <div className="flex flex-wrap gap-2 mt-2">
                  {company.metadata.industries.map((industry, idx) => (
                    <span
                      key={idx}
                      className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm"
                    >
                      {industry}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* AI Score Section */}
          {loading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          ) : score ? (
            <div className="border-t pt-6">
              <h3 className="text-2xl font-semibold mb-4">AI Investment Score</h3>
              
              <div className="text-center mb-6">
                <div className={`text-6xl font-bold ${getScoreColor(score.total_score)}`}>
                  {score.total_score}/10
                </div>
                <p className="text-gray-600 mt-2">Overall Score</p>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
                {Object.entries(score.scores).map(([key, value]) => {
                  const Icon = scoreIcons[key as keyof typeof scoreIcons]
                  return (
                    <div key={key} className="text-center">
                      <Icon className="w-8 h-8 mx-auto mb-2 text-gray-600" />
                      <div className={`text-2xl font-semibold ${getScoreColor(value)}`}>
                        {value.toFixed(1)}
                      </div>
                      <p className="text-xs text-gray-600 capitalize">
                        {key.replace('_score', '').replace('_', ' ')}
                      </p>
                    </div>
                  )
                })}
              </div>

              <div className="bg-gray-50 p-4 rounded-lg">
                <h4 className="font-semibold mb-2">Investment Thesis</h4>
                <p className="text-gray-700">{score.investment_thesis}</p>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              Score not available for this company
            </div>
          )}
        </div>
      </div>
    </div>
  )
}