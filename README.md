# Agents for Art

An intelligent multi-agent system for systematically discovering, extracting, and cataloging UK art exhibitions and open calls. This project uses specialized AI agents to automate the collection of comprehensive data about art exhibitions, entry fees, prizes, and venues across the UK art scene.

## Summary

Agents for Art is a sophisticated web scraping and data collection system that employs multiple specialized AI agents to research and catalog UK art exhibitions and open calls from January 2023 to July 2026. The system automatically discovers relevant exhibitions, extracts detailed information including entry fees and prizes, and stores everything in a structured database for analysis.

The project aims to build a comprehensive database of 1000+ unique exhibition entries to analyze trends in entry fees, prizes, and exhibition frequency across the UK art landscape.

## Tools, Libraries and Frameworks

### Core AI Framework
- **SmolAgents** (v1.18.0+) - Multi-agent orchestration and coordination
- **OpenAI GPT Models** / **Hugging Face Models** - LLM backends for agent intelligence

### Database & Data Management
- **SQLAlchemy** (v2.0.41+) - Modern async ORM with proper typing
- **aiosqlite** (v0.21.0+) - Async SQLite database operations
- **SQLite** - Database engine with WAL mode for concurrency

### Web Scraping & Browser Automation
- **Selenium** (v4.33.0+) - Web browser automation
- **Helium** (v5.1.1+) - Simplified browser interaction layer
- **httpx** - Modern async HTTP client
- **DuckDuckGo Search** (v8.0.3+) - Web search capabilities

### Supporting Libraries
- **Pillow** (v11.2.1+) - Image processing
- **python-dotenv** (v1.1.0+) - Environment variable management
- **cryptography** (v42.0.0+) - Security and encryption
- **websockets** (v14.0+) - WebSocket support
- **crewai** (v0.126.0+) - Additional agent capabilities

### Development Tools
- **Ruff** (v0.11.13+) - Fast Python linter and formatter
- **Python 3.12+** - Modern Python with latest features

## Project Structure

```
agents-for-art/
├── main.py                     # Main orchestrator and agent coordination
├── models/                     # Database models and management
│   ├── __init__.py
│   ├── models.py              # SQLAlchemy models (URLs, Exhibitions, Fees, Prizes)
│   └── db.py                  # Async database manager and operations
├── tools/                     # Agent tools and utilities
│   ├── database_tools.py      # Database operation tools for agents
│   └── web_tools.py           # Web scraping and browser tools
├── helium_instructions.txt    # Browser automation guidelines
├── pyproject.toml            # Project dependencies and configuration
├── art_events.db             # SQLite database (generated)
├── .gitignore               # Git ignore patterns
└── README.md                # This documentation
```

### Key Components

#### Models (`/models/`)
- **`models.py`** - Modern SQLAlchemy 2.x models with proper typing
  - `Exhibition` - Main exhibition data with relationships
  - `Url` - Raw scraped URLs and metadata
  - `EntryFee` - Fee structures (tiered/flat rates, commissions)
  - `Prize` - Prize information and amounts
- **`db.py`** - Async database manager with connection pooling and WAL mode

#### Agent Tools (`/tools/`)
- **`database_tools.py`** - Database operations accessible to agents
  - Async operations with retry logic
  - Data validation and consistency checks
  - Query helpers and statistics
- **`web_tools.py`** - Web scraping and browser automation tools
  - Rate-limited scraping with user agent rotation
  - Enhanced popup handling and element searching
  - Error handling and timeout management

#### Main Orchestrator (`main.py`)
- **Agent Configuration** - Model selection and parameter tuning
- **Agent Specialization** - Five specialized agent types
- **Task Coordination** - Workflow management and result integration
- **Resource Management** - Proper cleanup and error handling

## Database Schema

The system uses a relational database with four main tables:

### Tables

**`urls`** - Source URL tracking
- `id` (Primary Key)
- `url` - Exhibition URL (unique)
- `raw_title`, `raw_date`, `raw_location`, `raw_description` - Raw scraped data
- `first_seen`, `updated_at` - Timestamps

