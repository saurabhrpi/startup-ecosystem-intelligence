# Deployment Guide

## Backend Deployment Options

### Option 1: Fly.io (Recommended for FastAPI)
```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login to Fly
fly auth login

# Create Dockerfile for backend
# Then deploy
fly launch
fly deploy
```

### Option 2: Railway
1. Go to https://railway.app
2. Connect your GitHub repo
3. Set environment variables
4. Deploy

### Option 3: Render
1. Go to https://render.com
2. Create a new Web Service
3. Connect your GitHub repo
4. Set environment variables

## Frontend Deployment to Vercel

### Method 1: Vercel CLI
```bash
cd frontend
npm i -g vercel
vercel
```

### Method 2: GitHub Integration
1. Push your code to GitHub
2. Go to https://vercel.com
3. Import your GitHub repository
4. Set root directory to `frontend`
5. Add environment variable:
   - `NEXT_PUBLIC_API_URL` = Your backend URL (e.g., https://your-api.fly.dev)
6. Deploy!

### Method 3: Direct Upload
```bash
cd frontend
npm run build
# Then drag & drop the .next folder to Vercel dashboard
```

## Environment Variables for Vercel

In Vercel dashboard, add:
- `NEXT_PUBLIC_API_URL`: Your deployed backend URL

## CORS Configuration

Make sure your backend allows requests from your Vercel domain!