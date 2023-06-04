import os
import datetime as dt
import time
import DocumentProcessor
import DatabaseProcessor
import pathlib
from zipfile import ZipFile, ZIP_DEFLATED
import shutil

PARM_LOGFILE = (r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Log/10KDocumentExtraction')
PARM_TENK_OUTPUT_PATH = (r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Extracted10K/')
PARM_SOURCE_INPUT_PATH = (r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/FormDownloads/10K/')
PARM_REPROCESS_PATH = (r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/ReProcessDocHeaders/')
PARM_PROCESSED_PATH = (r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/FormDownloads/10KProcessed/')

PARM_FORM_PREFIX = 'https://www.sec.gov/Archives/'
PARM_BGNYEAR = 2022  # User selected bgn period.  Earliest available is 1993
PARM_ENDYEAR = 2022  # User selected end period.
PARM_BGNQTR = 1  # Beginning quarter of each year
PARM_ENDQTR = 4  # Ending quarter of each year



def process10K():
    summary_logfile = f'{PARM_LOGFILE}10KDocumentExtractionSummary{dt.datetime.now().strftime("%c")}.txt'
    success_logfile = f'{PARM_LOGFILE}Success{dt.datetime.now().strftime("%c")}.txt'
    failure_logfile = f'{PARM_LOGFILE}Failure{dt.datetime.now().strftime("%c")}.txt'
    item_zero_logfile = f'{PARM_LOGFILE}ItemZero{dt.datetime.now().strftime("%c")}.txt'
    f_log = open(summary_logfile, 'a')
    f_log.write('Begin Processing 10K FIles...:  {0}\n'.format(time.strftime('%c')))

    for year in range(PARM_BGNYEAR, PARM_ENDYEAR + 1):
        for qtr in range(PARM_BGNQTR, PARM_ENDQTR + 1):
            processed_all_items =0
            processed_zero_items=0
            error_processing=0
            total_items_submitted=0

            f_log.write('\tStart Processing Year:{0}  Quarter:{1}\n'.format(year, qtr))
            f_log.flush()
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
                total_items_submitted = len(file_list)
                input_file_path = f'{input_path}/{file}'
                output_file_path = f'{output_file_folder}/{file}'
                sec_url_clean_file_name = file.replace('-','/',1)
                sec_url = f'{PARM_FORM_PREFIX}/{sec_url_clean_file_name}'
 
                section_processor = DocumentProcessor.tenKDatabaseProcessor()  
                success_failure = section_processor.processSingleTenKFile(f_input_file_path=input_file_path,f_output_file_path=output_file_path, 
                                                                          f_success_log=success_logfile,f_failed_log=failure_logfile,
                                                                          f_item0_logile = item_zero_logfile, f_sec_url= sec_url , f_file_name = file)
               
                if(success_failure == 1):
                    processed_all_items +=1

                elif(success_failure == 2):
                    processed_zero_items+=1
                else:
                    error_processing =+1

            f_log = open(summary_logfile, 'a')
            f_log.write('\t\tTotal Items Submitted For Processing:{0}\n'.format(total_items_submitted))

            f_log.write('\t\tSuccess - Files fully Processd:{0}\n'.format(processed_all_items))
            f_log.write('\t\tSuccess - Files Processd as Item[0]:{0}\n'.format(processed_zero_items))
            f_log.write('\t\tFaliure  - Files Failed to Process due to errors:{0}\n'.format(error_processing))
            missed_files = total_items_submitted - processed_all_items+processed_zero_items+error_processing
            if(total_items_submitted != processed_all_items+processed_zero_items+error_processing):
                        f_log.write('\tALERT  - Files Not picked up for processing :{0}\n'.format(missed_files))

            f_log.write('\tCompleted Processing Year:{0}  Quarter:{1}\n'.format(year, qtr))
            # #Archive Processed Folder as Zip File and Remove Folder
            # try:
            #     f_log.write('\tFolder compression Start:{0}  Quarter:{1}\n'.format(year, qtr))
            #     archive_Processed_Files(input_path, f'Year{year}Q{qtr}.zip')
            #     f_log.write('\tFolder compression complete:{0}  Quarter:{1}\n'.format(year, qtr))
            # except (Exception) as exc:

            #     print(f'Error Creating Compressed Folder: {input_path}\n')
            #     f_log.write(f'{dt.datetime.now()}\n' +
            #                     f'Error Processing File: {input_path}\n')
            #     f_log.write(f'Error Details:\n' + f'{exc.args}\n\n')
            #     f_log.flush()

    f_log.write('End Processing 10K Files...:  {0}\n'.format(time.strftime('%c')))
    f_log.flush()


def process10KHeaders():
    summary_logfile = f'{PARM_LOGFILE}10KDocumentHeaderExtractionSummary{dt.datetime.now().strftime("%c")}.txt'
    success_logfile = f'{PARM_LOGFILE}Success{dt.datetime.now().strftime("%c")}.txt'
    failure_logfile = f'{PARM_LOGFILE}Failure{dt.datetime.now().strftime("%c")}.txt'
    item_zero_logfile = f'{PARM_LOGFILE}ItemZero{dt.datetime.now().strftime("%c")}.txt'
    f_log = open(summary_logfile, 'a')
    f_log.write('Begin Processing 10K FIles...:  {0}\n'.format(time.strftime('%c')))

    section_processor = DatabaseProcessor.tenKDatabaseProcessor()

    for year in range(PARM_BGNYEAR, PARM_ENDYEAR + 1):
        for qtr in range(PARM_BGNQTR, PARM_ENDQTR + 1):
            processed_all_items =0
            processed_zero_items=0
            error_processing=0
            total_items_submitted=0

            f_log.write('\tStart Processing Year:{0}  Quarter:{1}\n'.format(year, qtr))
            f_log.flush()
            # Setup output path
            path = '{0}'.format(PARM_SOURCE_INPUT_PATH)
            input_path = f'{PARM_SOURCE_INPUT_PATH}Year{year}Q{qtr}'
            file_list = sorted(os.listdir(input_path))
           
            #Create output directory if it does not exist
            output_file_folder = f'{PARM_TENK_OUTPUT_PATH}Year{year}Q{qtr}'
            if not os.path.exists(output_file_folder):
                os.makedirs(output_file_folder)
                print('Path: {0} created'.format(output_file_folder))

            currenct_row_count = 1 
            total_count =0 
            for file in file_list:
                if(currenct_row_count == 101):
                    currenct_row_count = 1
                else:
                    currenct_row_count += 1
                total_count +=1
                
                total_items_submitted = len(file_list)
                input_file_path = f'{input_path}/{file}'
                output_file_path = f'{output_file_folder}/{file}'
                sec_url_clean_file_name = file.replace('-','/',1)
                sec_url = f'{PARM_FORM_PREFIX}/{sec_url_clean_file_name}'
 
                # current_document_seed = section_processor.getCurrentDocumentSeedFromDatabase()
                section_processor.initProcessorParams(f_input_file_path=input_file_path,f_output_file_path=output_file_path, 
                                                                                                  f_success_log=success_logfile,f_failed_log=failure_logfile,
                                                                                                  f_item0_logile = item_zero_logfile, f_sec_url= sec_url , f_document_name = file, 
                                                                                                  b_process_hader_only=True,d_reporting_year=year, d_reporting_quarter=qtr, b_bulk_mode=True)
                try:
                   
                    if(total_count == total_items_submitted):
                        section_processor.processDocumentHeader(currenct_row_count, last_batch=True)
                    else:
                        section_processor.processDocumentHeader(currenct_row_count)

                    #Archive Processed Files    
                    processed_path_folder = f'{PARM_PROCESSED_PATH}Year{year}Q{qtr}'

                    if not os.path.exists(processed_path_folder):
                        os.makedirs(processed_path_folder)
            
                    processed_path = f'{processed_path_folder}/{file}'
                    os.rename(input_file_path,processed_path)


                except (Exception) as exc:
                    error_processing =+1
                    print(f'Error Processing File: = {input_file_path}\n')
                    if failure_logfile:
                        f_log = open(failure_logfile, 'a')
                        f_log.write(f'{dt.datetime.now()}\n' +
                                    f'Error Processing File: {input_file_path}\n')
                        f_log.write(f'Error Details:\n' + f'{exc.args}\n\n')
                        f_log.flush()
                
                print(f'{dt.datetime.now()}' +  f'Total Files Processed Sofar:' +f'{total_count} of {total_items_submitted}\n' )     

                processed_all_items +=1
                
            f_log = open(summary_logfile, 'a')
            f_log.write('\t\tTotal Items Submitted For Processing:{0}\n'.format(total_items_submitted))

            f_log.write('\t\tSuccess - Files fully Processd:{0}\n'.format(processed_all_items))
            f_log.write('\t\tSuccess - Files Processd as Item[0]:{0}\n'.format(processed_zero_items))
            f_log.write('\t\tFaliure  - Files Failed to Process due to errors:{0}\n'.format(error_processing))
            missed_files = total_items_submitted - processed_all_items+processed_zero_items+error_processing
            if(total_items_submitted != processed_all_items+processed_zero_items+error_processing):
                        f_log.write('\tALERT  - Files Not picked up for processing :{0}\n'.format(missed_files))

            f_log.write('\tCompleted Processing Year:{0}  Quarter:{1}\n'.format(year, qtr))
           
    f_log.write('End Processing 10K Files...:  {0}\n'.format(time.strftime('%c')))
    f_log.flush()


def archive_Processed_Files(directory_path:str, zip_file_name:str):
   
   # Archive folder and create a zip file
    directory = pathlib.Path(directory_path)
    archive_location = PARM_SOURCE_INPUT_PATH+''+zip_file_name
    print(archive_location)
    with ZipFile(archive_location, "w", ZIP_DEFLATED, compresslevel=9) as archive:
        for file_path in directory.rglob("*"):
            archive.write(file_path, arcname=file_path.relative_to(directory))
            print("Zipped File:", file_path)
    #Remvove Processed Folder        
    shutil.rmtree(directory_path)


# process10K()

process10KHeaders()
#archive_Processed_Files('/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/FormDownloads/10K/TobeZipped')