**`exhibitions`** - Structured exhibition data
- `id` (Primary Key)
- `title`, `venue`, `location`, `county` - Exhibition details
- `date_start`, `date_end` - Exhibition dates
- `description` - Detailed description
- `url_id` (Foreign Key → urls.id)

**`entry_fees`** - Fee structures
- `id` (Primary Key)
- `exhibition_id` (Foreign Key → exhibitions.id)
- `fee_type` - "tiered" or "flat"
- `number_entries`, `fee_amount`, `flat_rate`, `commission_percent` - Fee details

**`prizes`** - Prize information
- `id` (Primary Key)
- `exhibition_id` (Foreign Key → exhibitions.id)
- `prize_rank`, `prize_amount`, `prize_type`, `prize_description` - Prize details

## Agent Architecture

The system employs five specialized AI agents:

1. **Research_Coordinator** (Manager)
   - Coordinates overall research process
   - Delegates tasks to specialized agents
   - Monitors progress and statistics

2. **Web_Search_Specialist**
   - Discovers exhibition URLs from aggregator sites
   - Targets ArtRabbit, Artlyst, The Art Newspaper
   - Uses strategic search queries

3. **Browser_Navigation_Agent**
   - Handles browser navigation and interaction
   - Manages popups and cookie banners
   - Searches for key terms on pages

4. **Content_Extraction_Specialist**
   - Extracts structured data from web pages
   - Processes exhibition details, fees, and prizes
   - Handles various page formats and layouts

5. **Database_Management_Specialist**
   - Stores extracted data with validation
   - Ensures data consistency and handles duplicates
   - Manages database operations and queries

## How to Use

### Prerequisites

- Python 3.12 or higher
- Internet connection for web scraping
- Optional: OpenAI API key for GPT models (otherwise uses Hugging Face models)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/CodeHalwell/agents-for-art.git
   cd agents-for-art
   ```

2. **Install dependencies:**
   ```bash
   pip install -e .
   ```

3. **Set up environment variables (optional):**
   ```bash
   # Create .env file for API keys
   echo "OPENAI_API_KEY=your_key_here" > .env
   ```

### Running the System

1. **Start the research system:**
   ```bash
   python main.py
   ```

2. **Monitor progress:**
   - The system will automatically create `art_events.db`
   - Agents will begin searching and extracting data
   - Progress is logged to the console

### Configuration

Edit the `AgentConfig` class in `main.py` to customize:
- Model providers (OpenAI vs Hugging Face)
- Agent parameters (max steps, verbosity)
- Search targets and date ranges

### Accessing Results

The collected data is stored in SQLite database `art_events.db`. You can query it directly:

```python
import sqlite3
conn = sqlite3.connect('art_events.db')
cursor = conn.cursor()

# Get exhibition count
cursor.execute("SELECT COUNT(*) FROM exhibitions")
print(f"Total exhibitions: {cursor.fetchone()[0]}")

# Get recent exhibitions
cursor.execute("""
    SELECT title, venue, date_start 
    FROM exhibitions 
    ORDER BY created_at DESC 
    LIMIT 10
""")
for row in cursor.fetchall():
    print(f"{row[0]} at {row[1]} - {row[2]}")
