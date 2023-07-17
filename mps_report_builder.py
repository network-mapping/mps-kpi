import os
import re
import calendar
import numpy as np
import pandas as pd
from glob import glob
from datetime import datetime

default_project_code_template = r'(^NM[ACIL]P[0-9]+)'
default_excel_header_row = 5
PROFIT_AND_LOSS_TITLE = 'profit and loss'


def validate_config(config):
    if 'companies' not in config.keys():
        raise ValueError('No companies defined in config')
    else:
        if config['companies'] is None:
            raise ValueError(f'No companies are defined in config')
        for k, v in config['companies'].items():
            if 'name' not in v.keys():
                raise ValueError(f'Company missing name: "{k}"')
            if 'currency' not in v.keys():
                raise ValueError(f'Company missing currency: "{k}"')

    if 'exchange_rates' not in config.keys():
        raise ValueError('No exchange_rates defined in config')
    else:
        for v in config['exchange_rates']:
            if 'year' not in v.keys():
                raise ValueError(f'Year missing from exchange_rates item: "{v}"')
            if 'month' not in v.keys():
                raise ValueError(f'Month missing from exchange_rates item: "{v}"')

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

        self.companies = config['companies']
        self.exchange_rates = config['exchange_rates']
        self.mps_mappings = config['mps_category_mapping']
        self.excel_header_row = excel_header_row
        self.project_pattern = re.compile(project_regex)

    def get_currency(self, company_name):

        for k, v in self.companies.items():
            if v['name'].lower() == company_name.lower():
                return v['currency']

        raise ValueError(f'Could not find "{company_name}" in config')

    def get_conversion_rate(self, company_name, year, month):

        for v in self.exchange_rates:
            if str(v['year']) == year:
                if str(v['month']).lower() == month:
                    currency = self.get_currency(company_name)
                    if currency not in v.keys():
                        raise ValueError(
                            f'"{currency}" not found in exchange_rates item: "{v}"')
                    rate = v[currency]

                    return rate, currency

        raise ValueError(f'Could not find conversion rate for "{month} {year} {company_name}" in config')

    def get_mps_category(self, cost):

        for category, v in self.mps_mappings.items():
            if cost.lower() in [x.lower() for x in v]:
                return category

        raise ValueError(f'Found unmapped cost project cost: "{cost}". Add this mapping to the config.')

    def is_p_and_l_report(self, path):
        # get the company name, report type and date - ignore if not a p&l
        df = pd.read_excel(path, header=None)
        report = str(df.iloc[1, 0]).lower()

        return report == PROFIT_AND_LOSS_TITLE

    def get_mps_project_categories(self, df):
        # check all the project cost columns are mapped
        try:
            start_project_costs = np.nonzero(df.columns == 'projects')[0][0] + 1
        except IndexError:
            raise ValueError(f'Could not find "projects" in costs categories')
        try:
            end_project_costs = np.nonzero(df.columns == 'total projects')[0][0]
        except IndexError:
            raise ValueError(f'Could not find "total projects" in costs categories')
        categories = [
            [cost, self.get_mps_category(cost)]
            for cost in df.columns[start_project_costs:end_project_costs]
        ]

        return pd.DataFrame(categories, columns=['finance', 'mps'])


    def get_mps_income_categories(self, df):
        # check all the project cost columns are mapped
        try:
            start_income = np.nonzero(df.columns == 'income')[0][0] + 1
        except IndexError:
            raise IndexError(f'Could not find "income" in costs categories')
        try:
            end_income = np.nonzero(df.columns == 'total income')[0][0]
        except IndexError:
            raise IndexError(f'Could not find "total income" in costs categories')
        categories = [
            [cost, self.get_mps_category(cost)]
            for cost in df.columns[start_income:end_income]
        ]

        return pd.DataFrame(categories, columns=['finance', 'mps'])

    # drop columns that are not project costs or income and merge into the mps categories
    def get_mps_columns(self, df):
        mps_project_categories = self.get_mps_project_categories(df)  # check all the project cost columns are mapped
        try:
            mps_income_categories = self.get_mps_income_categories(df)  # check all the project cost columns are mapped
        except IndexError:
            mps_income_categories = pd.DataFrame([], columns=['finance', 'mps'])

        # merge the columns by the mps group
        finance_columns = pd.concat([mps_project_categories.finance, mps_income_categories.finance]).values
        mps_columns = pd.concat([mps_project_categories.mps, mps_income_categories.mps]).values
        df = df[finance_columns].T
        df['mps_code'] = mps_columns
        df = df.groupby('mps_code').sum().T

        return df

    def get_date(self, val_str):
        if re.match(r'^[1-9]+-[0-9]+ [a-zA-Z]+, 20[2-9][0-9]$', val_str):  # 'day-day month, year'
            tmp = re.split(',| |-', val_str)
            date = datetime.strptime(f'{tmp[-3]} {tmp[-1]}', '%B %Y')
            day = tmp[1]

        elif re.match(r'^[a-zA-Z]+ [1-9]+-[0-9]+, 20[2-9][0-9]$', val_str):  # 'month day-day, year'
            tmp = re.split(',| |-', val_str)
            date = datetime.strptime(f'{tmp[0]} {tmp[-1]}', '%B %Y')
            day = tmp[2]

        elif re.match(r'^[a-zA-Z]+ 20[2-9][0-9]$', val_str):  # 'month year'
            date = datetime.strptime(val_str, '%B %Y')
            day = calendar.monthrange(date.year, date.month)[1]

        else:
            raise ValueError(f'Unrecognised report date format "{val_str}"')

        year = date.strftime('%Y')
        month = date.strftime('%B').lower()

        return year, month, day

    def import_profit_and_loss_report(self, path):
        # get the company name, report type and date - ignore if not a p&l
        df = pd.read_excel(path, header=None)
        company_name = str(df.iloc[0, 0]).lower()
        report = str(df.iloc[1, 0]).lower()

        if report != PROFIT_AND_LOSS_TITLE:
            raise ValueError(f'"{path}" is not the recognised profit and loss report format.')

        year, month, day = self.get_date(df.iloc[2, 0])

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

        # parse out the project code and name and add them back in as seperate columns
        projec_codes_and_names = [self.project_pattern.split(project)[1:] for project in df.index]
        tmp = pd.DataFrame(projec_codes_and_names, columns=['code', 'name'])

        # get the exchange rate and convert to GBP
        rate, currency = self.get_conversion_rate(company_name, year, month)
        df[df.select_dtypes(include=['number']).columns] *= rate

        # add in the dataframe specific information to the columns
        df.insert(0, 'Project Name', tmp.name.values)
        df.insert(0, 'Project Code', tmp.code.values)
        df.insert(0, 'Conversion Rate', rate)
        df.insert(0, 'Converted From', currency)
        df.insert(0, 'Currency', 'GBP')
        df.insert(0, 'Year', year)
        df.insert(0, 'Month', month)
        df.insert(0, 'Day', day)
        df.insert(0, 'Report', report)
        df.insert(0, 'Company', company_name)

        print(f'Parsed {company_name} {report} {month} {year} using exchange rate {rate}')

        return df

    def get_mps_report(self, folder, out_folder, out_fname='mps_report.csv'):
        # parse all the xls files in a folder
        reports = []
        for path in glob(os.path.join(folder, '*.xlsx')):
            if self.is_p_and_l_report(path):
                try:
                    reports.append(self.import_profit_and_loss_report(path))
                except Exception as e:
                    print(f'Unexpected error with report: {path} - {e}')
                    raise e
            else:
                print(f'WARNING: Ignoring "{path}", format does not match profit and loss report.')

        df = pd.concat(reports).fillna(0)
        fname = os.path.join(out_folder, out_fname)
        df.to_csv(fname)

        return df


