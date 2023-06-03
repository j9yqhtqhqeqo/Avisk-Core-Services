
# This program downloads all Master Index files from SEC site#
import datetime as dt
import io
import os
import requests
import sys
import time
from urllib.request import urlopen
import pandas as pd
import re
import time

PARM_BGNYEAR = 2022  # User selected bgn period.  Earliest available is 1993
PARM_ENDYEAR = 2022 # User selected end period.
PARM_BGNQTR = 1  # Beginning quarter of each year
PARM_ENDQTR = 4  # Ending quarter of each year
# Path where you will store the downloaded files
PARM_PATH_INDEX_DOWNLOAD = r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/IndexDownloads'
PARM_PATH_PROCESSED_FILES = r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/ProcessedIndexFiles'
PARM_PATH_FORM_DOWNLOAD = r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/FormDownloads'

# Change the file pointer below to reflect your location for the log file
#    (directory must already exist)
PARM_LOGFILE = (r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Log/EdgarDownload' +
                str(PARM_BGNYEAR) +'Q'+str(PARM_BGNQTR) + '-' + str(PARM_ENDYEAR) +'Q'+str(PARM_ENDQTR))
# EDGAR parameter
PARM_FORM_PREFIX = 'https://www.sec.gov/Archives/'
PARM_MASTERIDX_PREFIX = 'https://www.sec.gov/Archives/edgar/full-index/'

HEADER = {'Host': 'www.sec.gov', 'Connection': 'close',
          'Accept': 'application/json, text/javascript, */*; q=0.01', 'X-Requested-With': 'XMLHttpRequest',
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36',
          }


def download_single_file(url, f_name=None, f_log=None, number_of_tries=5, sleep_time=5):
    logfile = f'{PARM_LOGFILE} {dt.datetime.now().strftime("%c")}.txt'
    try:
        response = requests.get(url, headers=HEADER)
        if response.status_code == 200:
            # file_list = io.StringIO(response.content.decode(encoding="UTF-8", errors='ignore' )).readlines()
            with open(f_name, 'wb') as f:
                f.write(response.content)
                return 1
        else:
            print(f'  Failed download: URL = {url}')
            if f_log:
                f_log = open(logfile, 'a')
                f_log.write(f'  Failed download: URL = {url}\n')
                f_log.flush()
            return -1

    except Exception as exc:
        print(f'  Failed download: URL = {url}')
        if f_log:
            f_log = open(logfile, 'a')
            f_log.write(f'  Failed download: URL = {url}\n')
            f_log.flush()
        return -1


def download_index_files():

    # Download each year/quarter master.idx and save record for requested forms

    logfile = f'{PARM_LOGFILE} {dt.datetime.now().strftime("%c")}.txt'
    f_log = open(logfile, 'a')
    f_log.write('BEGIN LOOPS:  {0}\n'.format(time.strftime('%c')))
    n_tot = 0
    n_errs = 0
    for year in range(PARM_BGNYEAR, PARM_ENDYEAR + 1):
        for qtr in range(PARM_BGNQTR, PARM_ENDQTR + 1):
            startloop = dt.datetime.now()
            n_qtr = 0
            file_count = dict()
            # Setup output path
            path = '{0}'.format(PARM_PATH_INDEX_DOWNLOAD)
            if not os.path.exists(path):
                os.makedirs(path)
                print('Path: {0} created'.format(path))
            # Build master index URL
            sec_url = f'{PARM_MASTERIDX_PREFIX}{year}/QTR{qtr}/master.idx'
            file_name = '{0}/{1}{2}{3}{4}{5}'.format(
                path, "Year", year, "Q", qtr, '.txt')
            files_downloaded = download_single_file(sec_url, file_name)
            if files_downloaded == 1:
                n_qtr = n_qtr + 1
                n_tot = n_tot + 1
                print(f'{year} : {qtr} -> {files_downloaded:,} downloads completed.  Time = ' +
                      f'{(dt.datetime.now() - startloop)}' +
                      f' | {dt.datetime.now()}')
                f_log.write(f'{year} | {qtr} | n_qtr = {n_qtr:>8,} | n_tot = {n_tot:>8,} | n_err = {n_errs:>6,} | ' +
                            f'{dt.datetime.now()}')
                f_log.flush()
            else:
                f_log.write(f'{year} | {qtr} | n_qtr = "Error" | n_tot = {n_tot:>8,} | n_err = {n_errs:>6,} | ' +
                            f'{dt.datetime.now()}')

        f_log.write('\n')

    print('{0:,} total forms downloaded.'.format(n_tot))
    f_log.write('\n{0:,} total forms downloaded.'.format(n_tot))


