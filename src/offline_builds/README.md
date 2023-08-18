#  MPS Report Generator

Reads in profit and loss reports generated from Quickbooks for each of the groups companies, converts them to GBP, 
maps the categories across to the desired MPS categories and merges them into a single report with one line for 
each project and date. The report builder only considers costs in the Projects section of the finance report and 
also extracts the income categories. The application will search a folder for all the .xlsx files and process the
once that have the expected format.

usage: 

    main.py [-h] [--excel_header_row EXCEL_HEADER_ROW]
                 [--project_code_template PROJECT_CODE_TEMPLATE]
                 [--input_path INPUT_PATH] [--output_path OUTPUT_PATH]
                 [--config CONFIG]

options:

    -h, --help            Show this help message and exit

    --excel_header_row EXCEL_HEADER_ROW
                          The excel row number which contains the project column headings.
                          Default = 5

    --project_code_template PROJECT_CODE_TEMPLATE
                          Regex string to parse the project codes from the column headings.
                          Default = r'(^NM[ACIL]P[0-9]+)'

    --input_path INPUT_PATH
                          The path to folder containing finance reports.
                          Default = .

    --output_path OUTPUT_PATH
                          The path to write the outputs.
                          Default = .

    --config CONFIG       The path to the config file.
                          Default = ./config.yaml

There must be an exchange rate that covers the period of each report defined in the config.yaml file:

    exchange_rates:
        AUD to GBP:
          2023:
            June: 0.52  # conversion to GPB
            July: 0.52  # conversion to GPB
            ...
        CAD to GBP:
          2023:
            June: 0.58  # conversion to GPB
            July: 0.58  # conversion to GPB
            ...
        USD to GBP:
          2023:
            June: 0.76  # conversion to GPB
            July: 0.76  # conversion to GPB
            ...

The finance categories must all be mapped to MPS categories in the `mps_category_mapping` of the config.yaml file:

    mps_category_mapping:                     
      Travel and Subsistence:                 # MPS category
        - 'accomodation'                      # Finance categories (must be a list)
        - 'accommodation'
        - 'airfares'
        - 'air fares'
        - 'car hire'
        - 'subsistence'
        - 'subsistance'
        - 'telephone'
        - 'travel'
      Aviation:                               # MPS category
         - 'aviation'                         # Finance categories
      ...