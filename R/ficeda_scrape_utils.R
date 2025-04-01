# data is in each "table-responsive
ficeda_fetch_data_from_tables <- function(){
  
  # data doesnt seem to be stored
  # probably requires live
  ficeda_tables <- read_html_live("http://74.208.24.179:8080/precios-consumidor/pages/general_search/created:2025-04-01/type_id:2") |> 
    html_elements(".table-responsive") |> 
    map(
      ~ html_element(.x, "table") |> 
        html_table()
    ) |> 
    list_rbind()
  
}