############################################################################################################
# SEC Sections: ITEM1,ITEM1A,ITEM1B,ITEM2,ITEM3,ITEM4,ITEM5,ITEM6,ITEM7,ITEM7A,ITEM8,ITEM9,ITEM9A,ITEM9B,
#              ITEM9C,ITEM10,ITEM11,ITEM12,ITEM13,ITEM14,ITEM15,ITEM16
#
############################################################################################################


from bs4 import BeautifulSoup
import re
import pandas as pd
import os
import datetime as dt
import time


class formItem:
    def __init__(self) -> None:
        self.form_Elements = []
        self.hierarchy = 0
        self.item_text=' '
        self.selected_item_name: str
        self.start_index = 0
        self.end_index = 0

    def add_Element(self, hierarchy=0, item_name='', start=0, end=0):
        self.form_Elements.append(formItemElement(item_name, start, end))
        self.hierarchy = hierarchy
        self.selected_item_name = item_name.replace('<LINESEP>', '')

    def populate_section_text(self, preprocesseddata):
        pass

    def print_details(self):
        for ele in self.form_Elements:
            print('Name:' + ele.item_name)
            print('Start:' + str(ele.start))
            print('End:' + str(ele.end))


class formItemElement:
    def __init__(self,  item_name, start, end):
        self.err = False

        if (item_name):
            self.item_name = item_name
            self.start = start
            self.end = end
        else:
            self.err = True
        return


class ItemsNotProcssedError(Exception):

    def __init__(self, ErrorMessage) -> None:
        super().__init__(ErrorMessage)
        self.ErrorMessage = ErrorMessage

    def getErrorMessage(self):
        return self.ErrorMessage


