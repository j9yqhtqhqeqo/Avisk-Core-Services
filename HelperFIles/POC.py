import multiprocessing

process_count = multiprocessing.cpu_count()

queue_size = 230


buffer =[0]*process_count

for i in range(queue_size):
    j = i % process_count
    buffer[j] = buffer[j] + 1

for item in buffer:
    print(item)

#import urllib      
# from urllib import request    
            
            
# req = request.Request('https://d1io3yog0oux5.cloudfront.net/_7b982f54e1d755807c5fc728a7db0cfe/anteroresources/db/847/7428/esg_report/Antero-Resources-ESG-2023-08-28%21.pdf')
# req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:106.0) Gecko/20100101 Firefox/106.0')
# req.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8')
# req.add_header('Accept-Language', 'en-US,en;q=0.5')

# file_location = r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/TestPdfDownload.pdf'

# with urllib.request.urlopen(req) as response:
#         with open(file_location, 'wb') as f:
#                     f.write(response.read())

# sample =  'Significant�Operational�Changes�In�May�of�2018,�Scott�Saxberg�stepped�down�as�President�and�Chief�Executive�Officer�of�Crescent�Point,�'
# current_data_encoded = sample.encode('ascii',errors='replace')
# current_data = current_data_encoded.decode('ascii', errors='replace')
# new_data =  current_data.replace('?',' ')
# new_other_data = sample.replace('?',' ')
# print('End:')

#         sql = f"INSERT INTO dbo.t_key_word_hits( \
#                 batch_id, dictionary_type,document_id,  document_name, company_id, reporting_year,\
#                 dictionary_id ,key_word, locations,frequency, insights_generated,exposure_path_id, internalization_id,\
#                 impact_category_id, esg_category_id,\
#                 added_dt,added_by ,modify_dt,modify_by\
#                 )\
#                     VALUES\
#                     ({batch_id},{dictionary_type},{document_id},N'{document_name}', {company_id}, {reporting_year},\
#                 {dictionary_id} ,N'{key_word}', N'{locations}', {frequency},0, {exposure_path_id}, {internalization_id},\
#                 {impact_category_id},{esg_category_id},\
#                 CURRENT_TIMESTAMP, N'Mohan Hanumantha',CURRENT_TIMESTAMP, N'Mohan Hanumantha')"

# exit_loop = False
# while(not exit_loop):
#         userInput = input('Enter i to Include, e to Exclude:')
#         if(userInput == 'i'):
#             print("Entered i -- exit")
#             exit_loop = True

#         if(userInput == 'e'):
#             print("Entered e -- exit")
#             exit_loop = True




# import numpy as np

# # str ='1085,6981'

# str =  list('1085,6981, 7602, 7847, 7976, 7985, 8244, 8281, 8771, 8826, 8930, 9034, 9145, 9175, 9239, 9266, 9773, 9799, 9848, 10186, 10985, 11181, 11768, 25565, 28792, 33745, 1710, 5532, 29906, 13945, 30216, 1668, 7621, 7852, 30591,19097, 19103, 30265, 16272, 26992, 27035, 628, 646, 1156, 2022, 5436, 8008, 8024, 8164, 8566, 8698, 8712, 9285, 9302, 9349, 9366, 9420, 11996, 12767, 12778, 13291, 13330, 13377, 13391, 13491, 13760, 15018, 15535, 16220, 16385, 16427, 16485, 16592, 16607, 16654, 18229, 18244, 18645, 19644, 20168, 20358, 23802, 23888, 23909, 23923, 23930, 23982, 24228, 27243, 27765, 27772, 27782, 27793, 28435, 28445, 28543, 28943, 28951, 28967, 29042, 29056, 29253, 29294, 29328, 29384, 29413, 29437, 29497, 29574, 29580, 29585, 29590, 29595, 29639, 32245, 32271, 32510, 32701, 32749, 32810, 32853, 32887, 32921, 33563, 33716, 33765, 33799, 33847')
# integer_exp_insight_keyword_locations = np.asarray(
#             str, dtype=np.int32)


# word ='  forests, '
# print(word.replace('.','').replace(',','').strip())



# # Import requests to retrive Web Urls example HTML. TXT 
# import requests
# from bs4 import BeautifulSoup
# import re
# import pandas as pd
# import pathlib
# from zipfile import ZipFile, ZIP_DEFLATED


# line = ']		IRS NUMBER:				232539694'
# # doc_start_pattern = re.compile(r'IRS NUMBER:')
# # doc_start_found = doc_start_pattern.search(line,re.IGNORECASE)
# # irs_number = line[doc_start_found.start():]
# irs_number = line.strip(']').lstrip('\t').strip('IRS NUMBER:')
# irs_number=re.sub('\\t', '', irs_number)
# print(irs_number)

