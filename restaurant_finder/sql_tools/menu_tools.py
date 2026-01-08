"""Menu scraping tools for restaurant finder agent.

Implements a 3-tier scraping strategy:
1. BeautifulSoup - Fast scraping for static HTML menus
2. Playwright - Fallback for JavaScript-heavy sites
3. OCR - For PDF and image-based menus

Includes Gemini API integration for menu summarization.
"""

import os
import re
import json
import time
import tempfile
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from pdf2image import convert_from_path
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv

from .db_connection import get_db_connection

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Constants
CACHE_TTL_DAYS = 7
REQUEST_TIMEOUT = 10
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def get_cached_menu(place_id: str) -> str:
    """
    Retrieve a cached menu from the database.

    Args:
        place_id: Google Places ID for the restaurant

    Returns:
        JSON string with cached menu data and summary, or error message
    """
    try:
        db = get_db_connection()

        # Check for cached menu within TTL
        query = """
            SELECT
                place_id,
                menu_url,
                menu_data,
                menu_summary,
                scrape_timestamp,
                scrape_method,
                scrape_status
            FROM restaurants.restaurant_menus
            WHERE place_id = %s
            AND scrape_timestamp > %s
            AND scrape_status = 'success'
            ORDER BY scrape_timestamp DESC
            LIMIT 1;
        """

        cache_cutoff = datetime.now() - timedelta(days=CACHE_TTL_DAYS)
        results = db.execute_query(query, (place_id, cache_cutoff))

        if not results:
            return json.dumps({
                "status": "cache_miss",
                "message": "No cached menu found or cache expired"
            })

        menu = results[0]

        return json.dumps({
            "status": "cache_hit",
            "place_id": menu["place_id"],
            "menu_url": menu["menu_url"],
            "summary": menu["menu_summary"],
            "menu_data": menu["menu_data"],
            "last_updated": menu["scrape_timestamp"].isoformat() if menu["scrape_timestamp"] else None,
            "scrape_method": menu["scrape_method"]
        }, indent=2)

    except Exception as e:
        logger.error(f"Error retrieving cached menu: {e}")
        return json.dumps({
            "status": "error",
            "message": f"Error retrieving cached menu: {str(e)}"
        })


def scrape_restaurant_menu(place_id: str, use_cache: bool = True) -> str:
    """
    Scrape restaurant menu from website using 3-tier strategy.

    Tier 1: BeautifulSoup for static HTML
    Tier 2: Playwright for JavaScript-heavy sites
    Tier 3: OCR for PDF/image menus

    Args:
        place_id: Google Places ID for the restaurant
        use_cache: Whether to check cache first (default: True)

    Returns:
        JSON string with menu data and summary
    """
    try:
        # Check cache first
        if use_cache:
            cached = json.loads(get_cached_menu(place_id))
            if cached.get("status") == "cache_hit":
                logger.info(f"Cache hit for place_id: {place_id}")
                return json.dumps(cached, indent=2)

        # Get restaurant details to find menu URL
        menu_url = _discover_menu_url(place_id)

        if not menu_url:
            return _save_and_return_error(
                place_id,
                None,
                "Menu URL not found. Restaurant may not have an online menu."
            )

        logger.info(f"Found menu URL: {menu_url}")

        # Detect menu type and scrape accordingly
        menu_type = _detect_menu_type(menu_url)

        if menu_type == "pdf":
            menu_data = _scrape_pdf_menu(menu_url)
        elif menu_type == "image":
            menu_data = _scrape_image_menu(menu_url)
        else:  # HTML
            # Try BeautifulSoup first
            menu_data = _scrape_html_menu(menu_url)

            # Fall back to Playwright if BeautifulSoup fails
            if not menu_data or len(menu_data.get("sections", [])) == 0:
                logger.info("BeautifulSoup failed, trying Playwright...")
                menu_data = _scrape_with_playwright(menu_url)

            # If still no data, try OCR on embedded images
            if not menu_data or len(menu_data.get("sections", [])) == 0:
                logger.info("Playwright failed, trying OCR on embedded images...")
                menu_data = _scrape_embedded_images(menu_url)

        if not menu_data or len(menu_data.get("sections", [])) == 0:
            return _save_and_return_error(
                place_id,
                menu_url,
                "Unable to extract menu data from website"
            )

        # Generate summary with Gemini
        summary = _generate_menu_summary(menu_data)

        # Save to database
        _save_menu_to_db(
            place_id,
            menu_url,
            menu_data,
            summary,
            menu_data.get("scrape_method", "unknown"),
            "success"
        )

        return json.dumps({
            "status": "success",
            "place_id": place_id,
            "menu_url": menu_url,
            "summary": summary,
            "menu_data": menu_data,
            "scrape_method": menu_data.get("scrape_method"),
            "last_updated": datetime.now().isoformat()
        }, indent=2)

    except Exception as e:
        logger.error(f"Error scraping menu: {e}")
        return json.dumps({
            "status": "error",
            "message": f"Error scraping menu: {str(e)}"
        })


