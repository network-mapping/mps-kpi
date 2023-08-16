import os
import re
import calendar
import numpy as np
import pandas as pd
from datetime import datetime
from enum import Enum
from dotenv import load_dotenv

load_dotenv()

default_project_code_template = os.getenv('PROJECT_CODE_TEMPLATE')
default_excel_header_row = 5
PROFIT_AND_LOSS_TITLE = 'profit and loss'
GBP_CONVERSION = 'GBP to GBP'

company_currency_conversion = {
  'Network Mapping Pty Ltd': 'AUD to GBP',
  'Network Mapping Corp': 'CAD to GBP',
  'Network Mapping Inc': 'USD to GBP',
  'Network Mapping Limited': GBP_CONVERSION
}


class ColumnNamesEnum(Enum):
    project_name = 'Project Name'
    project_code = 'Project Code'
    currency = 'Currency'
    date = 'Date'
    aud_rate = 'AUD to GBP'
    cad_rate = 'CAD to GBP'
    usd_rate = 'USD to GBP'

    @classmethod
    def columns(cls):
        return [x.value for x in list(cls)]


class FinanceCategoriesEnum(Enum):
    income = 'income'
    total_income = 'total income'
    project = 'projects'
    total_project = 'total projects'


def validate_config(config):

    if 'exchange_rates' not in config.keys():
        raise ValueError('No exchange_rates defined in config')

    if 'mps_category_mapping' not in config.keys():
        raise ValueError('No mps_category_mapping definied in config')

    for category, v in config['mps_category_mapping'].items():
        if not isinstance(v, list):
            raise ValueError(f'Found "{type(v)}", expected {type(list)} in config mps_category_mapping')


def mps_reporter(config, excel_header_row, project_regex):

    try:
        validate_config(config)
    except Exception as e:
        print('Invalid config.')
        raise

    return MPSReporter(config, excel_header_row, project_regex)


