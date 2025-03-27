parse_scorpion_xml_url_metadata <- function(scorpion_site_metadata){

  url_attributes <- c("loc",
                      "lastmod", # last time sku changed
                      "changefreq",
                      "priority" # nose
                      #"pagemap",
                      #"image"
                      )
  
    scorpion_site_url_metadata <- url_attributes |> 
      map(
        ~ scorpion_site_metadata |> 
            html_element(.x) |> 
            html_text2() |> 
            as_tibble()
      ) |> 
      list_cbind()
    
    colnames(scorpion_site_url_metadata) <- url_attributes
    
    augmented_scorpion_site_url_metadata <- scorpion_site_url_metadata |> 
      mutate(
        page_name = basename(loc),
        image_name = scorpion_site_metadata |> 
          html_element("image") |> 
          html_element('title') |> 
          html_text2()
      )
      
      
  return(augmented_scorpion_site_url_metadata)
  
}

# might want to leverage llm to catalog url type or if something is missing the ist not a product

fetch_scorpion_sitemap <- function(date_today){
  # robots txt has no guard-rails: https://www.scorpion.com.mx/robots.txt
  
  #plan(multisession, workers = 4)
  
  scorpion_sitemap <- read_html("https://www.scorpion.com.mx/pub/sitemaps/sitemap.xml") |> 
    html_elements("url") |> 
    map(
      ~ parse_scorpion_xml_url_metadata(.x)
    ) |> 
    list_rbind()
  
  
  return(scorpion_sitemap)
}



zoom_in_product_urls <- function(scorpion_sitemap){
  
  scorpion_sitemap |> 
    filter(
      !is.na(changefreq), # will also return /search by department results
      priority == "1.0" # some pages dont return anything but are still listed... why?
    ) |> 
    mutate(
      is_available = loc |> 
        map_lgl(
          ~ check_product_availability(.x)
        )
    )
  
}


#' Check Product Availability
#' 
#' This function checks if a product is available on a given URL.
#' It scrapes the webpage and looks for an "Error 404" message.
#' 
#' @param product_info_url A character string containing the URL of the product page.
#' 
#' @return A logical value indicating whether the product is available (TRUE) or not (FALSE).
#' 
#' @examples
#' check_product_availability("https://example.com/product1")
check_product_availability <- function(product_info_url){
  
  page <- read_html_live(product_info_url)
  
  if (is.na(page)) {
    return(FALSE)  # Return FALSE if the page could not be loaded
  }
  
  page_only_404_title <- page |> html_elements("h3.title") |> html_text2()
  
  not_found <- page_only_404_title == "Error 404"
  
  return(!any(not_found))  # TRUE if available, FALSE if not available
}


scrape_product_price_data <- function(product_info_url){
  
  page <- read_html_live(product_info_url)
  
  product_info_prices <- page |> 
    html_element("div.product-info-price") 
  
  precio_minorista <- product_info_prices |> 
    html_element("span.active.prodPiece") 
  
  tbl_precio_minorista <- tibble(
    unidad = precio_minorista |> 
      html_element("h4") |> 
      html_text2(),
    precio = precio_minorista |> 
      html_element("span.price") |> 
      html_text2(),
    piezas_requeridas = "1"
  )
  
  precios_mayoristas <- product_info_prices |> 
    html_elements("div.p-20-related") |> 
    map(
      ~ tibble(
        piezas_requeridas = html_element(.x, "button.prodBox") |> 
          html_attr("data-pieze"),
        precio = html_element(.x, "div.price") |> 
          html_text2() 
      )
    ) 
  
  
  product_prices_tbl <- tbl_precio_minorista |> 
    bind_rows(precios_mayoristas) |> 
    fill(unidad, .direction = "down") |> 
    mutate(
      precio = precio |> 
        str_extract("\\d+(\\.\\d+)?")
    )
  
}