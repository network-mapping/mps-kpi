from datetime import datetime
from glob import glob
import os
from os.path import join, dirname, realpath
from flask import Flask, request, send_file, render_template, flash, redirect,url_for
import yaml
from dotenv import load_dotenv
from mps_report_builder import mps_reporter
import json
import urllib

load_dotenv()
app = Flask(__name__,static_url_path='',static_folder='./assets')
APP_ROOT = dirname(realpath(__file__))
app.secret_key = "super secret key"
default_output_path = join(APP_ROOT,os.getenv('DEFAULT_OUTPUT_PATH') or 'outputs')
if not os.path.exists(default_output_path):
  os.makedirs(default_output_path)

@app.route('/')
def index():
    return render_template('index.html', form=request.args.get('form') or {}, downloads=request.args.get('downloads'))

@app.route('/api/mps/report/run', methods=['POST'])
def run_report():
    
    if request.method == 'POST':
    
        # Get the list of files from webpage
        reports = request.files.getlist("reports")
       
        # save reports to disk
        for report in reports:
           if not report.filename:
            flash({"error":'You must submit reports!'})
            return redirect(url_for('index'))
        else:
          report.save(join(APP_ROOT,'uploads/',f'{report.filename}'))
          
        #set the paths to point to the uploaded reports
        report_paths = [join(APP_ROOT,'uploads/',f'{report.filename}') for report in reports]

       
 
       
        if not any(report_paths):
          return f'No finance reports found in uploaded files'
        else:
               
            #set user overrides   
            user_provided_config = yaml.safe_load(request.form.get('config')) #use yaml formatted config
            if not user_provided_config:
              flash({"error":'You must submit a config file!'})
              return redirect(url_for('index'))
            excel_header_row_input = request.form.get('excel_header_row')
            if not excel_header_row_input:
              flash({"error":'You must provide a excel row header (the default is 5)!'})
              return redirect(url_for('index'))
            excel_header_row = int(excel_header_row_input)
            project_code_template = os.getenv('PROJECT_CODE_TEMPLATE') or r'(^NM[ACIL]P[0-9]+)'
          
            #gather info from uploaded reports 
            mps_report_builder = mps_reporter(user_provided_config, excel_header_row, project_code_template)
            # set report name
            report_name = f'mps_report.{datetime.today().strftime("%Y.%m.%d")}.csv'
            # build report and return its path
            fname = mps_report_builder.get_mps_report(report_paths, join(APP_ROOT, 'outputs'), out_fname=report_name)
            print(fname)
            # send success message to user with download link
            flash(
              {
              "text":"Analysis complete click Download to get your report!",
              "download_link": urllib.parse.quote(fname, safe=''),
              "download_name": report_name
              }
              )
            # return render_template('index.html', form={}, downloads=downloads)
            return redirect(url_for('index'))
        

@app.route('/finance_download/<filename>')
def finance_download(filename):
    return send_file(urllib.parse.unquote(filename))

@app.route('/example_config')
def example_config_download():
    return send_file(join(APP_ROOT,'config.yaml'))
  
if __name__ == '__main__':
    app.run(port=os.getenv('PORT'), host=os.getenv('HOST'))
