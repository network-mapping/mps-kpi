from datetime import datetime
from glob import glob
import os
from os.path import join, dirname, realpath
from flask import Flask, request, send_file, render_template, flash
import yaml
from dotenv import load_dotenv
from mps_report_builder import mps_reporter
import json
import urllib

load_dotenv()
app = Flask(__name__,static_url_path='',static_folder='./assets')
APP_ROOT = dirname(realpath(__file__))
downloads = []
app.secret_key = "super secret key"


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/mps/report/run', methods=['POST'])
def run_report():
    
    if request.method == 'POST':
    
        # Get the list of files from webpage
        reports = request.files.getlist("reports")
        # save reports to disk
        [report.save(join(APP_ROOT,'uploads/',f'{report.filename}')) for report in reports]
        #set the paths to point to the uploaded reports
        report_paths = [join(APP_ROOT,'uploads/',f'{report.filename}') for report in reports]

        #set user overrides   
        user_provided_config = yaml.safe_load(request.form.get('config')) #use json formatted config
        excel_header_row = int(request.form.get('excel_header_row'))
        project_code_template = os.getenv('PROJECT_CODE_TEMPLATE')
       
        #gather info from uploaded reports 
        mps_report_builder = mps_reporter(user_provided_config, excel_header_row, project_code_template)

        if not any(report_paths):
          return f'No finance reports found in uploaded files'
        else:
            report_name = f'mps_report.{datetime.today().strftime("%Y.%m.%d")}.csv'
            fname = mps_report_builder.get_mps_report(report_paths, join(APP_ROOT, 'outputs'), out_fname=report_name)
            print(fname)
            
            downloads.append(
              {
                "link": urllib.parse.quote(fname, safe=''),
                "name":report_name
              }
            )
            flash('Analysis complete click Download to get your report!')
            return render_template('index.html', form={}, downloads=downloads)
          
        

@app.route('/finance_download/<filename>')
def finance_download(filename):
    return send_file(urllib.parse.unquote(filename))

@app.route('/example_config')
def example_config_download():
    return send_file(join(APP_ROOT,'config.yaml'))
  
if __name__ == '__main__':
    app.run(port=os.getenv('PORT'), host=os.getenv('HOST'))
