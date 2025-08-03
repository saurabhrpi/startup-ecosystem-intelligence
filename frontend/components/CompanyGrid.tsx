'use client'

import { Company } from '@/lib/types'
import CompanyCard from './CompanyCard'

interface CompanyGridProps {
  companies: Company[]
  onSelectCompany: (company: Company) => void
}

export default function CompanyGrid({ companies, onSelectCompany }: CompanyGridProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      {companies.map((company) => (
        <CompanyCard
          key={company.id}
          company={company}
          onClick={() => onSelectCompany(company)}
        />
      ))}
    </div>
  )
}