```

## MIT License

Copyright (c) 2024 CodeHalwell

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Collaboration and Contributions

Contributions, suggestions, and collaboration are welcome! Here's how you can get involved:

### Contributing

1. **Fork the repository** and create a feature branch
2. **Follow the existing code style** using Ruff for formatting
3. **Test your changes** thoroughly before submitting
4. **Submit a pull request** with a clear description of your changes

### Areas for Contribution

- Additional web scraping tools for new art platforms
- Enhanced data extraction algorithms
- Improved error handling and recovery
- Performance optimizations
- Documentation improvements
- Testing infrastructure

### Reporting Issues

- Use GitHub Issues to report bugs or suggest features
- Provide detailed reproduction steps and expected behavior
- Include relevant logs and system information

### Development Guidelines

- **Code Style:** Follow existing patterns and use Ruff for linting
- **Documentation:** Update documentation for any API changes
- **Testing:** Add tests for new functionality where applicable
- **Async/Await:** Use proper async patterns for database and web operations

## Next Steps for Improvement

Based on the current codebase analysis, here are recommended improvements:

### 1. Enhanced Database Logic and Helper Functions

**Current State:** Basic async operations with retry logic
**Improvements Needed:**
- Add database query optimization and indexing
- Implement bulk insert operations for better performance
- Add data validation helpers and constraint checking
- Create reporting and analytics query helpers
- Implement database migration system for schema updates

**Specific Tasks:**
```python
# Add these helper functions to models/db.py:
- bulk_insert_exhibitions(exhibitions_data: List[Dict])
- get_exhibitions_by_criteria(date_range, location, fee_range)
- generate_fee_analysis_report()
- cleanup_duplicate_entries()
- add_database_indexes()
```

### 2. Addition of More Web-Based Search Tools

**Current State:** DuckDuckGo search and basic web scraping
**Improvements Needed:**
- Add specialized scrapers for major UK art platforms
- Implement Google Search API integration
- Add RSS feed monitoring for art news sites
- Create social media monitoring (Twitter, Instagram art hashtags)
- Add calendar integration for event discovery

**Target Platforms:**
- ArtRabbit API integration
- Artlyst automated scraping
- The Art Newspaper RSS feeds
- Saatchi Art competition feeds
- Royal Academy and major gallery calendars

### 3. Fine-Tune Existing Tools (Reduce Token Usage)

**Current State:** Direct LLM calls for all content extraction
**Improvements Needed:**
- Implement pre-processing to extract relevant sections before LLM analysis
- Add regex patterns for common fee and date formats
- Use deterministic parsing for structured data (prices, dates, locations)
- Implement content summarization before LLM processing
- Add caching for similar content patterns

**Optimization Strategies:**
```python
# Add to tools/web_tools.py:
- preprocess_content_for_extraction(html_content) 
- extract_prices_with_regex(text)
- extract_dates_with_regex(text)
- cache_similar_content_patterns(content_hash)
- reduce_content_to_relevant_sections(content, keywords)
```

### 4. Improve Agent Flow for Constant Database Updates

**Current State:** Sequential processing with potential data loss
**Improvements Needed:**
- Implement checkpoint system for resuming interrupted operations
- Add real-time progress tracking and reporting
- Create database update queues with priority handling
- Implement incremental updates rather than full re-processing
- Add data consistency verification between agent steps

**Flow Improvements:**
- Add state persistence for agent coordination
- Implement rollback mechanisms for failed operations
- Create progress monitoring dashboard
- Add automated health checks and recovery

### 5. Additional Improvements Identified During Review

**Code Quality:**
- Add comprehensive logging throughout the system
- Implement proper error categorization and handling
- Add configuration management system
- Create comprehensive test suite

**Performance:**
- Implement connection pooling for web requests
- Add request rate limiting per domain
- Optimize database queries with proper indexing
- Add asynchronous processing queues

**Monitoring & Analytics:**
- Add metrics collection (success rates, processing times)
- Create data quality monitoring
- Implement alerting for system failures
- Add trend analysis and reporting tools

**Security:**
- Implement request header randomization
- Add proxy rotation support
- Secure API key management
- Add rate limiting per target site

### Implementation Priority

1. **High Priority:** Database optimization and helper functions
2. **High Priority:** Token usage reduction in LLM calls
3. **Medium Priority:** Additional web search tools
4. **Medium Priority:** Agent flow improvements
5. **Low Priority:** Monitoring and analytics enhancements

These improvements would significantly enhance the system's reliability, efficiency, and data collection capabilities while reducing operational costs and improving maintainability.