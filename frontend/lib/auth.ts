import CredentialsProvider from 'next-auth/providers/credentials'
import type { NextAuthOptions, User, Session } from 'next-auth'
import type { JWT } from 'next-auth/jwt'
import { createHash } from 'crypto'

export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: 'Email',
      credentials: {
        email: { label: 'Email', type: 'email', placeholder: 'you@example.com' },
      },
      async authorize(credentials) {
        const email = credentials?.email?.trim().toLowerCase()
        if (!email) return null
        const id = createHash('sha256').update(email).digest('hex').slice(0, 24)
        const user: User = { id, name: email.split('@')[0], email }
        return user
      },
    }),
  ],
  secret: process.env.NEXTAUTH_SECRET,
  session: { strategy: 'jwt' },
  pages: { signIn: '/signin' },
  callbacks: {
    async jwt({ token, user }: { token: JWT; user?: User | null }) {
      if (user) {
        token.sub = user.id
        token.email = user.email
      }
      return token
    },
    async session({ session, token }: { session: Session; token: JWT }) {
      if (session.user) {
        ;(session.user as any).id = token.sub
        session.user.email = (token as any).email as string | null
      }
      return session
    },
  },
}


