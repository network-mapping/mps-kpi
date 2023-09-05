from datetime import datetime
from glob import glob
import os
from os.path import join, dirname, realpath
from flask import Flask, request, send_file, render_template, flash, redirect,url_for
import yaml
from dotenv import load_dotenv
from mps_report_builder import mps_reporter
import zipfile
import urllib
from flask import json
from werkzeug.exceptions import HTTPException
import traceback


load_dotenv()
app = Flask(__name__,static_url_path='',static_folder='./assets')
APP_ROOT = dirname(realpath(__file__))
app.secret_key = "super secret key"
default_output_path = join(APP_ROOT,os.getenv('DEFAULT_OUTPUT_PATH') or 'outputs')
if not os.path.exists(default_output_path):
  os.makedirs(default_output_path)
  
@app.errorhandler(Exception)
def handle_exception(e):
    """Return JSON instead of HTML for HTTP errors."""
    # start with the correct headers and status code from the error
    response = e.get_response()
    # replace the body with JSON
    response.data = json.dumps({
        "code": e.code,
        "name": e.name,
        "description": traceback.format_exc().split('\n'),
    })
    response.content_type = "application/json"
    return response
  
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
         #use yaml formatted config
           
            project_code_template = os.getenv('PROJECT_CODE_TEMPLATE') or r'(^NM[ACIL]P[0-9]+)'
            excel_header_row = os.getenv('EXCEL_HEADER_ROW') or 5
            config_file = yaml.load(open(join(APP_ROOT,'config.yaml'), "r"), Loader=yaml.FullLoader)
            #gather info from uploaded reports 
            mps_report_builder = mps_reporter(config_file, excel_header_row , project_code_template)
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

@app.route('/current_config')
def current_config_download():
    return send_file(join(APP_ROOT,'config.yaml'))

def zipfolder(foldername, target_dir):            
    zipobj = zipfile.ZipFile(foldername + '.zip', 'w', zipfile.ZIP_DEFLATED)
    rootlen = len(target_dir) + 1
    for base, dirs, files in os.walk(target_dir):
        for file in files:
            fn = join(base, file)
            zipobj.write(fn, fn[rootlen:])
        for directory in dirs:
            zipobj.write(base, directory)


@app.route('/exe_download')
def exe_download():
    filename = 'src/mps-generator-offline'
    zipfolder(filename, 'src/offline_builds')
    return send_file('mps-generator-offline.zip')



@app.route('/settings/config', methods=['GET', 'POST'])
def update_config():
    if request.method == 'POST':
        new_config = request.files.get('new_config')

        new_config.save(join(APP_ROOT, 'config.yaml'))
        flash({
           "success": "Successfully updated config file"
        })
 
    return render_template('config.html')

  
if __name__ == '__main__':
    app.run(port=os.getenv('PORT'), host=os.getenv('HOST'))
