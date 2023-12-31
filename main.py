import os
import argparse
import yaml
from datetime import datetime
from glob import glob
from mps_report_builder import mps_reporter
from mps_report_builder import default_project_code_template
from mps_report_builder import default_excel_header_row

default_config_file = 'config.yaml'


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--excel_header_row', type=int, default=default_excel_header_row,
                        help='The excel row number which contains the project column headings.')
    parser.add_argument('--project_code_template', type=str, default=default_project_code_template,
                        help='Regex string to parse the project codes from the column headings.')
    parser.add_argument('--input_path', type=str, default='.',
                        help='path to folder containing finance reports.')
    parser.add_argument('--output_path', type=str, default='.',
                        help='path to write the outputs.')
    parser.add_argument('--config', type=str, default='config.yaml',
                        help='The path to the config file.')
    clargs = parser.parse_args()

    config = yaml.load(open(clargs.config, "r"), Loader=yaml.FullLoader)

    mps_report_builder = mps_reporter(
        config, clargs.excel_header_row, clargs.project_code_template
    )
    report_paths = glob(os.path.join(clargs.input_path, '*.xlsx'))
    if not any(report_paths):
        print(f'No finance reports found in "{clargs.input_path}".')
    else:
        report_name = f'mps_report.{datetime.today().strftime("%Y.%m.%d")}.csv'
        fname = mps_report_builder.get_mps_report(report_paths, clargs.output_path, out_fname=report_name)
        print(f'Written {fname}.') if fname else None

    print(f'Done.')