class tenKProcessor:

    def __init__(self) -> None:
        self.data_cleanup_complete = False
        self.clean_data_as_text: str
        self.final_itemized_data: str
        self.document_header: str
        self.header_text: str
        self.final_xml: str

        self.d_reporting_year:int
        self.d_reporting_quarter:int
        self.b_process_hader_only = False

        self.f_input_file_path: str
        self.f_output_file_path: str
        self.f_success_log: str
        self.f_failed_log: str
        self.f_sec_url: str
        self.f_item0_logile: str
        self.f_document_name:str
       
        self.b_bulk_mode:bool
        self.b_last_batch:bool



        self.conformed_name:str
        self.standard_industry_classification:str
        self.irs_number = 0
        self.state_of_incorporation:str 
        self.fiscal_year_end:str 
        self.form_type:str
        self.street_1:str
        self.city:str 
        self.state:str 
        self.zip:str



        self.filtered_item_list = []
        self.form_item1 = formItem()
        self.form_item1A = formItem()
        self.form_item1B = formItem()
        self.form_item2 = formItem()
        self.form_item3 = formItem()
        self.form_item4 = formItem()
        self.form_item5 = formItem()
        self.form_item6 = formItem()
        self.form_item7 = formItem()
        self.form_item7A = formItem()
        self.form_item8 = formItem()
        self.form_item9 = formItem()
        self.form_item9A = formItem()
        self.form_item9B = formItem()
        self.form_item9C = formItem()
        self.form_item10 = formItem()
        self.form_item11 = formItem()
        self.form_item12 = formItem()
        self.form_item13 = formItem()
        self.form_item14 = formItem()
        self.form_item15 = formItem()
        self.form_item16 = formItem()

    def preProcessDocumentData(self):
        if (self.data_cleanup_complete):
            print('Data Already Loaded')
            return

        with open(self.f_input_file_path, 'r') as fin:
            raw_10k = fin.read()

        # Search for the first <Document></Document> Tag
        doc_start_pattern = re.compile(r'<DOCUMENT>')
        doc_end_pattern = re.compile(r'</DOCUMENT>')

        doc_start_found = doc_start_pattern.search(raw_10k)
        doc_end_found = doc_end_pattern.search(raw_10k)

        # Document Tag Not found
        if (doc_start_found):
            doc_start_is = doc_start_found.start()
            doc_end_is = doc_end_found.end()
            self.header_text = raw_10k[:doc_start_is]
            if(self.b_process_hader_only): return
        else:
            print('Process All content as Item 0')
            self.header_text = raw_10k[0:]
            if(self.b_process_hader_only): return
            self.saveResultsAsItemZero()

        raw_basic = raw_10k[doc_start_is:doc_end_is]

        item_1a_content = BeautifulSoup(raw_basic, 'html.parser')
        sourcedata = item_1a_content.get_text().encode('ascii')
        untagged_data = sourcedata.decode('ascii', errors='ignore')

        untagged_data = untagged_data.replace('\xa0', '')

        untagged_data = self.getWellformedContent(untagged_data)

        tagged_data = re.sub(r'(?<=[\w\r\:\.\;\) *])\n',
                             '<LINESEP>', untagged_data)

        tagged_data_no_newline = re.sub(r'\n', r"", tagged_data)
        tagged_data_no_newline = re.sub(
            r'<LINESEP>\s*Part\s*I*\s*', '<LINESEP>', tagged_data_no_newline)
        ##
        # tag_iter = re.findall(r'ITEM\s*\d*\w', tagged_data_no_newline)
        tag_iter = re.findall(r'ITEM\s*\d*\w\.*', tagged_data_no_newline)

        for items in tag_iter:
            tagged_data_no_newline = tagged_data_no_newline.replace(
                items, "".join(items.split()))
        ##

        tagged_data_no_newline = re.sub(
            r'<LINESEP>\s*Item\s*', '<LINESEP>ITEM', tagged_data_no_newline)
        tagged_data_no_newline = re.sub(
            r'<LINESEP>\s*', '<LINESEP>', tagged_data_no_newline)

        final_data = re.sub(r'ITEM<LINESEP>\s*', 'ITEM',
                            tagged_data_no_newline)
        back_to_orig_data = re.sub(r'<LINESEP>', '\n', final_data)

        self.clean_data_as_text = final_data
        self.data_cleanup_complete = True

        with open("z_RawText.txt", 'w') as f1:
            f1.write(raw_basic)

        with open("z_UntaggedData.txt", 'w') as f1:
            f1.write(untagged_data)

        with open("z_tagged_data_no_newline.txt", 'w') as f1:
            f1.write(tagged_data_no_newline)

        with open("z_TaggedData.txt", 'w') as f2:
            f2.write(tagged_data)

        # with open("TestFile3.txt", 'w') as f3:
        #     f3.write(final_data1)

        with open("z_FinalOutput.txt", 'w') as f4:
            f4.write(final_data)

        with open("z_back_to_orig.txt", 'w') as f4:
            f4.write(back_to_orig_data)

    def createSectionList(self):
        if (self.data_cleanup_complete == False):
            raise Exception(
                "Call preProcessDocumentData() before invoking createSectionList()..")
        # print(self.clean_data_as_text)

        all_tags = re.finditer('<LINESEP>ITEM\d+\w?',
                               self.clean_data_as_text)

        for tag in all_tags:
            # print(str(tag.group()), tag.start(), tag.end())
            tag_name = str(tag.group()).strip()
            match tag_name:
                case '<LINESEP>ITEM1':
                    # print(tag_name)
                    self.form_item1.add_Element(
                        1, tag_name, tag.start(), tag.end())

                case '<LINESEP>ITEM1A':
                    # print(tag_name)
                    self.form_item1A.add_Element(
                        2, tag_name, tag.start(), tag.end())
                case '<LINESEP>ITEM1B':
                    # print(tag_name)
                    self.form_item1B.add_Element(
                        3, tag_name, tag.start(), tag.end())
                case '<LINESEP>ITEM2':
                    self.form_item2.add_Element(
                        4, tag_name, tag.start(), tag.end())
                    # print(tag_name)
                case '<LINESEP>ITEM3':
                    self.form_item3.add_Element(
                        5, tag_name, tag.start(), tag.end())
                    # print(tag_name)
                case '<LINESEP>ITEM4':
                    self.form_item4.add_Element(
                        6, tag_name, tag.start(), tag.end())
                    # print(tag_name)
                case '<LINESEP>ITEM5':
                    self.form_item5.add_Element(
                        7, tag_name, tag.start(), tag.end())
                    # print(tag_name)
                case '<LINESEP>ITEM6':
                    self.form_item6.add_Element(
                        8, tag_name, tag.start(), tag.end())
                    # print(tag_name)
                case '<LINESEP>ITEM7':
                    self.form_item7.add_Element(
                        9, tag_name, tag.start(), tag.end())
                    # print(tag_name)
                case '<LINESEP>ITEM7A':
                    self.form_item7A.add_Element(
                        10, tag_name, tag.start(), tag.end())
                    # print(tag_name)
                case '<LINESEP>ITEM8':
                    self.form_item8.add_Element(
                        11, tag_name, tag.start(), tag.end())
                    # print(tag_name)
                case '<LINESEP>ITEM9':
                    self.form_item9.add_Element(
                        12, tag_name, tag.start(), tag.end())
                    # print(tag_name)
                case '<LINESEP>ITEM9A':
                    self.form_item9A.add_Element(
                        13, tag_name, tag.start(), tag.end())
                    # print(tag_name)
                case '<LINESEP>ITEM9B':
                    self.form_item9B.add_Element(
                        14, tag_name, tag.start(), tag.end())
                    # print(tag_name)
                case '<LINESEP>ITEM9C':
                    self.form_item9C.add_Element(
                        15, tag_name, tag.start(), tag.end())
                    # print(tag_name)
                case '<LINESEP>ITEM10':
                    self.form_item10.add_Element(
                        16, tag_name, tag.start(), tag.end())
                    # print(tag_name)
                case '<LINESEP>ITEM11':
                    self.form_item11.add_Element(
                        17, tag_name, tag.start(), tag.end())
                    # print(tag_name)
                case '<LINESEP>ITEM12':
                    self.form_item12.add_Element(
                        18, tag_name, tag.start(), tag.end())
                    # print(tag_name)
                case '<LINESEP>ITEM13':
                    self.form_item13.add_Element(
                        19, tag_name, tag.start(), tag.end())
                    # print(tag_name)
                case '<LINESEP>ITEM14':
                    self.form_item14.add_Element(
                        20, tag_name, tag.start(), tag.end())
                    # print(tag_name)
                case '<LINESEP>ITEM15':
                    self.form_item15.add_Element(
                        21, tag_name, tag.start(), tag.end())
                    # print(tag_name)
                case '<LINESEP>ITEM16':
                    self.form_item16.add_Element(
                        22, tag_name, tag.start(), tag.end())

    def populateItemText(self):
        self.updateStartIndex()
        self.updateEndIndex()

        # Populate Text
        self.filtered_item_list.sort(key=lambda item: item.hierarchy)
        final_itemized_data = ''
        for item in self.filtered_item_list:
            if (item.end_index != 0):
                item.item_text = self.clean_data_as_text[item.start_index:item.end_index]
            else:
                item.item_text = self.clean_data_as_text[item.start_index:]
            # final_itemized_data = "\n#####################################################################################################################\n"
            start_tag = '<'+item.selected_item_name.strip() + '>'
            end_tag = '\n</'+item.selected_item_name.strip() + '>\n'
            item_text = (str(item.item_text).replace(
                '<LINESEP><LINESEP>', ' ').replace('<LINESEP>', '\n'))
            tagged_text = ''
            tagged_text = start_tag + item_text + end_tag
            final_itemized_data += tagged_text
        if (len(final_itemized_data.rstrip().lstrip()) > 0):
            self.final_itemized_data = final_itemized_data
        else:
            self.saveResultsAsItemZero()

    def updateStartIndex(self):

     # if (len(self.form_item1.form_Elements) == 2):
        self.form_item1.start_index = self.getStartIndex(self.form_item1)
     # if (len(self.form_item1A.form_Elements) == 2):
        self.form_item1A.start_index = self.getStartIndex(self.form_item1A)

     # if (len(self.form_item1B.form_Elements) == 2):
        self.form_item1B.start_index = self.getStartIndex(self.form_item1B)

     # if (len(self.form_item2.form_Elements) == 2):
        self.form_item2.start_index = self.getStartIndex(self.form_item2)

     # if (len(self.form_item3.form_Elements) == 2):
        self.form_item3.start_index = self.getStartIndex(self.form_item3)

     # if (len(self.form_item4.form_Elements) == 2):
        self.form_item4.start_index = self.getStartIndex(self.form_item4)

     # if (len(self.form_item5.form_Elements) == 2):
        self.form_item5.start_index = self.getStartIndex(self.form_item5)

     # if (len(self.form_item6.form_Elements) == 2):
        self.form_item6.start_index = self.getStartIndex(self.form_item6)

     # if (len(self.form_item7.form_Elements) == 2):
        self.form_item7.start_index = self.getStartIndex(self.form_item7)

     # if (len(self.form_item7A.form_Elements) == 2):
        self.form_item7A.start_index = self.getStartIndex(self.form_item7A)

     # if (len(self.form_item8.form_Elements) == 2):
        self.form_item8.start_index = self.getStartIndex(self.form_item8)

     # if (len(self.form_item9.form_Elements) == 2):
        self.form_item9.start_index = self.getStartIndex(self.form_item9)

     # if (len(self.form_item9A.form_Elements) == 2):
        self.form_item9A.start_index = self.getStartIndex(self.form_item9A)

     # if (len(self.form_item9B.form_Elements) == 2):
        self.form_item9B.start_index = self.getStartIndex(self.form_item9B)

     # if (len(self.form_item9C.form_Elements) == 2):
        self.form_item9C.start_index = self.getStartIndex(self.form_item9C)

     # if (len(self.form_item10.form_Elements) == 2):
        self.form_item10.start_index = self.getStartIndex(self.form_item10)

     # if (len(self.form_item11.form_Elements) == 2):
        self.form_item11.start_index = self.getStartIndex(self.form_item11)

     # if (len(self.form_item12.form_Elements) == 2):
        self.form_item12.start_index = self.getStartIndex(self.form_item12)

     # if (len(self.form_item13.form_Elements) == 2):
        self.form_item13.start_index = self.getStartIndex(self.form_item13)

     # if (len(self.form_item14.form_Elements) == 2):
        self.form_item14.start_index = self.getStartIndex(self.form_item14)

     # if (len(self.form_item15.form_Elements) == 2):
        self.form_item15.start_index = self.getStartIndex(self.form_item15)

     # if (len(self.form_item16.form_Elements) == 2):
        self.form_item16.start_index = self.getStartIndex(self.form_item16)

    def getStartIndex(self, form_item: formItem):

        # Well formed document
        if (len(form_item.form_Elements) == 2):
            if (form_item.form_Elements[1].start > form_item.form_Elements[0].start):
                start_pos = form_item.form_Elements[1].start
                self.filtered_item_list.append(form_item)
            else:
                start_pos = form_item.form_Elements[0].start
                self.filtered_item_list.append(form_item)
            return start_pos

        # Missing Table of Contents
        elif (len(form_item.form_Elements) == 1):
            start_pos = form_item.form_Elements[0].start
            self.filtered_item_list.append(form_item)
            return start_pos

        # Special Processing for Item1
        if (form_item.hierarchy == 1):
            if (form_item.form_Elements[1].start > form_item.form_Elements[0].start):
                start_pos = form_item.form_Elements[1].start
                self.filtered_item_list.append(form_item)
            else:
                start_pos = form_item.form_Elements[0].start
                self.filtered_item_list.append(form_item)
            return start_pos

        # More than one Item Found - Identify the correct Item
        elif (len(form_item.form_Elements) > 0):
            print("Missing Hierarchy - More than two tags found:", form_item.selected_item_name,
                  " Hierarchy#:", form_item.hierarchy)

            previous_hierarchy_start = self.getPreviousHierarchyStart(
                form_item.hierarchy)

            if (previous_hierarchy_start == -1):
                print("Issue Processing Hierarchy:")
                raise ItemsNotProcssedError(
                    "More than two Items found for:"+form_item.selected_item_name)
                return 0

            form_item.form_Elements.sort(key=lambda item: item.start)

            for item in form_item.form_Elements:
                if (item.start > previous_hierarchy_start):
                    print("Missing Hierarchy processed successfully:")
                    start_pos = item.start
                    self.filtered_item_list.append(form_item)
                    return start_pos

    def getPreviousHierarchyStart(self, current_hierarchy):

        if (self.filtered_item_list):
            last_added_item = self.filtered_item_list[len(
                self.filtered_item_list) - 1]
            return last_added_item.start_index
        return -1

    def updateEndIndex(self):
        self.filtered_item_list.sort(key=lambda item: item.hierarchy)
        for index, item in enumerate(self.filtered_item_list):
            # print(item.selected_item_name,"  ", item.start_index," ", item.end_index)
            for item2 in self.filtered_item_list:
                if (item.start_index != item2.start_index and item2.start_index > item.start_index):
                    replacing_item = item
                    replacing_item.end_index = item2.start_index
                    self.filtered_item_list[index] = replacing_item
                    break

    def getReport(self):
        items_found = ''
        for item in self.filtered_item_list:
            items_found += item.selected_item_name+","
        # print('Following Items Found in document and successfully processed:')
        # print(items_found.rstrip(','))
        return items_found.rstrip(',')

    def postProcessCleanup(self):
        self.data_cleanup_complete = False

    def initProcessorParams(self, f_input_file_path=None, f_output_file_path=None, f_success_log=None, 
                            f_failed_log=None, f_item0_logile=None, f_sec_url=None,f_document_name=None, 
                            b_process_hader_only = False, 
                            d_reporting_year = None, d_reporting_quarter = None, b_bulk_mode = False):
        self.f_input_file_path = f_input_file_path
        self.f_output_file_path = f_output_file_path
        self.f_success_log = f_success_log
        self.f_failed_log = f_failed_log
        self.f_sec_url = f_sec_url
        self.f_item0_logile = f_item0_logile
        self.f_document_name = f_document_name
        self.b_process_hader_only = b_process_hader_only
        self.d_reporting_year = d_reporting_year
        self.d_reporting_quarter = d_reporting_quarter

        #Reset Header
        self.conformed_name=""
        self.standard_industry_classification=""
        self.irs_number = 0
        self.state_of_incorporation="" 
        self.fiscal_year_end="" 
        self.form_type=""
        self.street_1=""
        self.city="" 
        self.state="" 
        self.zip=""

        self.b_bulk_mode=b_bulk_mode

    def processSingleTenKFile(self, f_input_file_path=None, f_output_file_path=None, f_success_log=None, f_failed_log=None, f_item0_logile=None, f_sec_url=None,f_document_name=None):

        self.f_input_file_path = f_input_file_path
        self.f_output_file_path = f_output_file_path
        self.f_success_log = f_success_log
        self.f_failed_log = f_failed_log
        self.f_sec_url = f_sec_url
        self.f_item0_logile = f_item0_logile
        self.f_document_name = f_document_name

        try:
            if(self.b_process_hader_only):
                  self.preProcessDocumentData()
                  self.extractDocumentHeader()
                  self.saveResults()
                  return 1
            else:
                self.preProcessDocumentData()
                self.createSectionList()
                self.populateItemText()
                self.extractDocumentHeader()
                self.build_final_xml()
                self.saveResults()
                self.postProcessCleanup()
                return 1

        except (ItemsNotProcssedError) as exc:

            print(f'Item Processing Alert: = {self.f_item0_logile}\n')
            if f_item0_logile:
                f_log = open(f_item0_logile, 'a')
                f_log.write(f'{dt.datetime.now()}\n' +
                            f'Item Processing Alert: {self.f_input_file_path}\n')
                f_log.write(f'Details:\n' + f'{exc.ErrorMessage}\n\n')
                f_log.flush()
            return 2

        except (Exception) as exc:

            print(f'Error Processing File: = {self.f_input_file_path}\n')
            if self.f_failed_log:
                f_log = open(self.f_failed_log, 'a')
                f_log.write(f'{dt.datetime.now()}\n' +
                            f'Error Processing File: {self.f_input_file_path}\n')
                f_log.write(f'Error Details:\n' + f'{exc.args}\n\n')
                f_log.flush()
            return 0

    def saveResultsAsItemZero(self):
        # Save all content Beyond tag Accession Number into Item 0
        with open(self.f_input_file_path, 'r') as fin:
            raw_text = fin.read()
        doc_start_pattern = re.compile(r'ACCESSION NUMBER:')
        doc_start_is = doc_start_pattern.search(raw_text).start()
        item0_text = raw_text[doc_start_is:]
        self.final_itemized_data = item0_text
        item0 = formItem()
        item0.add_Element(item_name='ITEM0')
        self.filtered_item_list.append(item0)
        self.extractDocumentHeader()
        self.build_final_xml()
        self.saveResults()
        raise ItemsNotProcssedError(
            "Item Tags Not found. Data Processed as [Tag0]")

    def saveResults(self):
        pass

        # with open(self.f_output_file_path, 'w') as targetFile:
        #     targetFile.write(self.final_xml)

        # log_info = self.getReport()
        # f_log = open(self.f_success_log, 'a')
        # f_log.write(f'{dt.datetime.now()}\n' +
        #             f'Following Items were Found in the document {self.f_input_file_path} and successfully processed:\n'+f'|{log_info}| \n')
        # print(f'{dt.datetime.now()}\n' +
        #       f'Following Items were Found in the document {self.f_input_file_path} and successfully processed:\n'+f'|{log_info}| \n')

    def processDocumentHeader(self, current_count:0, last_batch:False):
        self.preProcessDocumentData()
        self.extractDocumentHeader()
        self.saveResults()

    def extractDocumentHeader(self):
        conformed_name=""
        standard_industry_classification=""
        irs_number = 0
        state_of_incorporation="" 
        fiscal_year_end="" 
        form_type=""
        street_1=""
        city="" 
        state="" 
        zip=""

        header_start = '<HEADER>\n'
        header_end = '</HEADER>\n'
        sec_url = "<SEC_URL_LOC>"+self.f_sec_url+"</SEC_URL_LOC>\n"

        lines = self.getWellformedContent(self.header_text).split('\n')
        for line in lines:
            if ('COMPANY CONFORMED NAME:' in line):
                conformed_name = line.strip(']').lstrip('\t').strip(
                    'COMPANY CONFORMED NAME:')
                self.conformed_name=re.sub('\\t', '', conformed_name)
                conformed_name = '<COMPANY_CONFORMED_NAME>' + \
                    re.sub('\\t', '', conformed_name) + \
                    '</COMPANY_CONFORMED_NAME>\n'

            if ('STANDARD INDUSTRIAL CLASSIFICATION:' in line):
                standard_industry_classification = line.lstrip(
                    '\t').strip('STANDARD INDUSTRIAL CLASSIFICATION:')
                self.standard_industry_classification=re.sub('\\t', '', standard_industry_classification)
                standard_industry_classification = '<STANDARD_INDUSTRIAL_CLASSIFICATION>' + \
                    re.sub('\\t', '', standard_industry_classification) + \
                    '</STANDARD_INDUSTRIAL_CLASSIFICATION>\n'

            if ('IRS NUMBER:' in line):
                irs_number = line.strip(']').lstrip('\t').strip('IRS NUMBER:')
                self.irs_number=re.sub('\\t', '', irs_number)
                irs_number = '<IRS_NUMBER>' + \
                    re.sub('\\t', '', irs_number)+'</IRS_NUMBER>\n'

            if ('STATE OF INCORPORATION:' in line):
                state_of_incorporation = line.strip(']').lstrip(
                    '\t').strip('STATE OF INCORPORATION:')
                self.state_of_incorporation=re.sub('\\t', '', state_of_incorporation)
                state_of_incorporation = '<STATE_OF_INCORPORATION>' + \
                    re.sub('\\t', '', state_of_incorporation) + \
                    '</STATE_OF_INCORPORATION>\n'

            if ('FISCAL YEAR END:' in line):
                fiscal_year_end = line.strip(']').lstrip('\t').strip('FISCAL YEAR END:')
                self.fiscal_year_end=re.sub('\\t', '', fiscal_year_end)
                fiscal_year_end = '<FISCAL_YEAR_END>' + \
                    re.sub('\\t', '', fiscal_year_end)+'</FISCAL_YEAR_END>\n'

            if ('FORM TYPE:' in line):
                form_type = line.strip(']').lstrip('\t').strip('FORM TYPE:')
                self.form_type = re.sub('\\t', '', form_type)
                form_type = '<FORM_TYPE>' + \
                    re.sub('\\t', '', form_type)+'</FORM_TYPE>\n'

            if ('STREET 1:' in line):
                street_1 = line.strip(']').lstrip('\t').strip('STREET 1:')
                self.street_1 = re.sub('\\t', '', street_1)
                street_1 = '<STREET_1>' + \
                    re.sub('\\t', '', street_1)+'</STREET_1>\n'

            if ('CITY:' in line):
                city = line.strip(']').lstrip('\t').strip('CITY:')
                self.city = re.sub('\\t', '', city)
                city = '<CITY>'+re.sub('\\t', '', city)+'</CITY>\n'
            if ('STATE:' in line):
                state = line.strip(']').lstrip('\t').strip('STATE:')
                self.state=re.sub('\\t', '', state)
                state = '<STATE>'+re.sub('\\t', '', state)+'</STATE>\n'

            if ('ZIP:' in line):
                zip = line.strip(']').lstrip('\t').strip('ZIP:')
                self.zip=re.sub('\\t', '', zip)
                zip = '<ZIP>'+re.sub('\\t', '', zip)+'</ZIP>\n'



        self.document_header = header_start + sec_url 
        if(conformed_name):
            self.document_header += conformed_name
        
        if(standard_industry_classification):
            self.document_header += standard_industry_classification
        
        if(irs_number):
            self.document_header +=  irs_number
        
        if(state_of_incorporation):
            self.document_header += state_of_incorporation 
        
        if(fiscal_year_end):
            self.document_header += fiscal_year_end
    
        if(form_type):
            self.document_header += form_type

        if(form_type):
            self.document_header += street_1

        if(city):
            self.document_header += city

        if(state):
            self.document_header += state

        self.document_header += header_end



    def build_final_xml(self):
        self.final_xml = '<?xml version="1.0" encoding="ascii"?>\n' + \
            '<Document>\n' + \
            self.document_header+'<ITEMS>\n' + self.final_itemized_data + '</ITEMS>\n' + \
            '</Document>'
       # print(self.final_xml)

    def getWellformedContent(self, orig_content):
        pass


