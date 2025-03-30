import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from playwright.sync_api import sync_playwright
from tqdm import tqdm



def py_scrape_product_price_data(product_info_url):
    """Synchronous function to scrape product price data from a given URL using Playwright.
       Stores logs in a dictionary instead of printing them.
    """
    max_retries = 3
    logs = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            for attempt in range(1, max_retries + 1):
                try:
                    logs.append(f"Attempt {attempt}: Navigating to {product_info_url}")
                    page.goto(product_info_url, timeout=30000, wait_until="load")
                    logs.append("Page loaded successfully")

                    # Check if product-info-price div exists
                    product_info_prices = page.locator("div.product-info-price")
                    if not product_info_prices.is_visible():
                        raise Exception("Element div.product-info-price not found")
                    logs.append("Found product-info-price div")

                    # Scrape the retail price
                    retail_price_data = extract_retail_price(product_info_prices, logs)
                    
                    # Get wholesale prices
                    wholesale_prices = extract_wholesale_prices(product_info_prices, logs)
                    
                    all_prices = [retail_price_data] + wholesale_prices
                    return {"url": product_info_url, "prices": all_prices, "logs": logs}
                
                except Exception as e:
                    logs.append(f"Attempt {attempt} failed: {e}")
                    if attempt < max_retries:
                        logs.append("Retrying in 5 seconds...")
                        page.wait_for_timeout(5000)
                    else:
                        logs.append("Max retries reached. Returning empty list.")
                        return {"url": product_info_url, "prices": [], "logs": logs}
        
        finally:
            browser.close()


def extract_retail_price(product_info_prices, logs):
    """Extracts the retail price from the product info price section."""
    
    # Check for active.prodPiece in a span or button using either span or button
    active_prod_piece_locator = None

    if product_info_prices.locator("span.active.prodPiece").is_visible():
        active_prod_piece_locator = product_info_prices.locator("span.active.prodPiece")
    elif product_info_prices.locator("button.active.prodPiece").is_visible():
        active_prod_piece_locator = product_info_prices.locator("button.active.prodPiece")
    
    # assign correct locator
    precio_minorista = active_prod_piece_locator
    
    if not precio_minorista.is_visible():
        raise Exception("Element ctive.prodPiece not found in span nor button")
    
    unidad = precio_minorista.locator("h4")
    precio = precio_minorista.locator("span.price")
    
    if not unidad.is_visible() or not precio.is_visible():
        raise Exception("Retail price elements not found")
    
    tbl_precio_minorista = {
        "unidad": unidad.text_content().strip(),
        "precio": precio.text_content().strip(),
        "oferta": "minorista",
        "piezas_requeridas": "1"
    }
    logs.append(f"Extracted minorista price: {tbl_precio_minorista}")
    return tbl_precio_minorista


def extract_wholesale_prices(product_info_prices, logs):
    """Extracts wholesale price data from the product page."""
    precios_mayoristas = product_info_prices.locator("div.p-20-related").all()
    if not precios_mayoristas:
        logs.append("No wholesale prices found")
        return []
    
    wholesale_prices = []
    for index, precio_box in enumerate(precios_mayoristas):
        logs.append(f"Processing wholesale price box {index + 1}")

        # Check for piezas_requeridas using either span or button
        piezas_requeridas = "Unknown"
        piezas_requeridas_locator = None

        if precio_box.locator("span.prodBox").is_visible():
            piezas_requeridas_locator = precio_box.locator("span.prodBox")
        elif precio_box.locator("button.prodBox").is_visible():
            piezas_requeridas_locator = precio_box.locator("button.prodBox")
        
        if piezas_requeridas_locator:
            piezas_requeridas = piezas_requeridas_locator.nth(0).get_attribute("data-pieze") or "Unknown"
        
        # Extract price
        precio = precio_box.locator("div.price")
        if not precio.is_visible():
            logs.append(f"Warning: div.price not found in box {index + 1}")
            continue
        
        precio_text = precio.text_content().strip()

        # Extract offer subtitle
        subtitulo = precio_box.locator("label h4")
        subtitulo_text = subtitulo.inner_text().strip() if subtitulo.is_visible() else "Unknown"
        
        wholesale_prices.append({
            "piezas_requeridas": piezas_requeridas,
            "precio": precio_text,
            "oferta": subtitulo_text
        })
    
    logs.append(f"Extracted wholesale prices: {len(wholesale_prices)} items found")
    return wholesale_prices


def scrape_multiple_product_price_data(url_list):
    """ Run multiple scraping tasks in parallel using ThreadPoolExecutor. """
    results = []
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(py_scrape_product_price_data, url): url for url in url_list}
        for future in tqdm(as_completed(futures), total=len(url_list), desc="Processing URLs"):
            result = future.result()  # Get the price data and logs
            results.append(result)
    
    return results

def py_check_product_availability(product_info_url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        success = False
        attempts = 0

        while not success and attempts < 3:
            try:
                page.goto(product_info_url, timeout=30000, wait_until="networkidle")  # Increased timeout to 30s
                print(f"Now processing: {product_info_url}")
                
                # Check for the presence of required elements dynamically
                titles_locator = None
                h1_locator = None
                
                if page.locator("h3.title").is_visible():
                    titles_locator = page.locator("h3.title")
                elif page.locator("h1").is_visible():
                    h1_locator = page.locator("h1")
                
                if not titles_locator and not h1_locator:
                    raise Exception("Required elements not found on the page")
                
                titles = titles_locator.all_text_contents() if titles_locator else []
                h1_text = h1_locator.inner_text().strip() if h1_locator else ""
                
                # Check for 404 errors
                not_found_h3 = any(title.strip() == "Error 404" for title in titles)
                not_found_h1 = h1_text == "404 Not Found"
                not_found = not_found_h3 or not_found_h1
                
                success = True  # Mark success to exit loop
                return product_info_url, not not_found  # Return URL and availability status
            except Exception as e:
                attempts += 1
                print(f"Attempt {attempts}: Error loading page ({e})", file=sys.stderr)
                if attempts < 3:
                    print("Retrying in 5 seconds...")
                    page.wait_for_timeout(5000)  # Wait before retrying
        
        return product_info_url, False  # Return False if all attempts fail
    
    browser.close()


def check_multiple_product_availabilities(url_list):
    # Use ThreadPoolExecutor to parallelize the checking process
    results = []
    with ThreadPoolExecutor() as executor:
        # Use tqdm to add a progress bar for the parallel tasks
        futures = {executor.submit(py_check_product_availability, url): url for url in url_list}
        for future in tqdm(as_completed(futures), total=len(url_list), desc="Processing URLs"):
            product_info_url, is_available = future.result()  # Unpack the tuple but only use the 'is_available' part
            results.append((product_info_url,is_available))

    return results

