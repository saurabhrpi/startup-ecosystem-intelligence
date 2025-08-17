'use client'

import { useState } from 'react'
import InvestorCard from './InvestorCard'
import PersonDetail from './PersonDetail'

interface Person {
  id: string
  score: number
  metadata: {
    name: string
    role?: string
    company?: string
    source?: string
    location?: string
    type: string
  }
}

export default function InvestorGrid({ people = [] }: { people: Person[] }) {
  const [selected, setSelected] = useState<Person | null>(null)
  if (!people || people.length === 0) {
    return <div className="text-center py-8 text-gray-500">No investors found. Try a different search.</div>
  }
  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {people.map((p) => (
          <InvestorCard key={p.id} person={p} onClick={() => setSelected(p)} />
        ))}
      </div>
      {selected && <PersonDetail person={selected as any} onClose={() => setSelected(null)} />}
    </>
  )
}


