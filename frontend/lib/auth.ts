import CredentialsProvider from 'next-auth/providers/credentials'
import type { NextAuthOptions, User, Session } from 'next-auth'
import type { JWT } from 'next-auth/jwt'
import { createHash } from 'crypto'

export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: 'Email',
      credentials: {
        name: { label: 'Name', type: 'text', placeholder: 'Jane Doe' },
        email: { label: 'Email', type: 'email', placeholder: 'you@example.com' },
      },
      async authorize(credentials) {
        const email = credentials?.email?.trim().toLowerCase()
        if (!email) return null
        const providedName = (credentials as any)?.name?.toString().trim()
        const id = createHash('sha256').update(email).digest('hex').slice(0, 24)
        const name = providedName && providedName.length > 0 ? providedName : email.split('@')[0]
        const user: User = { id, name, email }
        return user
      },
    }),
  ],
  // Fallback to BACKEND_API_KEY if NEXTAUTH_SECRET isn't set in hosting env
  secret: process.env.NEXTAUTH_SECRET || process.env.BACKEND_API_KEY,
  session: { strategy: 'jwt' },
  pages: { signIn: '/signin' },
  callbacks: {
    async jwt({ token, user }: { token: JWT; user?: User | null }) {
      if (user) {
        token.sub = user.id
        token.email = user.email
        ;(token as any).name = user.name
      }
      return token
    },
    async session({ session, token }: { session: Session; token: JWT }) {
      if (session.user) {
        ;(session.user as any).id = token.sub
        session.user.email = (token as any).email as string | null
        session.user.name = ((token as any).name as string | undefined) || session.user.name || null
      }
      return session
    },
  },
}


