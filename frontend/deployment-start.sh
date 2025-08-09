#!/bin/bash
set -e

PORT=${PORT:-8080}
export NODE_ENV=production

echo "Starting deployment on port $PORT"

# Check if build exists
if [ ! -d ".next" ]; then
  echo "No build found, creating a minimal response server while building..."
  
  # Start a minimal Node.js server that responds immediately to health checks
  node -e "
    const http = require('http');
    const server = http.createServer((req, res) => {
      if (req.url === '/' || req.url === '/health') {
        res.writeHead(200, { 'Content-Type': 'text/plain' });
        res.end('Building... Please wait.');
      } else {
        res.writeHead(404);
        res.end('Not found');
      }
    });
    server.listen($PORT, '0.0.0.0', () => {
      console.log('Temporary server listening on 0.0.0.0:$PORT');
    });
  " &
  
  TEMP_SERVER_PID=$!
  
  # Build in the background
  echo "Running build..."
  npm ci
  npm run build
  
  # Kill temporary server
  kill $TEMP_SERVER_PID 2>/dev/null || true
  
  echo "Build complete, starting Next.js..."
fi

# Start the actual Next.js server
exec npx next start -H 0.0.0.0 -p $PORT