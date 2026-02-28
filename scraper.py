"""
Surplus Equipment Scraper
Scrapes industrial equipment from surplus.infineon.com

Data fields extracted:
- title, condition, location, category, listing_type
- pictures, manufacturer, model, year_of_manufacturer, description
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import re
import time
from urllib.parse import urljoin, urlparse


class SurplusScraper:
    BASE_URL = "https://surplus.infineon.com/"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

    def get_soup(self, url: str) -> BeautifulSoup:
        """Get BeautifulSoup object from URL"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

    def extract_text(self, element, default: str = "") -> str:
        """Safely extract text from element"""
        if element:
            return element.get_text(strip=True)
        return default

    def extract_table_value(self, soup: BeautifulSoup, label: str) -> str:
        """Extract value from table by finding the row with a specific label"""
        # Find all table rows
        rows = soup.find_all('tr')
        for row in rows:
            # Look for the label in the first cell (usually td.txtb)
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                label_text = self.extract_text(cells[0]).lower()
                # Check if this is the row we're looking for
                # Match exact label or contains it
                if label_text == label.lower() or label.lower() in label_text:
                    # Get the value from the second cell
                    # Look for td.txt class within the second cell
                    value_cell = cells[1]
                    value_elem = value_cell.find(class_='txt') or value_cell.find('td')
                    if value_elem:
                        value = self.extract_text(value_elem)
                    else:
                        value = self.extract_text(value_cell)
                    if value:
                        # Clean up the value - remove common artifacts
                        value = re.sub(r'^(Offered|Wanted)\s+at.*$', '', value, flags=re.IGNORECASE)
                        value = re.sub(r'Serial\s+Number.*$', '', value, flags=re.IGNORECASE)
                        value = re.sub(r'Model.*$', '', value, flags=re.IGNORECASE)
                        value = re.sub(r'Manufacture.*$', '', value, flags=re.IGNORECASE)
                        value = re.sub(r'Manufacturer.*$', '', value, flags=re.IGNORECASE)
                        value = re.sub(r'\d{5,}.*$', '', value)  # Remove long numbers (likely serials)
                        value = ' '.join(value.split())  # Clean up whitespace
                        return value.strip()
        return ""

    def scrape_listing(self, item_no: str) -> Dict[str, any]:
        """Scrape a single listing page by item number"""
        listing_url = f"{self.BASE_URL}iinfo.cfm?ItemNo={item_no}"
        soup = self.get_soup(listing_url)
        if not soup:
            return None

        listing_data = {
            'title': '',
            'condition': '',
            'location': 'Regensburg, Germany',  # Default location from site info
            'category': '',
            'listing_type': '',
            'price': '',
            'pictures': [],
            'manufacturer': '',
            'model': '',
            'year_of_manufacturer': '',
            'description': '',
            'url': listing_url,
            'item_id': item_no
        }

        # Extract title - Try multiple selectors
        # Option 1: h1.HL1 span.HL1
        title_elem = soup.select_one('h1.HL1 span.HL1')
        if title_elem:
            title_text = self.extract_text(title_elem)
            # Remove quantity and price info from title
            title_text = re.sub(r'^\d+\s+(Offered|Wanted)\s+at.*', '', title_text, flags=re.IGNORECASE)
            listing_data['title'] = title_text.strip()

        # Option 2: If no title found, try extracting from the page title tag
        if not listing_data['title']:
            title_tag = soup.find('title')
            if title_tag:
                title_text = self.extract_text(title_tag)
                # Clean up the title
                title_text = title_text.replace('Infineon Technologies AG - Equipment Trade', '').strip()
                listing_data['title'] = title_text

        # Option 3: Try to find title in the first bold/strong tag
        if not listing_data['title']:
            for bold in soup.find_all(['b', 'strong']):
                text = self.extract_text(bold)
                if text and len(text) > 10 and 'offered' not in text.lower() and 'wanted' not in text.lower():
                    listing_data['title'] = text
                    break

        # Extract listing type from the h2.HL span (contains "Offered at" or "Wanted")
        type_elem = soup.select_one('h2.HL span.HL')
        if type_elem:
            type_text = self.extract_text(type_elem).lower()
            if 'offered' in type_text:
                listing_data['listing_type'] = 'For Sale'
            elif 'wanted' in type_text:
                listing_data['listing_type'] = 'Wanted'

        # Extract description - paragraph after h1
        # Look for p tag in the main content area
        p_tags = soup.find_all('p')
        for p in p_tags:
            text = self.extract_text(p)
            if text and len(text) > 20 and 'copyright' not in text.lower():
                listing_data['description'] = text
                break

        # Extract all product images - multiple methods to ensure we get everything
        seen_urls = set()

        # Method 1: Get main image from img.imgprev
        main_img = soup.select_one('img.imgprev')
        if main_img:
            src = main_img.get('src')
            if src:
                src = src.split('?')[0]
                full_url = urljoin(self.BASE_URL, src)
                listing_data['pictures'].append(full_url)
                seen_urls.add(src)

        # Method 2: Get additional images from a.addlImage links
        addl_image_links = soup.select('a.addlImage')
        for link in addl_image_links:
            href = link.get('href')
            if href and href not in seen_urls:
                href = href.split('?')[0]
                full_url = urljoin(self.BASE_URL, href)
                listing_data['pictures'].append(full_url)
                seen_urls.add(href)

        # Method 3: Fallback - find all clientresources images (product images)
        all_imgs = soup.find_all('img', src=re.compile(r'clientresources', re.IGNORECASE))
        for img in all_imgs:
            src = img.get('src')
            if src and src not in seen_urls:
                src = src.split('?')[0]
                if re.search(r'\.(jpg|jpeg|png|gif|bmp|webp)', src, re.IGNORECASE):
                    full_url = urljoin(self.BASE_URL, src)
                    listing_data['pictures'].append(full_url)
                    seen_urls.add(src)

        # Extract all table data at once for better accuracy
        # The site uses a specific table structure with td.txtb (labels) and td.txt (values)
        all_data = {}
        rows = soup.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                # Get label from first cell (often has class txtb)
                label_elem = cells[0].find(class_='txtb') or cells[0]
                label_text = self.extract_text(label_elem).strip().lower()

                # Get value from second cell (often has class txt)
                value_elem = cells[1].find(class_='txt') or cells[1]
                value_text = self.extract_text(value_elem).strip()

                if label_text and value_text:
                    all_data[label_text] = value_text

        # Map the extracted data to our fields
        listing_data['manufacturer'] = all_data.get('manufacturer', '')
        listing_data['model'] = all_data.get('model', '')
        listing_data['year_of_manufacturer'] = all_data.get('year of manufacture', '')
        listing_data['condition'] = all_data.get('condition', '')
        listing_data['price'] = all_data.get('unit price', '')

        # Extract category from breadcrumb or title
        # Look for menubar links or category navigation
        category_links = soup.select('a.menubar')
        if category_links:
            categories = [self.extract_text(a) for a in category_links if self.extract_text(a)]
            # Filter out navigation items
            categories = [c for c in categories if c not in ['View', 'Search-by-Specs']]
            if categories:
                listing_data['category'] = ' > '.join(categories)

        # Clean up data
        listing_data['title'] = re.sub(r'\s+', ' ', listing_data['title']).strip()
        listing_data['description'] = re.sub(r'\s+', ' ', listing_data['description']).strip()

        return listing_data

    def discover_listings(self, max_items: Optional[int] = None, category_menuid: Optional[str] = None) -> List[str]:
        """
        Discover all item listings from the 'All Items' pages.
        Uses pagination to get all available items.

        Args:
            max_items: Maximum number of items to discover
            category_menuid: Category ID to filter (e.g., 'm', 'm_5', 'm_5_5'). None for all categories.
        """
        item_numbers = []
        start_rec = 1
        items_per_page = 100

        if category_menuid:
            print(f"Discovering listings from category: {category_menuid}...")
        else:
            print("Discovering listings from all items pages...")

        while True:
            # Use the specified category or default to all items
            menuid = category_menuid if category_menuid else 'm'
            all_items_url = f"{self.BASE_URL}mAllitems.cfm?menuid={menuid}&subject=1&startRec={start_rec}"
            soup = self.get_soup(all_items_url)

            if not soup:
                break

            # Find all item links - they are in td.itemid a.collink0
            item_links = soup.select('td.itemid a.collink0')

            if not item_links:
                # No more items found
                break

            # Extract item numbers from hrefs like "iinfo.cfm?ItemNo=265103"
            for link in item_links:
                href = link.get('href', '')
                # Extract ItemNo from URL
                match = re.search(r'ItemNo=(\d+)', href)
                if match:
                    item_no = match.group(1)
                    if item_no not in item_numbers:
                        item_numbers.append(item_no)

            print(f"  Found {len(item_links)} items on page (starting at {start_rec})")

            # Check if we should stop
            if len(item_links) < items_per_page:
                # Last page
                break

            if max_items and len(item_numbers) >= max_items:
                item_numbers = item_numbers[:max_items]
                break

            start_rec += items_per_page
            time.sleep(0.5)  # Be respectful

        print(f"Total items discovered: {len(item_numbers)}")
        return item_numbers

    def scrape_all_listings(self, max_items: Optional[int] = None, progress_callback=None, category_menuid: Optional[str] = None) -> List[Dict[str, any]]:
        """
        Scrape all discovered listings.
        Args:
            max_items: Maximum number of items to scrape (None for all)
            progress_callback: Function called with (current, total, url) during scraping
            category_menuid: Category ID to filter (e.g., 'm', 'm_5', 'm_5_5'). None for all categories.
        """
        item_numbers = self.discover_listings(max_items, category_menuid)
        all_data = []

        for i, item_no in enumerate(item_numbers):
            print(f"Scraping {i+1}/{len(item_numbers)}: Item {item_no}")

            if progress_callback:
                progress_callback(i+1, len(item_numbers), f"Item {item_no}")

            listing_data = self.scrape_listing(item_no)
            if listing_data:
                all_data.append(listing_data)

            # Be respectful - add delay between requests
            time.sleep(0.5)

        return all_data


if __name__ == "__main__":
    scraper = SurplusScraper()
    # Test with a single item first to debug
    print("Testing single item scrape...")
    item_data = scraper.scrape_listing("255419")

    if item_data:
        print("\n=== Scraped Data ===")
        for key, value in item_data.items():
            if key != 'pictures':
                print(f"{key}: {value}")
            else:
                print(f"{key}: {len(value)} images")
                for i, pic in enumerate(value[:3]):
                    print(f"  - {pic}")

    # Test with a limited number of items
    print("\n\nTesting batch scrape...")
    data = scraper.scrape_all_listings(max_items=3)

    print(f"\nScraped {len(data)} listings")
    for item in data:
        print(f"\n--- {item['title'][:50]} ---")
        print(f"Manufacturer: {item['manufacturer']}")
        print(f"Model: {item['model']}")
        print(f"Year: {item['year_of_manufacturer']}")
        print(f"Condition: {item['condition']}")
        print(f"Pictures: {len(item['pictures'])}")
        print(f"URL: {item['url']}")
