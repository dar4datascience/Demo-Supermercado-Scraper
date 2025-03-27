from playwright.sync_api import sync_playwright
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm  # Import tqdm for progress bar

def py_check_product_availability(product_info_url):
    sys.sleep(5)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            page.goto(product_info_url, timeout=10000)  # 10 seconds timeout
            print(f"Now processing: {product_info_url}")

            # Extract the text of h3.title elements
            titles = page.locator("h3.title").all_text_contents()

            # Check if "Error 404" is present
            not_found = any(title.strip() == "Error 404" for title in titles)

            return product_info_url, not not_found  # Return URL and availability status
        except Exception as e:
            print(f"Error loading page: {e}", file=sys.stderr)
            return product_info_url, False  # Return False if there's an error
        finally:
            browser.close()

def check_multiple_product_availabilities(url_list):
    # Use ThreadPoolExecutor to parallelize the checking process
    results = []
    with ThreadPoolExecutor() as executor:
        # Use tqdm to add a progress bar for the parallel tasks
        futures = {executor.submit(py_check_product_availability, url): url for url in url_list}
        for future in tqdm(as_completed(futures), total=len(url_list), desc="Processing URLs"):
            _, is_available = future.result()  # Unpack the tuple but only use the 'is_available' part
            results.append(is_available)

    return results


# Example usage
# url_list = ["https://example.com/product1", "https://example.com/product2", "https://example.com/product3"]
# availability_results = check_multiple_product_availabilities(url_list)
# 
# # Print the results
# for url, is_available in availability_results:
#     print(f"URL: {url} - Available: {is_available}")

def py_scrape_product_price_data(product_info_url):
    sys.sleep(5)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            page.goto(product_info_url, timeout=10000)  # 10 seconds timeout
            print(f"Now processing: {product_info_url}")
            
            # Scrape the product prices
            product_info_prices = page.locator("div.product-info-price")
            
            # Get retail price information
            precio_minorista = product_info_prices.locator("span.active.prodPiece")
            unidad = precio_minorista.locator("h4").text_content()
            precio = precio_minorista.locator("span.price").text_content()
            
            # Prepare retail price tibble
            tbl_precio_minorista = {
                "unidad": unidad,
                "precio": precio,
                "piezas_requeridas": "1"
            }
            
            # Get wholesale prices
            precios_mayoristas = product_info_prices.locator("div.p-20-related").all()
            wholesale_prices = []
            for precio_box in precios_mayoristas:
                piezas_requeridas = precio_box.locator("button.prodBox").get_attribute("data-pieze")
                precio = precio_box.locator("div.price").text_content()
                wholesale_prices.append({
                    "piezas_requeridas": piezas_requeridas,
                    "precio": precio
                })

            # Combine the retail and wholesale prices
            all_prices = [tbl_precio_minorista] + wholesale_prices
            
            # Return the processed prices as a list of dictionaries (you can later convert to a DataFrame)
            return all_prices
            
        except Exception as e:
            print(f"Error loading page: {e}", file=sys.stderr)
            return []
        finally:
            browser.close()


def scrape_multiple_product_price_data(url_list):
    # Use ThreadPoolExecutor to parallelize the checking process
    results = []
    with ThreadPoolExecutor() as executor:
        # Use tqdm to add a progress bar for the parallel tasks
        futures = {executor.submit(py_scrape_product_price_data, url): url for url in url_list}
        for future in tqdm(as_completed(futures), total=len(url_list), desc="Processing URLs"):
            product_prices = future.result()  # Get the price data for the product
            results.append(product_prices)

    return results

# Example usage
# url_list = ["https://example.com/product1", "https://example.com/product2", "https://example.com/product3"]
# price_results = scrape_multiple_product_price_data(url_list)
# 
# # Print the results
# for result in price_results:
#     print(result)
