import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from playwright.sync_api import sync_playwright
from tqdm import tqdm

def py_scrape_product_price_data(product_info_url):
    """ Synchronous function to scrape product price data from a given URL using Playwright.
        Stores logs in a dictionary instead of printing them.
    """
    max_retries = 3
    logs = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for attempt in range(1, max_retries + 1):
            try:
                logs.append(f"Attempt {attempt}: Navigating to {product_info_url}")
                page.goto(product_info_url, timeout=30000, wait_until="load")
                logs.append("Page loaded successfully")

                # Check if product-info-price div exists
                product_info_prices = page.locator("div.product-info-price")
                if not product_info_prices.count():
                    raise Exception("Element div.product-info-price not found")
                logs.append("Found product-info-price div")

                # Scrape the retail price
                precio_minorista = product_info_prices.locator("span.active.prodPiece")
                if not precio_minorista.count():
                    raise Exception("Element span.active.prodPiece not found")

                unidad = precio_minorista.locator("h4")
                if not unidad.count():
                    raise Exception("Element h4 inside minorista not found")
                precio = precio_minorista.locator("span.price")
                if not precio.count():
                    raise Exception("Element span.price inside minorista not found")

                unidad_text = unidad.text_content()
                precio_text = precio.text_content()

                tbl_precio_minorista = {
                    "unidad": unidad_text,
                    "precio": precio_text,
                    "oferta": "minorista",
                    "piezas_requeridas": "1"
                }
                logs.append(f"Extracted minorista price: {tbl_precio_minorista}")

                # Get wholesale prices
                precios_mayoristas = product_info_prices.locator("div.p-20-related").all()
                if not precios_mayoristas:
                    logs.append("No wholesale prices found")

                wholesale_prices = []
                for index, precio_box in enumerate(precios_mayoristas):
                    logs.append(f"Processing wholesale price box {index + 1}")

                    piezas_requeridas = precio_box.locator("span.prodBox").get_attribute("data-pieze")
                    if piezas_requeridas is None:
                        logs.append(f"Warning: piezas_requeridas not found in box {index + 1}")
                        piezas_requeridas = "Unknown"

                    precio = precio_box.locator("div.price")
                    if not precio.count():
                        logs.append(f"Warning: div.price not found in box {index + 1}")
                        continue  # Skip this entry
                    precio_text = precio.text_content()

                    subtitulo = precio_box.locator("label h4")
                    subtitulo_text = "Unknown" if not subtitulo.count() else subtitulo.inner_text()

                    wholesale_prices.append({
                        "piezas_requeridas": piezas_requeridas,
                        "precio": precio_text,
                        "oferta": subtitulo_text
                    })

                logs.append(f"Extracted wholesale prices: {len(wholesale_prices)} items found")

                all_prices = [tbl_precio_minorista] + wholesale_prices
                return {"url":product_info_url, "prices": all_prices, "logs": logs}

            except Exception as e:
                logs.append(f"Attempt {attempt} failed: {e}")
                if attempt < max_retries:
                    logs.append("Retrying in 5 seconds...")
                    page.wait_for_timeout(5000)
                else:
                    logs.append("Max retries reached. Returning empty list.")
                    return {"prices": [], "logs": logs}

        browser.close()

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
                
                # Extract the text of h3.title elements
                titles = page.locator("h3.title").all_text_contents()
                
                # Check if "Error 404" is present
                not_found = any(title.strip() == "Error 404" for title in titles)
                
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

