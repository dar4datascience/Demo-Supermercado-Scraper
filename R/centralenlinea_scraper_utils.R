fetch_centralenlinea_site_map <- function(date_today){
  # robots txt has no guard-rails: https://www.centralenlinea.com.mx/robots.txt
  
  #plan(multisession, workers = 4)
  # https://www.centralenlinea.com/categorias/frutas-y-verduras#!
  #https://www.centralenlinea.com/categorias/carnes-aves-y-pescados
  # capture <a href="/categorias/reposteria" id="373" tabindex="0">
  # Repostería y panadería
  # </a>  hrefs
  # requieres scroll down and going through menus to capture the data
  # does this need to be read live? prooably
  centralenlinea_site_map <- read_html("https://www.centralenlinea.com/") |> 
    html_elements("href") 
  
  centralenlinea_site_categories <- centralenlinea_site_map[grepl("categorias", centralenlinea_site_map)] 
  
  
  return(centralenlinea_site_categories)
}



parse_centralenlinea_xml_url_metadata <- function(centralenlinea_site_metadata){
  
  url_attributes <- c("loc",
                      "lastmod", # last time sku changed
                      "changefreq",
                      "priority" # nose
                      #"pagemap",
                      #"image"
  )
  
  centralenlinea_site_url_metadata <- url_attributes |> 
    map(
      ~ centralenlinea_site_metadata |> 
        html_element(.x) |> 
        html_text2() |> 
        as_tibble()
    ) |> 
    list_cbind()
  
  colnames(centralenlinea_site_url_metadata) <- url_attributes
  
  augmented_centralenlinea_site_url_metadata <- centralenlinea_site_url_metadata |> 
    mutate(
      page_name = basename(loc),
      image_name = centralenlinea_site_metadata |> 
        html_element("image") |> 
        html_element('title') |> 
        html_text2()
    )
  
  
  return(augmented_centralenlinea_site_url_metadata)
  
}