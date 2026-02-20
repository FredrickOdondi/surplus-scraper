"""
FastAPI Application for Surplus Equipment Scraper
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
from pydantic import BaseModel
from typing import List, Dict, Optional
import pandas as pd
import io
from datetime import datetime

from scraper import SurplusScraper

app = FastAPI(title="Surplus Equipment Scraper")

# Store for scraped data (in production, use a database)
scraped_data_store = {}
scraping_status = {}


class ScrapingRequest(BaseModel):
    max_listings: Optional[int] = None


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Render the main page"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/scrape")
async def start_scraping(background_tasks: BackgroundTasks, request: ScrapingRequest = ScrapingRequest()):
    """Start the scraping process in the background"""
    job_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    scraping_status[job_id] = {"status": "pending", "progress": 0, "total": 0, "current_url": ""}

    background_tasks.add_task(run_scraping_job, job_id, request.max_listings)

    return {"job_id": job_id, "status": "started"}


def run_scraping_job(job_id: str, max_listings: Optional[int] = None):
    """Run the scraping job"""
    scraping_status[job_id] = {"status": "running", "progress": 0, "total": 0, "current_url": "Initializing..."}

    def progress_callback(current: int, total: int, url: str):
        scraping_status[job_id] = {
            "status": "running",
            "progress": current,
            "total": total,
            "current_url": url[:100] + "..." if len(url) > 100 else url
        }

    try:
        scraper = SurplusScraper()
        all_data = scraper.scrape_all_listings(max_items=max_listings, progress_callback=progress_callback)

        # Convert pictures list to string for CSV export
        for item in all_data:
            if isinstance(item.get('pictures'), list):
                item['pictures'] = '; '.join(item['pictures']) if item['pictures'] else ''

        scraped_data_store[job_id] = all_data
        scraping_status[job_id] = {
            "status": "completed",
            "progress": scraping_status[job_id].get("progress", 0),
            "total": scraping_status[job_id].get("total", 0),
            "current_url": "Completed",
            "count": len(all_data)
        }
    except Exception as e:
        import traceback
        scraping_status[job_id] = {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "progress": scraping_status[job_id].get("progress", 0),
            "total": scraping_status[job_id].get("total", 0)
        }


@app.get("/api/status/{job_id}")
async def get_scraping_status(job_id: str):
    """Get the status of a scraping job"""
    if job_id not in scraping_status:
        raise HTTPException(status_code=404, detail="Job not found")
    return scraping_status[job_id]


@app.get("/api/data/{job_id}")
async def get_scraped_data(job_id: str):
    """Get the scraped data for a job"""
    if job_id not in scraped_data_store:
        raise HTTPException(status_code=404, detail="Data not found")
    return {"data": scraped_data_store[job_id]}


@app.get("/api/export/{job_id}/csv")
async def export_csv(job_id: str):
    """Export scraped data as CSV"""
    if job_id not in scraped_data_store:
        raise HTTPException(status_code=404, detail="Data not found")

    data = scraped_data_store[job_id]
    if not data:
        raise HTTPException(status_code=404, detail="No data to export")

    df = pd.DataFrame(data)

    # Reorder columns
    columns_order = [
        'item_id', 'title', 'condition', 'location', 'category', 'listing_type', 'price',
        'manufacturer', 'model', 'year_of_manufacturer', 'description',
        'pictures', 'url'
    ]

    df = df.reindex(columns=columns_order, fill_value='')

    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)

    response = StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type='text/csv',
        headers={'Content-Disposition': f'attachment; filename=surplus_equipment_{job_id}.csv'}
    )

    return response


@app.get("/api/export/{job_id}/json")
async def export_json(job_id: str):
    """Export scraped data as JSON"""
    if job_id not in scraped_data_store:
        raise HTTPException(status_code=404, detail="Data not found")

    data = scraped_data_store[job_id]
    if not data:
        raise HTTPException(status_code=404, detail="No data to export")

    from fastapi.responses import JSONResponse
    return JSONResponse(
        content=data,
        headers={'Content-Disposition': f'attachment; filename=surplus_equipment_{job_id}.json'}
    )


@app.delete("/api/data/{job_id}")
async def delete_data(job_id: str):
    """Delete scraped data"""
    if job_id in scraped_data_store:
        del scraped_data_store[job_id]
    if job_id in scraping_status:
        del scraping_status[job_id]
    return {"message": "Data deleted"}


@app.get("/api/jobs")
async def list_jobs():
    """List all scraping jobs"""
    jobs = []
    for job_id, status in scraping_status.items():
        job_info = {
            "job_id": job_id,
            "status": status.get("status", "unknown"),
            "count": scraped_data_store.get(job_id, len(scraped_data_store.get(job_id, [])))
        }
        jobs.append(job_info)
    return {"jobs": jobs}


# Templates
templates = Jinja2Templates(directory="templates")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
