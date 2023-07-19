set CONDAPATH=C:\ProgramData\Miniconda3
set ENVNAME=mps-kpi
if %ENVNAME%==base (set ENVPATH=%CONDAPATH%) else (set ENVPATH=~\.conda\envs\%ENVNAME%)
call %CONDAPATH%\Scripts\activate.bat %ENVPATH%
Rem add command line args here
python main.py 
call conda deactivate
pause 