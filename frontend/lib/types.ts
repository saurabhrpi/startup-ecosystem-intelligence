export interface Company {
  id: string
  score: number
  metadata: {
    name: string
    description?: string
    industries?: string[]
    batch?: string
    location?: string
    website?: string
    type: string
    source?: string
  }
}

export interface SearchResult {
  query: string
  matches: Company[]
  response: string
  total_results: number
}

export interface CompanyScore {
  company_id: string
  company_name: string
  total_score: number
  scores: {
    founder_score: number
    network_score: number
    market_score: number
    technical_score: number
    timing_score: number
  }
  investment_thesis: string
  scoring_date: string
  rank?: number
}

export interface NetworkData {
  nodes: Array<{
    id: string
    label: string
    type: string
    properties: any
  }>
  edges: Array<{
    source: string
    target: string
    type: string
    properties?: any
  }>
}