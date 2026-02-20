# Surplus Equipment Scraper

A Python web scraper application that extracts industrial equipment data from surplus.infineon.com. Built with FastAPI backend, BeautifulSoup for HTML parsing, and a responsive HTML/JavaScript frontend.

## Features

- **Automated Scraping**: Discovers and scrapes all equipment listings from the website
- **Real-time Progress**: Live progress updates during scraping
- **Data Extraction**: Extracts comprehensive data for each equipment item:
  - Title
  - Condition
  - Location
  - Category
  - Listing Type (For Sale/Wanted)
  - Manufacturer
  - Model
  - Year of Manufacturer
  - Description
  - Pictures (all image URLs)
- **Export Options**: Export data to CSV or JSON formats
- **Interactive Table**: View scraped data in a sortable, filterable table
- **Statistics**: View summary statistics of scraped data

## Installation

1. **Install Python dependencies:**

```bash
pip install -r requirements.txt
```

Or install manually:

```bash
pip install fastapi uvicorn beautifulsoup4 requests pandas python-multipart jinja2 aiofiles httpx lxml
```

## Usage

### Starting the Server

Run the FastAPI application:

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The application will be available at: **http://localhost:8000**

### Using the Web Interface

1. Open your browser and go to `http://localhost:8000`
2. Optionally, set a maximum number of listings to scrape (leave empty for all)
3. Click "Start Scraping"
4. Watch the progress bar and status updates
5. Once complete, view the data in the table
6. Export to CSV or JSON using the action buttons

### Using the Scraper Programmatically

You can also use the scraper directly in Python:

```python
from scraper import SurplusScraper

# Create scraper instance
scraper = SurplusScraper()

# Scrape all listings
data = scraper.scrape_all_listings()

# Or scrape with a limit
data = scraper.scrape_all_listings(max_items=10)

# Access individual item data
for item in data:
    print(f"Title: {item['title']}")
    print(f"Manufacturer: {item['manufacturer']}")
    print(f"Model: {item['model']}")
    print(f"Year: {item['year_of_manufacturer']}")
    print(f"Condition: {item['condition']}")
    print(f"Pictures: {len(item['pictures'])} images")
    print(f"URL: {item['url']}")
    print("-" * 50)
```

## API Endpoints

### Web Interface
- `GET /` - Main web interface

### Scraping Operations
- `POST /api/scrape` - Start a new scraping job
  - Body: `{"max_listings": 100}` (optional)
  - Returns: `{"job_id": "20240220_123000", "status": "started"}`

- `GET /api/status/{job_id}` - Get scraping job status
  - Returns: Status, progress, total items, current item

- `GET /api/data/{job_id}` - Get scraped data
  - Returns: JSON array of all scraped items

### Export
- `GET /api/export/{job_id}/csv` - Export data as CSV file
- `GET /api/export/{job_id}/json` - Export data as JSON file

### Management
- `GET /api/jobs` - List all scraping jobs
- `DELETE /api/data/{job_id}` - Delete scraped data

## Data Fields

Each scraped item contains:

| Field | Type | Description |
|-------|------|-------------|
| `item_id` | string | Unique item identifier |
| `title` | string | Equipment title/name |
| `manufacturer` | string | Manufacturer name |
| `model` | string | Model number/name |
| `year_of_manufacturer` | string | Year manufactured |
| `condition` | string | Equipment condition |
| `location` | string | Equipment location |
| `category` | string | Category path |
| `listing_type` | string | "For Sale" or "Wanted" |
| `description` | string | Full description |
| `pictures` | string | Semicolon-separated image URLs |
| `url` | string | Direct link to listing |

## CSV Export Format

The CSV export includes all fields in this order:

```
item_id,title,condition,location,category,listing_type,manufacturer,model,year_of_manufacturer,description,pictures,url
```

## Project Structure

```
surplus-scraper/
├── main.py              # FastAPI application
├── scraper.py           # Scraper logic
├── requirements.txt     # Python dependencies
├── templates/
│   └── index.html      # Frontend interface
├── static/             # Static files (CSS, JS, images)
└── README.md           # This file
```

## How It Works

1. **Discovery Phase**: The scraper first discovers all available listings by parsing the "All Items" pages, handling pagination automatically.

2. **Scraping Phase**: For each discovered item, it:
   - Fetches the individual item detail page
   - Extracts structured data using CSS selectors
   - Downloads image URLs
   - Parses specification tables

3. **Data Storage**: Data is stored in memory (can be modified to use a database for persistence)

4. **Export**: Data can be exported in CSV or JSON format

## Notes

- **Rate Limiting**: The scraper includes a 0.5 second delay between requests to be respectful to the server
- **Pagination**: Automatically handles pagination (100 items per page)
- **Error Handling**: Continues scraping even if individual items fail
- **Location**: Default location is set to "Regensburg, Germany" based on site information

## Troubleshooting

### "No items found" error
- Check your internet connection
- The website may be temporarily unavailable
- Verify the website structure hasn't changed significantly

### Slow scraping performance
- This is normal due to rate limiting and the number of items
- You can reduce the `max_listings` parameter for testing
- The delay between requests can be adjusted in `scraper.py` (search for `time.sleep(0.5)`)

### Images not loading
- Image URLs are relative to the website
- Some images may require authentication or may have expired

## License

This scraper is for educational and research purposes. Please respect the website's terms of service and robots.txt file.

## Support

For issues or questions, please check the code comments or create an issue in the repository.