class tenKXMLProcessor(tenKProcessor):
    def __init__(self, save_results) -> None:
        super().__init__()
        self.save_results = save_results

    def getWellformedContent(self, orig_content):
        return orig_content.replace("&", "&amp;").replace("\"", "&quot;").replace("'", "&apos;").replace("<", "&lt;").replace(">", "&gt;")

    def saveResults(self):
        if(self.save_results):
            output_xml_file_name = self.f_output_file_path.replace(
                '.txt', '.xml', 1)
            with open(output_xml_file_name, 'w') as targetFile:
                targetFile.write(self.final_xml)
        else: 
                return self.final_xml

        log_info = self.getReport()
        f_log = open(self.f_success_log, 'a')
        f_log.write(f'{dt.datetime.now()}\n' +
                    f'Following Items were Found in the document {self.f_input_file_path} and successfully processed:\n'+f'|{log_info}| \n')
        print(f'{dt.datetime.now()}\n' +
              f'Following Items were Found in the document {self.f_input_file_path} and successfully processed:\n'+f'|{log_info}| \n')

    def getProcessedXMLContent(self):
        return self.final_xml




class tenKTextProcessor(tenKProcessor):


    def getWellformedContent(self, orig_content):
        return orig_content

    def saveResults(self):
        output_xml_file_name = self.f_output_file_path
        with open(output_xml_file_name, 'w') as targetFile:
                targetFile.write(self.final_xml)

        log_info = self.getReport()
        f_log = open(self.f_success_log, 'a')
        f_log.write(f'{dt.datetime.now()}\n' +
                    f'Following Items were Found in the document {self.f_input_file_path} and successfully processed:\n'+f'|{log_info}| \n')
        print(f'{dt.datetime.now()}\n' +
              f'Following Items were Found in the document {self.f_input_file_path} and successfully processed:\n'+f'|{log_info}| \n')



