parse_scorpion_xml_url_metadata <- function(scorpion_site_metadata){

  url_attributes <- c("loc",
                      "lastmod", # last time sku changed
                      "changefreq",
                      "priority", # nose
                      "pagemap",
                      "image"
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
        page_name = basename(loc)
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
      !is.null(changefreq), # will also return /search by department results
      priority == 1 # some pages dont return anything but are still listed... why?
    )
  
}