def _discover_menu_url(place_id: str) -> Optional[str]:
    """Discover menu URL for a restaurant."""
    try:
        db = get_db_connection()

        # First check if menu_link column exists in database
        query = """
            SELECT website, menu_link
            FROM restaurants.sj_restaurants
            WHERE place_id = %s
            LIMIT 1;
        """
        results = db.execute_query(query, (place_id,))

        if not results:
            return None

        website = results[0].get("website")
        menu_link = results[0].get("menu_link")

        # Return menu_link if available
        if menu_link:
            return menu_link

        if not website:
            return None

        # Try common menu URL patterns
        base_url = website.rstrip('/')
        common_patterns = [
            f"{base_url}/menu",
            f"{base_url}/menus",
            f"{base_url}/food",
            f"{base_url}/our-menu",
            f"{base_url}/menu.html",
            f"{base_url}/menu.php"
        ]

        for url in common_patterns:
            try:
                response = requests.head(url, timeout=5, allow_redirects=True)
                if response.status_code == 200:
                    return url
            except:
                continue

        # Try to find menu link on homepage
        try:
            response = requests.get(website, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT})
            soup = BeautifulSoup(response.content, 'lxml')

            # Look for links containing "menu" or "food"
            menu_links = soup.find_all('a', href=re.compile(r'(menu|food|dish)', re.I))
            if menu_links:
                href = menu_links[0].get('href')
                return urljoin(website, href)
        except:
            pass

        # Return base website as fallback
        return website

    except Exception as e:
        logger.error(f"Error discovering menu URL: {e}")
        return None


def _detect_menu_type(url: str) -> str:
    """Detect if URL is PDF, image, or HTML."""
    url_lower = url.lower()

    if url_lower.endswith('.pdf'):
        return "pdf"

    if any(url_lower.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
        return "image"

    # Check Content-Type header
    try:
        response = requests.head(url, timeout=5, allow_redirects=True)
        content_type = response.headers.get('Content-Type', '').lower()

        if 'pdf' in content_type:
            return "pdf"
        if any(img_type in content_type for img_type in ['image/jpeg', 'image/png', 'image/gif']):
            return "image"
    except:
        pass

    return "html"


def _scrape_html_menu(url: str) -> Optional[Dict[str, Any]]:
    """Scrape menu using BeautifulSoup (Tier 1)."""
    try:
        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT}
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'lxml')

        # Try structured data first (schema.org)
        menu_data = _extract_structured_menu(soup)
        if menu_data:
            menu_data["scrape_method"] = "beautifulsoup_structured"
            return menu_data

        # Fall back to heuristic parsing
        menu_data = _extract_heuristic_menu(soup)
        if menu_data:
            menu_data["scrape_method"] = "beautifulsoup_heuristic"
            return menu_data

        return None

    except Exception as e:
        logger.error(f"BeautifulSoup scraping error: {e}")
        return None


