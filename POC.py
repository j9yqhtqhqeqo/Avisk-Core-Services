# Import requests to retrive Web Urls example HTML. TXT 
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd


item_text = '1989 to 1990 -- General Manager, Austria & Switzerland.'
item_text = (item_text).replace("&", "&amp;").replace("\"", "&quot;").replace("'", "&apos;").replace("<", "&lt;").replace(">", "&gt;")

print (item_text)

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

       