class MPSReporter(object):

    def __init__(self, config, excel_header_row, project_regex):

        self.exchange_rates = config['exchange_rates']
        self.mps_mappings = config['mps_category_mapping']
        self.finance_mappings = self.map_finance_to_mps()
        self.excel_header_row = excel_header_row
        self.project_pattern = re.compile(project_regex)

    def map_finance_to_mps(self):

        finance_mappings = {}
        for mps, finance_codes in self.mps_mappings.items():
            finance_mappings.update({
                code: mps for code in finance_codes
            })

        return finance_mappings

    @staticmethod
    def get_currency_conversion(company_name):

        if company_name not in company_currency_conversion.keys():
            raise ValueError(f'Unknown company: "{company_name}"')
        else:
            return company_currency_conversion[company_name]

    def get_conversion_rate(self, conversion, year, month):

        if conversion not in self.exchange_rates.keys():
            if conversion == GBP_CONVERSION:
                return 1.
            else:
                raise ValueError(f'Could not find "{conversion}" in exchange_rates config')
        else:
            if year not in self.exchange_rates[conversion].keys():
                raise ValueError(f'Could not find "{year}" in exchange_rates config for {conversion}')
            else:
                if month not in self.exchange_rates[conversion][year].keys():
                    raise ValueError(
                        f'Could not find "{month}" in exchange_rates config for {conversion} in {year}')
                else:
                    try:
                        rate = float(self.exchange_rates[conversion][year][month])
                    except ValueError:
                        raise ValueError(
                            f'Invalid exchange rate found in config for {conversion} in {month} {year}')

                    return rate

    def get_mps_category(self, finance_category):

        if finance_category not in self.finance_mappings.keys():
            raise ValueError(
                f'Found unmapped project cost: "{finance_category}". Add this mapping to the config.'
            )
        else:
            return self.finance_mappings[finance_category]

    @staticmethod
    def is_p_and_l_report(path):
        # get the company name, report type and date - ignore if not a p&l
        df = pd.read_excel(path, header=None)
        report = str(df.iloc[1, 0]).lower()

        return report == PROFIT_AND_LOSS_TITLE

    # check all the project cost columns are mapped
    def get_mps_project_categories(self, df):

        return self.get_category_range(
            df,
            from_category=FinanceCategoriesEnum.project.value,
            to_category=FinanceCategoriesEnum.total_project.value
        )

    # check all the project cost columns are mapped
    def get_mps_income_categories(self, df):

        return self.get_category_range(
            df,
            from_category=FinanceCategoriesEnum.income.value,
            to_category=FinanceCategoriesEnum.total_income.value
        )

    def get_category_range(self, df, from_category, to_category):

        start = np.nonzero(df.columns == from_category)
        end = np.nonzero(df.columns == to_category)

        if not np.any(start) & np.any(end):
            categories = []
        else:
            categories = [
                [cost, self.get_mps_category(cost)]
                for cost in df.columns[start[0][0]+1:end[0][0]]
            ]

        return pd.DataFrame(categories, columns=['finance', 'mps'])

    # drop columns that are not project costs or income and merge into the mps categories
    def get_mps_columns(self, df):

        pcats = self.get_mps_project_categories(df)  # check all the project cost columns are mapped
        icats = self.get_mps_income_categories(df)  # check all the project cost columns are mapped

        # merge the columns by the mps group
        finance_columns = pd.concat([pcats.finance, icats.finance]).values
        mps_columns = pd.concat([pcats.mps, icats.mps]).values
        df = df[finance_columns].T
        df['mps_code'] = mps_columns
        df = df.groupby('mps_code').sum().T

        return df

    @staticmethod
    def parse_date(datestring):

        if re.match(r'^[1-9]+-[0-9]+ [a-zA-Z]+, 20[2-9][0-9]$', datestring):  # 'day-day month, year'
            (sday, day, month, year) = re.split('-|, | ', datestring)


        elif re.match(r'^[a-zA-Z]+ [1-9]+-[0-9]+, 20[2-9][0-9]$', datestring):  # 'month day-day, year'
            (month, sday, day, year) = re.split('-|, | ', datestring)

        elif re.match(r'^[a-zA-Z]+ 20[2-9][0-9]$', datestring):  # 'month year'
            (month, year) = re.split('-|, | ', datestring)
            date = datetime.strptime(f'{month} {year}', '%B %Y')
            day = calendar.monthrange(date.year, date.month)[1]

        else:
            raise ValueError(f'Unrecognised report date format "{datestring}"')

        date = datetime.strptime(f'{day} {month} {year}', '%d %B %Y')

        return date

    def read_header_rows(self, df):

        # get the company name, report type and date - ignore if not a p&l
        company_name = str(df.iloc[0, 0])
        report = str(df.iloc[1, 0]).lower()
        datestr = str(df.iloc[2, 0])

        return company_name, report, datestr

    def convert_to_gbp(self, df, rate):

        return df[df.select_dtypes(include=['number']).columns] * rate

    def get_project_codes_and_names(self, df):

        # parse out the project code and name as separate columns
        project_codes_and_names = pd.DataFrame(
            [self.project_pattern.split(project)[1:]
             for project in df.index], columns=['code', 'name']
        )
        project_names = project_codes_and_names.name.values
        project_codes = project_codes_and_names.code.values

        return project_codes, project_names

    def import_profit_and_loss_report(self, path):

        # get the info from the header rows
        company_name, report, datestr = self.read_header_rows(pd.read_excel(path, header=None))

        # parse the date
        date = self.parse_date(datestr)
        datestr = date.strftime('%d/%m/%Y')
        month = date.strftime('%B')

        # now just get the data
        df = pd.read_excel(path, header=self.excel_header_row - 1, index_col=0)

        # get rid of columns that do not have a project code
        # ignore the final row and the empty rows before it
        # final row is something like: 'Monday, Jul 10, 2023 01:44:15 pm GMT+1 - Accrual Basis'
        project_columns = [column for column in df.columns if self.project_pattern.match(column)]
        df = df[project_columns][:-1].T
        df.columns = [str(x).lower().lstrip() for x in df.columns]

        # drop columns that are not project costs or income and merge into the mps categories
        df = self.get_mps_columns(df)

        # parse out the project code and name as separate columns
        project_codes, project_names = self.get_project_codes_and_names(df)

        # get the exchange rate and convert to GBP
        currency_conversion = self.get_currency_conversion(company_name)
        rate = self.get_conversion_rate(currency_conversion, date.year, month)
        df = self.convert_to_gbp(df, rate)

        self.add_columns(df, date, project_names, project_codes)

        print(f'Parsed {company_name} {report} {datestr} using exchange rate {rate}')

        return df

    def add_columns(self, df, date, project_names, project_codes):

        datestr = date.strftime('%d/%m/%Y')
        month = date.strftime('%B')

        # add in the dataframe specific information to the columns
        for conversion in (ColumnNamesEnum.aud_rate, ColumnNamesEnum.cad_rate, ColumnNamesEnum.usd_rate):
            df.insert(0, conversion.value, self.get_conversion_rate(conversion.value, date.year, month))
        df.insert(0, ColumnNamesEnum.currency.value, 'GPB')
        df.insert(0, ColumnNamesEnum.date.value, datestr)
        df.insert(0, ColumnNamesEnum.project_name.value, project_names)
        df.insert(0, ColumnNamesEnum.project_code.value, project_codes)

    @staticmethod
    def merge_company_mps_reports(reports):

        df = pd.concat(reports, ignore_index=True).fillna(0)
        merge_columns = [
            ColumnNamesEnum.project_code.value,
            ColumnNamesEnum.currency.value,
            ColumnNamesEnum.date.value,
            ColumnNamesEnum.aud_rate.value,
            ColumnNamesEnum.cad_rate.value,
            ColumnNamesEnum.usd_rate.value
        ]
        df = df.groupby(merge_columns).sum(numeric_only=True)

        return df

    def get_mps_report(self, finance_reports, out_folder, out_fname='mps_report.csv'):
        # parse all the xls files in a folder
        mps_reports = []
        for report in finance_reports:
            if self.is_p_and_l_report(report):
                mps_reports.append(self.import_profit_and_loss_report(report))
            else:
                print(f'WARNING: Ignoring "{report}", format does not match profit and loss report.')

        df = self.merge_company_mps_reports(mps_reports)
        fname = os.path.join(out_folder, out_fname)
        df.to_csv(fname)

        return fname