def _extract_structured_menu(soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
    """Extract menu from JSON-LD structured data."""
    try:
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            data = json.loads(script.string)

            if isinstance(data, dict) and data.get('@type') == 'Menu':
                sections = []
                for section in data.get('hasMenuSection', []):
                    items = []
                    for item in section.get('hasMenuItem', []):
                        items.append({
                            "name": item.get('name'),
                            "price": item.get('offers', {}).get('price'),
                            "description": item.get('description')
                        })
                    sections.append({
                        "section_name": section.get('name'),
                        "items": items
                    })

                return {"sections": sections}
    except:
        pass

    return None


def _extract_heuristic_menu(soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
    """Extract menu using heuristic HTML parsing."""
    sections = []

    # Remove script and style tags
    for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
        tag.decompose()

    # Look for menu sections (h2, h3, section tags)
    section_headers = soup.find_all(['h2', 'h3', 'h4'], string=re.compile(r'.+', re.I))

    for header in section_headers:
        section_name = header.get_text(strip=True)

        # Skip non-menu sections
        if any(skip in section_name.lower() for skip in ['about', 'contact', 'location', 'hours']):
            continue

        items = []

        # Look for menu items in siblings
        current = header.find_next_sibling()
        while current and current.name not in ['h2', 'h3', 'h4']:
            # Look for items in lists or divs
            item_elements = current.find_all(['li', 'div'], class_=re.compile(r'(menu-item|dish|food|item)', re.I))

            for elem in item_elements:
                text = elem.get_text()

                # Extract price
                price_match = re.search(r'\$\s*\d+\.?\d*', text)
                price = price_match.group(0) if price_match else None

                # Extract name and description
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                name = lines[0] if lines else None
                description = lines[1] if len(lines) > 1 else None

                if name:
                    items.append({
                        "name": name,
                        "price": price,
                        "description": description
                    })

            current = current.find_next_sibling()

        if items:
            sections.append({
                "section_name": section_name,
                "items": items
            })

    return {"sections": sections} if sections else None


def _scrape_with_playwright(url: str) -> Optional[Dict[str, Any]]:
    """Scrape menu using Playwright for JavaScript sites (Tier 2)."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=USER_AGENT)

            # Block unnecessary resources
            context.route("**/*.{png,jpg,jpeg,gif,svg,css,font,woff,woff2}", lambda route: route.abort())

            page = context.new_page()
            page.goto(url, timeout=REQUEST_TIMEOUT * 1000, wait_until='networkidle')

            # Scroll to trigger lazy loading
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)

            # Get rendered HTML
            html = page.content()
            browser.close()

            # Parse with BeautifulSoup
            soup = BeautifulSoup(html, 'lxml')
            menu_data = _extract_heuristic_menu(soup)

            if menu_data:
                menu_data["scrape_method"] = "playwright"

            return menu_data

    except PlaywrightTimeout:
        logger.error(f"Playwright timeout for URL: {url}")
        return None
    except Exception as e:
        logger.error(f"Playwright error: {e}")
        return None


def _scrape_pdf_menu(url: str) -> Optional[Dict[str, Any]]:
    """Scrape PDF menu using OCR (Tier 3)."""
    try:
        # Download PDF
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(response.content)
            pdf_path = tmp.name

        # Convert PDF to images
        images = convert_from_path(pdf_path, dpi=200)

        # Run OCR on each page
        menu_text = ""
        for i, image in enumerate(images):
            page_text = _ocr_image_with_gemini(image)
            menu_text += f"\n\n=== Page {i+1} ===\n\n{page_text}"

        # Clean up
        os.unlink(pdf_path)

        # Structure the menu data with Gemini
        menu_data = _structure_menu_with_gemini(menu_text)
        if menu_data:
            menu_data["scrape_method"] = "ocr_pdf"

        return menu_data

    except Exception as e:
        logger.error(f"PDF scraping error: {e}")
        return None


def _scrape_image_menu(url: str) -> Optional[Dict[str, Any]]:
    """Scrape image menu using OCR (Tier 3)."""
    try:
        # Download image
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp.write(response.content)
            img_path = tmp.name

        # Load image
        image = Image.open(img_path)

        # Run OCR
        menu_text = _ocr_image_with_gemini(image)

        # Clean up
        os.unlink(img_path)

        # Structure the menu data
        menu_data = _structure_menu_with_gemini(menu_text)
        if menu_data:
            menu_data["scrape_method"] = "ocr_image"

        return menu_data

    except Exception as e:
        logger.error(f"Image scraping error: {e}")
        return None


def _scrape_embedded_images(url: str) -> Optional[Dict[str, Any]]:
    """Extract and OCR embedded menu images from HTML page."""
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT})
        soup = BeautifulSoup(response.content, 'lxml')

        # Find images that might be menus
        images = soup.find_all('img', src=re.compile(r'(menu|food)', re.I))

        if not images:
            images = soup.find_all('img')[:5]  # Try first 5 images

        for img in images:
            img_url = urljoin(url, img.get('src'))

            try:
                img_response = requests.get(img_url, timeout=5)
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                    tmp.write(img_response.content)
                    img_path = tmp.name

                image = Image.open(img_path)
                menu_text = _ocr_image_with_gemini(image)
                os.unlink(img_path)

                if menu_text and len(menu_text) > 100:
                    menu_data = _structure_menu_with_gemini(menu_text)
                    if menu_data and menu_data.get("sections"):
                        menu_data["scrape_method"] = "ocr_embedded"
                        return menu_data
            except:
                continue

        return None

    except Exception as e:
        logger.error(f"Embedded image scraping error: {e}")
        return None


def _ocr_image_with_gemini(image: Image.Image) -> str:
    """Use Gemini Vision API to extract text from image."""
    if not GEMINI_API_KEY:
        logger.error("Gemini API key not found")
        return ""

    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')

        prompt = """Extract all menu items, prices, and descriptions from this menu image.
Return the text exactly as it appears, preserving the structure and organization.
Focus on food items, prices, and any descriptions."""

        response = model.generate_content([prompt, image])
        return response.text

    except Exception as e:
        logger.error(f"Gemini OCR error: {e}")
        return ""


def _structure_menu_with_gemini(menu_text: str) -> Optional[Dict[str, Any]]:
    """Use Gemini to structure OCR text into menu format."""
    if not GEMINI_API_KEY:
        return None

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')

        prompt = f"""Convert this menu text into a structured JSON format.
Return a JSON object with this structure:
{{
  "sections": [
    {{
      "section_name": "Section Name",
      "items": [
        {{
          "name": "Item Name",
          "price": "$XX.XX",
          "description": "Item description (optional)"
        }}
      ]
    }}
  ]
}}

Menu text:
{menu_text}

Return ONLY the JSON object, no additional text."""

        response = model.generate_content(prompt)

        # Extract JSON from response
        response_text = response.text.strip()
        # Remove markdown code blocks if present
        if response_text.startswith('```'):
            response_text = re.sub(r'^```json?\s*|\s*```$', '', response_text, flags=re.MULTILINE)

        menu_data = json.loads(response_text)
        return menu_data

    except Exception as e:
        logger.error(f"Gemini structuring error: {e}")
        return None


def _generate_menu_summary(menu_data: Dict[str, Any]) -> str:
    """Generate concise menu summary using Gemini."""
    if not GEMINI_API_KEY:
        return "Menu data available (no summary generated - Gemini API key not configured)"

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')

        menu_json = json.dumps(menu_data.get("sections", []), indent=2)

        prompt = f"""Analyze this restaurant menu and provide a concise 3-5 sentence summary.
Include:
- Popular or signature items (if identifiable)
- Dietary options (vegetarian, vegan, gluten-free)
- Price range (approximate $ to $$$)
- Any notable features or specialties

Menu data:
{menu_json}

Return only the summary, no additional formatting."""

        response = model.generate_content(prompt)
        return response.text.strip()

    except Exception as e:
        logger.error(f"Gemini summary error: {e}")
        return "Menu data available (summary generation failed)"


def _save_menu_to_db(
    place_id: str,
    menu_url: str,
    menu_data: Dict[str, Any],
    summary: str,
    scrape_method: str,
    status: str,
    error_message: Optional[str] = None
) -> None:
    """Save menu data to database."""
    try:
        db = get_db_connection()

        query = """
            INSERT INTO restaurants.restaurant_menus
            (place_id, menu_url, menu_data, menu_summary, scrape_timestamp,
             scrape_method, scrape_status, error_message, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (place_id) DO UPDATE SET
                menu_url = EXCLUDED.menu_url,
                menu_data = EXCLUDED.menu_data,
                menu_summary = EXCLUDED.menu_summary,
                scrape_timestamp = EXCLUDED.scrape_timestamp,
                scrape_method = EXCLUDED.scrape_method,
                scrape_status = EXCLUDED.scrape_status,
                error_message = EXCLUDED.error_message,
                updated_at = EXCLUDED.updated_at;
        """

        db.execute_write(query, (
            place_id,
            menu_url,
            json.dumps(menu_data),
            summary,
            datetime.now(),
            scrape_method,
            status,
            error_message,
            datetime.now()
        ))

        logger.info(f"Saved menu for place_id: {place_id}")

    except Exception as e:
        logger.error(f"Error saving menu to database: {e}")


def _save_and_return_error(place_id: str, menu_url: Optional[str], error_message: str) -> str:
    """Save error to database and return error response."""
    _save_menu_to_db(
        place_id,
        menu_url,
        {},
        "",
        "error",
        "failed",
        error_message
    )

    return json.dumps({
        "status": "failed",
        "place_id": place_id,
        "message": error_message
    })
