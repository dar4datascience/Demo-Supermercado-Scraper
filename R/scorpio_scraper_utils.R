
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

fetch_scorpio_site_map <- function(date_today){
  # robots txt has no guard-rails: https://www.scorpion.com.mx/robots.txt
  
  #plan(multisession, workers = 4)
  
  scorpio_site_map <- read_html("https://www.scorpion.com.mx/pub/sitemaps/sitemap.xml") |> 
    html_elements("url") |> 
    map(
      ~ parse_scorpion_xml_url_metadata(.x)
    ) |> 
    list_rbind()
  
  
  return(scorpio_site_map)
}


progressive_py_check_product_availability <- function(url_vector) {
  # # Set up the progressor
  # p <- progressr::progressor(along = url_vector)
  # 
  # # Initialize the vector to store the results
  # product_price_information <- logical(length(url_vector))  # Assuming boolean results
  
  # Set a "plan" for how the code should run.
  
  p <- progressor(steps = length(url_vector))

  product_price_information <- future_map(url_vector,
                                          py_check_product_availability,
                                          p = p)
  
  # # Iterate over the URLs and apply the function
  # for (kk in seq_along(url_vector)) {
  #   result <- py_check_product_availability(url_vector[kk])  # Assuming this is how the function is used
  #   product_price_information[kk] <- result
  #   
  #   # Update progress
  #   p()
  # }
  # 
  return(product_price_information)
}


zoom_in_product_urls <- function(scorpio_site_map){
  
  scorpio_zoomed_product_urls <- scorpio_site_map |> 
    filter(
      !is.na(changefreq), # will also return /search by department results
      priority == "1.0" # some pages dont return anything but are still listed... why?
    ) 
    
  
  #plan(multisession, workers = 4)
  
  #with_progress({
  
  zoom_product_availability <- scorpio_zoomed_product_urls$loc |> 
    check_multiple_product_availabilities()
  


  #})
    
return(zoom_product_availability)
  
}

augment_product_availability <- function(scorpio_site_map, zoom_product_availability) {
  
  scorpio_zoomed_product_urls <- scorpio_site_map |> 
    filter(
      !is.na(changefreq), # will also return /search by department results
      priority == "1.0"   # some pages don't return anything but are still listed... why?
    ) 
  
  # Correct the mapping over the list
  product_availability_df <- map_df(zoom_product_availability, ~ as_tibble(setNames(.x, c("url", "is_available"))))
  
  aug_scorpio_zoomed_product_urls <- scorpio_zoomed_product_urls |> 
    left_join(product_availability_df, join_by(loc == url))
  
  return(aug_scorpio_zoomed_product_urls)
}

fetch_product_price_information <- function(aug_scorpio_zoomed_product_urls){
  
  # COULD OPTIMZE BY UNIFYING CHECKING IF ITS AVAILABLE WITH FETCHING THE INFORMATION
 product_price_information_url <- aug_scorpio_zoomed_product_urls |> 
   filter(is_available == TRUE) |> 
   pull(loc) 
 
 
 product_price_information <- scrape_multiple_product_price_data(product_price_information_url)
  
  return(product_price_information)
}

custom_name_repair <- function(names) {
  sub("^prices\\$", "", names)  # Remove "prices$" prefix from column names
}

transform_to_dataframe <- function(scorpio_product_record){
  
  tibble(
    url = scorpio_product_record$url,
    prices = scorpio_product_record$price |>
      map(as_tibble) |>
      list_rbind(),
    logs = scorpio_product_record$logs |> 
         glue_collapse(sep = '\n')
        
      
  ) 
  
}


augment_product_price <- function(aug_scorpio_zoomed_product_urls, scorpio_product_price_information) {
  
  expanded_scorpio_product_price_information <- scorpio_product_price_information |> 
    map(
      ~ transform_to_dataframe(.x)
    ) |> 
    list_rbind() |> 
    group_by(url, logs) |> 
    mutate(
      prices = prices |> 
            fill(unidad, .direction = "down")
    ) |> 
    nest(prices = prices) |> 
    mutate(
      has_prices = if_else(is.null(prices), FALSE, TRUE)
    )
  
  # there are missing producsts cause we had 938 and 896 have returned
  
  # this returns all urls with the logs
  all_products <- scorpio_product_price_information |> 
    map(
    \(x)  tibble(
      url = pluck(x, "url"),
      logs = pluck(x, "logs")
    ) |> 
      mutate(
        logs = logs |> 
          glue_collapse(sep = '\n')
      )
    ) |> 
    list_rbind() 

  augmented_product_price <- aug_scorpio_zoomed_product_urls |> 
    filter(is_available == TRUE) |> 
    left_join(expanded_scorpio_product_price_information,
              join_by(loc == url)) |> 
    full_join(all_products,
              join_by(loc == url)) |> 
    mutate(
      logs = coalesce(logs.x, logs.y)
    ) |> 
    select(!c(logs.x, logs.y)) |> 
    distinct() |> 
    mutate(
      has_prices = if_else(is.na(has_prices), FALSE, TRUE)
    )
  
  return(augmented_product_price)
}