def download_sec_forms(form_type):
    # Get list of file from Index Down Loads

    success_logfile = f'{PARM_LOGFILE} {dt.datetime.now().strftime("%c")}Success.txt'
    print(success_logfile)
    failure_logfile = f'{PARM_LOGFILE} {dt.datetime.now().strftime("%c")}Failure.txt'
    print(failure_logfile)
    f_log = open(success_logfile, 'a')
    f_log_failure = open(failure_logfile, 'a')
   
    n_err = 0

    
    file_list = sorted(os.listdir(PARM_PATH_INDEX_DOWNLOAD))

    print(file_list)

    for file in file_list:
        n_tot = 0
        filepath = f'{PARM_PATH_INDEX_DOWNLOAD}/{file}'
        processed_file_path = f'{PARM_PATH_PROCESSED_FILES}/{file}'
        # print(filepath)
        # print(processed_file_path)
        if(file == '.DS_Store'):
            print('skipping system temp file')
        else:
            with open(filepath) as fread:
                text_lines = fread.readlines()
                text_lines_clean = text_lines[11:]
                
                linecount = len(re.findall('10-K', str(text_lines_clean)))

                print(f'Found {linecount} occurances')
                
                for lineitem in text_lines_clean:

                    files_downloaded = 0
                    file_exists = False

                    linedesc = IndexDescriptors(lineitem.strip())
                    sec_url = f'{PARM_FORM_PREFIX}/{linedesc.path}'
                    if(len(re.findall('10-K', linedesc.form)) >0 ):

                        # # Download 10K
                        download_path = '{0}/10K/{1}'.format(PARM_PATH_FORM_DOWNLOAD,file.strip(".txt"))
                        #print(download_path)
                        if not os.path.exists(download_path):
                            os.makedirs(download_path)
                            print('Path: {0} created'.format(download_path))
                        file_location = "{0}/{1}".format(download_path, linedesc.fileName)
                        if(os.path.isfile(file_location)):
                            file_exists = True
                        else:
                            files_downloaded = download_single_file(sec_url, file_location)

                        if files_downloaded == 1:
                            n_tot = n_tot + 1
                            print(f'{n_tot} of {linecount}:download completed for {linedesc.path}:.  Time = ' +
                                f' | {dt.datetime.now()}')
                            f_log.write(f'{n_tot} of {linecount}:download completed for {linedesc.path}:.  Time = ' +
                                f' | {dt.datetime.now()}')
                            f_log.write('\n')
                            f_log.flush()
                        elif files_downloaded == -1:
                            f_log_failure.write(f'download failed for {linedesc.path}:.  Time = ' +
                                f' | {dt.datetime.now()}')
                            f_log_failure.write('\n')
                            f_log_failure.flush()
                        elif file_exists == True:
                            n_tot = n_tot + 1
                            print(f'{n_tot} of {linecount}:download completed: This file already exists - {linedesc.path}:.  Time = ' +
                                f' | {dt.datetime.now()}')
                            f_log.write(f'{n_tot} of {linecount}:download completed:This file already exists -  {linedesc.path}:.  Time = ' +
                                f' | {dt.datetime.now()}')
                            f_log.write('\n')
                            f_log.flush()
                    # time.sleep(0.001)

                    # print(file_location)
                    # print(sec_url)
                    # print(linedesc.form)
        # print(f'{n_tot} of {linecount}:download completed for {linedesc.path}:.  Time = ' +
        # f' | {dt.datetime.now()}')
        # download_path = '{0}/10K/{1}'.format(PARM_PATH_FORM_DOWNLOAD,file.strip(".txt"))
        # print(download_path)
        os.rename(filepath,processed_file_path)
            

class IndexDescriptors:
    def __init__(self, line):
        self.err = False
        parts = line.strip('\n').split('|')
        if len(parts) == 5:
            self.cik = int(parts[0])
            self.name = parts[1]
            self.form = parts[2]
            self.filingdate = int(parts[3].replace('-', ''))
            self.path = parts[4]
            self.fileName = self.getFileName()
        else:
            self.err = True
        return
    
    def getFileName(self):
        parts = self.path.split('/')
        length = len(parts)
        file_name = str(self.cik)+"-"+parts[length-1]
        return file_name



f_10K = ['10-K', '10-K405', '10KSB', '10-KSB', '10KSB40']
f_10KA = ['10-K/A', '10-K405/A', '10KSB/A', '10-KSB/A', '10KSB40/A']
f_10KT = ['10-KT', '10KT405', '10-KT/A', '10KT405/A']

tenKlist = f_10K + f_10KA + f_10KT
download_sec_forms(tenKlist)

# print(tenKlist)

# if(str in tenKlist):
#     print("Success")
# else:
#     print("Failure")