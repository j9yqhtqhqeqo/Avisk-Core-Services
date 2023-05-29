import os
import datetime as dt
import time
import ExtractSectionsFrom10K


PARM_LOGFILE = (r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Log/10KDocumentExtraction')
PARM_TENK_OUTPUT_PATH = (r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Extracted10K/')
PARM_SOURCE_INPUT_PATH = (r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/FormDownloads/10K/')
PARM_FORM_PREFIX = 'https://www.sec.gov/Archives/'
PARM_BGNYEAR = 1994  # User selected bgn period.  Earliest available is 1993
PARM_ENDYEAR = 1994  # User selected end period.
PARM_BGNQTR = 1  # Beginning quarter of each year
PARM_ENDQTR = 1  # Ending quarter of each year

def process10K():
    success_logfile = f'{PARM_LOGFILE}Success{dt.datetime.now().strftime("%c")}.txt'
    failure_logfile = f'{PARM_LOGFILE}Failure{dt.datetime.now().strftime("%c")}.txt'
    item_zero_logfile = f'{PARM_LOGFILE}ItemZero{dt.datetime.now().strftime("%c")}.txt'
    f_log = open(success_logfile, 'a')
    f_log.write('BEGIN LOOPS:  {0}\n'.format(time.strftime('%c')))
    total_processed =0
    errors=0
    for year in range(PARM_BGNYEAR, PARM_ENDYEAR + 1):
        for qtr in range(PARM_BGNQTR, PARM_ENDQTR + 1):

            # Setup output path
            path = '{0}'.format(PARM_SOURCE_INPUT_PATH)
            input_path = f'{PARM_SOURCE_INPUT_PATH}Year{year}Q{qtr}'
            file_list = sorted(os.listdir(input_path))
           
            #Create output directory if it does not exist
            output_file_folder = f'{PARM_TENK_OUTPUT_PATH}Year{year}Q{qtr}'
            if not os.path.exists(output_file_folder):
                os.makedirs(output_file_folder)
                print('Path: {0} created'.format(output_file_folder))

            for file in file_list:
                n_tot = 0
                input_file_path = f'{input_path}/{file}'
                output_file_path = f'{output_file_folder}/{file}'
                sec_url_clean_file_name = file.replace('-','/',1)
                sec_url = f'{PARM_FORM_PREFIX}/{sec_url_clean_file_name}'
                section_processor = ExtractSectionsFrom10K.tenKXMLProcessor()  
                success_failure = section_processor.processSingleTenKFile(f_input_file_path=input_file_path, f_output_file_path=output_file_path, f_success_log=success_logfile,f_failed_log=failure_logfile,f_item0_logile = item_zero_logfile, f_sec_url=file)
               
                if(success_failure == 1):
                    total_processed +=1
                else:
                    errors =+1

process10K()