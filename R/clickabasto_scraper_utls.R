
fetch_clickabasto_site_map <- function(date_today){
  # robots txt has no guard-rails: https://www.clickabaston.com.mx/robots.txt
  
  #plan(multisession, workers = 4)
  #https://clickabasto.com/sitemap_products_1.xml?from=1763614621759&to=7744763428927
  
  clickabasto_site_map <- read_html("https://clickabasto.com/sitemap.xml") |> 
    html_elements("sitemap") |> 
    map(
      ~ html_element(.x, "loc") |> 
        html_text2()
    ) 
  
  # apply to cause this is too long
  clickabasto_product_site_map <- clickabasto_site_map[grepl("products", clickabasto_site_map)] |> 
    unlist() |> 
    read_html() |> 
    html_elements("url") |> 
    map(
    ~ parse_clickabaston_xml_url_metadata(.x)
    ) |> 
    list_rbind()
  
  
  return(clickabasto_product_site_map)
}


parse_clickabaston_xml_url_metadata <- function(clickabaston_site_metadata){
  
  url_attributes <- c("loc",
                      "lastmod", # last time sku changed
                      "changefreq"
  )
  
  clickabaston_site_url_metadata <- url_attributes |> 
    map(
      ~ clickabaston_site_metadata |> 
        html_element(.x) |> 
        html_text2() |> 
        as_tibble()
    ) |> 
    list_cbind()
  
  colnames(clickabaston_site_url_metadata) <- url_attributes
  
  augmented_clickabaston_site_url_metadata <- clickabaston_site_url_metadata |> 
    mutate(
      page_name = basename(loc),
      image_name = clickabaston_site_metadata |> 
        html_element("image") |> 
        html_element('title') |> 
        html_text2()
    )
  
  
  return(augmented_clickabaston_site_url_metadata)
  
}
