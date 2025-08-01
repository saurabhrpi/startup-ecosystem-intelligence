# Startup Ecosystem Intelligence Platform

An AI-powered intelligence platform that uses Graph RAG to discover hidden connections and opportunities in the startup ecosystem through multi-source data integration and intelligent agent analysis.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- OpenAI API key
- Pinecone API key

### Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd startup-ecosystem-intelligence
```

2. Create and activate virtual environment:
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

### Running the Application

#### 1. Data Pipeline (Collect and Process Data)
```bash
python run_pipeline.py
```
This will:
- Collect data from YC companies, GitHub repos, and other sources
- Generate embeddings for all collected data
- Store embeddings in Pinecone vector database

#### 2. API Server (Search and Query)
```bash
python run_api.py
```
This will start the FastAPI server at http://localhost:8000

API endpoints:
- `GET /` - Health check
- `GET /search?query=your+query` - Search the ecosystem
- `GET /stats` - Get database statistics
- `GET /docs` - Interactive API documentation

### Testing the API

```bash
# Search for AI startups
curl "http://localhost:8000/search?query=AI%20startups%20in%20San%20Francisco"

# Get database stats
curl "http://localhost:8000/stats"
```

## 📊 Project Structure

```
startup-ecosystem-intelligence/
├── backend/
│   ├── api/               # FastAPI application
│   ├── collectors/        # Data collectors (YC, GitHub, etc.)
│   ├── utils/            # Utilities (embeddings, vector store)
│   └── pipeline.py       # Main data pipeline
├── data/
│   ├── raw/              # Raw collected data
│   ├── processed/        # Processed data
│   └── embeddings/       # Generated embeddings
├── frontend/             # Next.js frontend (coming soon)
├── run_pipeline.py       # Entry point for data pipeline
├── run_api.py           # Entry point for API server
└── requirements.txt     # Python dependencies
```

## 🎯 Features

- **Multi-Source Data Collection**: YC companies, GitHub repos, SEC filings, and more
- **Vector Search**: Semantic search using OpenAI embeddings
- **Intelligent Responses**: GPT-4 powered analysis and insights
- **Graph Relationships**: Discover hidden connections (coming soon)
- **Real-time Updates**: Continuous data collection and processing

## 🔧 Configuration

Edit `.env` file to configure:
- `OPENAI_API_KEY`: Your OpenAI API key
- `PINECONE_API_KEY`: Your Pinecone API key
- `PINECONE_INDEX_NAME`: Pinecone index name (default: startup-embeddings)
- `GITHUB_TOKEN`: GitHub personal access token (optional)

## 📈 Current Status

- ✅ Data pipeline for YC companies and GitHub repos
- ✅ Vector embeddings generation
- ✅ RAG-powered search API
- ✅ Basic API endpoints
- 🚧 Graph database integration (Neo4j)
- 🚧 Frontend application
- 🚧 Additional data sources

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.
