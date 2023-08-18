import os
from os.path import join, dirname, realpath
import argparse
import yaml
from datetime import datetime
from glob import glob
from mps_report_builder import mps_reporter
from mps_report_builder import default_project_code_template
from mps_report_builder import default_excel_header_row
from dotenv import load_dotenv




if __name__ == '__main__':
    load_dotenv()
    APP_ROOT = dirname(realpath(__file__))
  
    default_config_file = join(APP_ROOT,os.getenv('DEFAULT_CONFIG_FILE') or 'config.yaml' )
    default_input_path =  join(APP_ROOT,os.getenv('DEFAULT_INPUT_PATH') or 'uploads')
    default_output_path = join(APP_ROOT,os.getenv('DEFAULT_OUTPUT_PATH') or 'outputs')
    if not os.path.exists(default_output_path):
        os.makedirs(default_output_path)
    print(f'Using Config: {default_config_file}')
    print(f'Using Input Dir: {default_input_path}')
    print(f'Using Output Dir: {default_output_path}')

    parser = argparse.ArgumentParser()
    parser.add_argument('--excel_header_row', type=int, default=default_excel_header_row,
                        help='The excel row number which contains the project column headings.')
    parser.add_argument('--project_code_template', type=str, default=default_project_code_template,
                        help='Regex string to parse the project codes from the column headings.')
    parser.add_argument('--input_path', type=str, default=default_input_path,
                        help='path to folder containing finance reports.')
    parser.add_argument('--output_path', type=str, default=default_output_path,
                        help='path to write the outputs.')
    parser.add_argument('--config', type=str, default=default_config_file,
                        help='The path to the config file.')
    clargs = parser.parse_args()

    config = yaml.load(open(clargs.config, "r"), Loader=yaml.FullLoader)

    mps_report_builder = mps_reporter(
        config, clargs.excel_header_row, clargs.project_code_template
    )
    report_paths = glob(join(clargs.input_path, '*.xlsx'))
    if not any(report_paths):
        print(f'No finance reports found in "{clargs.input_path}".')
    else:
        report_name = f'mps_report.{datetime.today().strftime("%Y.%m.%d")}.csv'
        fname = mps_report_builder.get_mps_report(report_paths, clargs.output_path, out_fname=report_name)
        print(f'Written {fname}.')

    print(f'Done.')