# file_path = '/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/FormDownloads/10K/Year1994Q1/63908-0000063908-94-000013.txt'

# logfile = f'templogfile.txt'
# section_processor = tenKTextProcessor()
# section_processor = tenKXMLProcessor()

# file_list =[
# '37008-0000950152-94-000288.txt',
# '37008-0000950152-94-000288.txt',
# '773915-0000892569-94-000101.txt',
# '773915-0000892569-94-000101.txt',
# '790381-0000898080-94-000022.txt',
# '793421-0000950103-94-001944.txt',
# '793421-0000950103-94-001944.txt',
# '842461-0000950124-94-000623.txt',
# '857402-0000857402-94-000035.txt',
# '859257-0000857402-94-000036.txt',
# '860004-0000857402-94-000037.txt',
# '865227-0000857402-94-000038.txt',
# '868482-0000857402-94-000039.txt',
# '869391-0000857402-94-000045.txt',
# '869844-0000869844-94-000001.txt',
# '873084-0000857402-94-000041.txt',
# '874783-0000857402-94-000042.txt',
# '876858-0000857402-94-000043.txt',
# '879209-0000857402-94-000044.txt',
# '893958-0000893958-94-000006.txt',
# '893958-0000893958-94-000007.txt',
# '909783-0000909783-94-000002.txt',
# '912238-0000912238-94-000002.txt'
# ]

# for file_name in file_list:
    
#     section_processor = tenKDatabaseProcessor()
#     section_processor.b_process_hader_only = True
#     section_processor.d_reporting_year=1994
#     section_processor.d_reporting_quarter=1
#     section_processor.processSingleTenKFile(
#         file_path, "temptarget.txt", logfile, logfile, logfile, f_sec_url="testurl", f_document_name=file_name)
# # # section_processor = tenKProcessor()
# # section_processor.processSingleTenKFile("103682-0001193125-16-480850.txt",logfile)
# # section_processor = tenKProcessor()
# section_processor.processSingleTenKFile("32567-0001264931-14-000431.txt",logfile)