# sic_code = '['
# sic_code_int = re.search('\d+', sic_code)
# if(not sic_code_int):
#         print('Not found')
# else:
#         print(sic_code_int.group())

# batch_id = 1
# document_id = 1

# new_doc_id =  int(str(batch_id)+str(document_id))

# print(new_doc_id)










     
# directory = pathlib.Path('/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/FormDownloads/10K/TobeZipped')
# with ZipFile('/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/FormDownloads/10K/TobeZipped.zip', "w", ZIP_DEFLATED, compresslevel=9) as archive:
#         for file_path in directory.rglob("*"):
#             archive.write(file_path, arcname=file_path.relative_to(directory))

# process10K()


# item_text = '1989 to 1990 -- General Manager, Austria & Switzerland.'
# item_text = (item_text).replace("&", "&amp;").replace("\"", "&quot;").replace("'", "&apos;").replace("<", "&lt;").replace(">", "&gt;")

# print (item_text)

# FileName='Tempstring.txt'
# with open(FileName, 'r') as fin:
#         raw_basic = fin.read()

    
#         item_1a_content = BeautifulSoup(raw_basic, 'html.parser')
#         sourcedata = item_1a_content.get_text().encode('ascii')
#         untagged_data = sourcedata.decode('ascii', errors='ignore')

#         untagged_data = untagged_data.replace('\xa0', '')

#         tagged_data = re.sub(r'(?<=[\w\r\:\.\;\) *])\n',
#                              '<LINESEP>', untagged_data)

#         tagged_data_no_newline1 = re.sub(r'\n', r"", tagged_data)
#         tagged_data_no_newline2 = re.sub(
#             r'<LINESEP>\s*Part\s*I*\s*', '<LINESEP>', tagged_data_no_newline1)
#         tagged_data_no_newline3 = re.sub(
#             r'<LINESEP>\s*Item\s*', '<LINESEP>ITEM', tagged_data_no_newline2)
#         tagged_data_no_newline4 = re.sub(
#             r'<LINESEP>\s*', '<LINESEP>', tagged_data_no_newline3)
        
#         tag_iter = re.findall(r'ITEM\s*\d*\w\.*', tagged_data_no_newline4)

#         for items in tag_iter:
#             #  print(items.group(), "  ", items.start(), items.end())   
            
#             tagged_data_no_newline4 = tagged_data_no_newline4.replace(items, "".join(items.split()))

#         print(tagged_data_no_newline4)
        # tagged_data_no_newline5 = re.sub(
        #     r'ITEM\s*\d*\w',cleanup(), tagged_data_no_newline4)
        


        # final_data = re.sub(r'ITEM<LINESEP>\s*', 'ITEM',
        #                     tagged_data_no_newline5)
        # back_to_orig_data = re.sub(r'<LINESEP>', '\n', final_data)



# test = ''
# all_tags = re.finditer('<LINESEP>Item\d*\w*[\.*]', test)
# for tag in all_tags:
#     print(tag.group(), tag.start(), tag.end())

# sourcedata = ('Table of Contents<LINESEP> <LINESEP>Part III  Item10. Directors').encode('utf-8')

# untagged_data = sourcedata.decode(
#   'utf-8', errors='ignore'
# )

# remove_parts = re.compile(r'<LINESEP>\s*Part\s*I*')
# untagged_data = remove_parts.sub('<LINESEP>',untagged_data, re.IGNORECASE)

# tagged_data = re.sub(r'(?<=[\w\r\:\.\;\) *])\n', r"<LINESEP>", untagged_data)
# tagged_data_no_newline = re.sub(r'\n', r"", tagged_data)
# final_data_1 = re.sub(r'<LINESEP>\s*Item', '<LINESEP>ITEM', tagged_data_no_newline)
# final_data = re.sub(r'ITEM<LINESEP>\s*', 'ITEM ', final_data_1)

# final_data = final_data.replace('\xc2', '')


# back_to_orig_data = re.sub(r'<LINESEP>', '\n', final_data)   

# print(sourcedata)
# print(final_data)
# # print(back_to_orig_data)



        # test_df = pd.DataFrame(data, columns =["item", "start", "end"])
        # test_df['item'] = test_df.item.str.lower()
        # # print(test_df.head())
        # # Get rid of unnesesary charcters from the dataframe
        # test_df.replace('&#160;',' ',regex=True,inplace=True)
        # test_df.replace('&nbsp;',' ',regex=True,inplace=True)
        # test_df.replace(' ','',regex=True,inplace=True)
        # test_df.replace('\.','',regex=True,inplace=True)
        # test_df.replace('>','',regex=True,inplace=True)

       