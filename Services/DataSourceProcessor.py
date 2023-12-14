import sys
from pathlib import Path
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))

from DBEntities.DataSourceDBEntity import DataSourceDBEntity
from DBEntities.DataSourceDBManager import DataSourceDBManager
import pdfkit
import fitz
import urllib
import ssl
import certifi
from urllib.request import urlopen
import urllib.request as request
import time
import requests
import os
import io
import datetime as dt



PARM_PDF_IN_FOLDER = (
    r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Stage0SourcePDFFiles')
PARM_PDF_OUT_FOLDER = (
    r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Stage1CleanTextFiles')
PARM_LOGFILE = (
    r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Log/DataSourceLog')


class DataSourceProcessor:

    def __init__(self, databse_context: None) -> None:
        self.document_list = []
        self.datasourceDBMgr = DataSourceDBManager(databse_context)
        self.logfile = f'{PARM_LOGFILE} {dt.datetime.now().strftime("%c")}.txt'
        self.flagged_for_review = False

    def download_webpage_as_pdf_file(self, url: str, f_name=None, f_log=None):
        try:

            # req = request.Request(url)
            # req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:106.0) Gecko/20100101 Firefox/106.0')
            # req.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8')
            # req.add_header('Accept-Language', 'en-US,en;q=0.5')

            HEADER = {'Host': 'www.sec.gov', 'Connection': 'close',
                      'Accept': 'application/json, text/javascript, */*; q=0.01', 'X-Requested-With': 'XMLHttpRequest',
                      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36',
                      }

            # SEC WEBSITE AS SOURCE
            if (url.find('www.sec.gov') > -1):
                # response = requests.get(url,headers=HEADER)
                pdfkit.from_url(url, f_name, verbose=True)

            # OTHER SOURCE
            else:
                response = requests.get(url)

                if response.status_code == 200:
                    with open(f_name, 'wb') as f:
                        f.write(response.content)
                        return 1

        except Exception as exc:
            print(f'  Failed download: URL = {url}')
            if f_log:
                f_log = open(logfile, 'a')
                f_log.write(f'  Failed download: URL = {url}\n')
                f_log.flush()
                raise exc

    def download_single_file(self, url, f_name=None, f_log=None):
        try:

            req = request.Request(url)
            req.add_header(
                'User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:106.0) Gecko/20100101 Firefox/106.0')
            req.add_header(
                'Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8')
            req.add_header('Accept-Language', 'en-US,en;q=0.5')

            with request.urlopen(req) as response:
                if response.status == 200:
                    with open(f_name, 'wb') as f:
                        f.write(response.read())
                else:
                    print(f'  Failed download: URL = {url}')
                    if f_log:
                        f_log = open(self.logfile, 'a')
                        f_log.write(f'  Failed download: URL = {url}\n')
                        f_log.flush()
                        l_except: Exception('  Failed download: URL = {url}\n')
                        raise l_except

        except Exception as exc:
            print(f'  Failed download: URL = {url}')
            print(exc)
            if f_log:
                f_log = open(self.logfile, 'a')
                f_log.write(f'  Failed download: URL = {url}\n')
                f_log.flush()
                raise exc

    def download_content_from_source_and_process_text(self):
        self.document_list = self.datasourceDBMgr.get_unprocessed_content_list()

        if (len(self.document_list) == 0):
            print(
                "All content in data source tables already processed: No New content to Download")
            return

        document: DataSourceDBEntity
        # processed_documents =[]
        for document in self.document_list:
            unique_id = document.unique_id
            company_name = document.company_name
            year = document.year
            content_type = document.content_type
            content_type_desc = document.content_type_desc
            source_type = document.source_type
            source_url = document.source_url
            processed_ind = document.processed_ind

            # File manually extracted
            if (source_type == 'file'):
                source_type_ext = 'pdf'
            else:
                source_type_ext = source_type

            print('Processing Url:', source_url)

            # Download file to the folder -- Year
            file_name = company_name + ' ' + \
                str(year)+' '+content_type_desc+'.'+source_type_ext
            l_file_location = PARM_PDF_IN_FOLDER + \
                '/' + str(year) + '/'+file_name
            try:
                # Down load file to Stage 0 -- same format as provided by source url
                if (source_type == 'pdf'):
                    self.download_single_file(
                        url=source_url, f_name=l_file_location, f_log=self.logfile)
                elif (source_type == 'webpage'):
                    self.download_webpage_as_pdf_file(
                        url=source_url, f_name=l_file_location, f_log=self.logfile)
                elif (source_type == 'file'):
                    print('Processing Manually dowloaded file')

                # Convert the downloaded file to Text Format
                ouput_folder = f'{PARM_PDF_OUT_FOLDER}/{year}'
                if not os.path.exists(ouput_folder):
                    os.makedirs(ouput_folder)

                output_file_name = company_name + ' ' + \
                    str(year)+' '+content_type_desc+'.txt'
                output_path = f'{ouput_folder}/{output_file_name}'

                doc = fitz.open(l_file_location)  # open a document
                out = open(output_path, "wb")  # create a text output
                for page in doc:  # iterate the document pages
                    text = page.get_text().encode("utf8")  # get plain text (is in UTF-8)
                    out.write(text)  # write text of page
                    # write page delimiter (form feed 0x0C)
                    out.write(bytes((12,)))
                out.close()

                # Create list of succeffully processed Files
                document.document_name = output_file_name
                # processed_documents.append(document)
                print("Successfully downloaded and processed file:"+output_file_name)
                # Add rows to t_document for all the files downloaded and successfully processed, and mark processed urls as complete

                # get file size
                self.flagged_for_review = False
                file_stats = os.stat(output_path)
                if (file_stats.st_size < 10000):
                    print(
                        f'File Size is:{file_stats.st_size} Bytes, '+'Flagged for review')
                    self.flagged_for_review = True
                self.datasourceDBMgr.add_stage1_processed_files_to_t_document(
                    document, self.flagged_for_review)

            except Exception as Exc:
                print('Failed to download file - check source url:' + source_url)
        print('Document processing complete')

    def get_unprocessed_source_document_list(self):
        return self.datasourceDBMgr.get_unprocessed_content_list()


# unprocessed_document_list = (DataSourceProcessor(
#     "Development")).get_unprocessed_source_document_list()
# print([x.as_dict() for x in unprocessed_document_list])


# l_datasource_processor = DataSourceProcessor("Test")
# l_datasource_processor.download_content_from_source_and_process_text()


# logfile = f'{PARM_LOGFILE} {dt.datetime.now().strftime("%c")}.txt'
# l_datasource_processor = DataSourceProcessor()
# l_datasource_processor.get_unprocessed_source_document_list()
# l_datasource_processor.download_content_from_source_and_process_text()

# url = 'https://www.sec.gov/Archives/edgar/data/1163165/000119312513065426/d452384d10k.htm'
# PARM_PATH_FORM_DOWNLOAD_TEST = r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/FormDownloads/testfile.txt'

# l_datasource_processor.download_webpage_as_pdf_file(url,PARM_PATH_FORM_DOWNLOAD_TEST)
# l_datasource_processor.download_single_file(url="https://d1io3yog0oux5.cloudfront.net/_7b982f54e1d755807c5fc728a7db0cfe/anteroresources/db/847/7396/esg_report/NYSE_AR_2017.pdf", f_name=file_location,f_log=logfile)
# l_datasource_processor.download_single_file(url="https://test.pdf", f_name=file_location,f_log=logfile)
