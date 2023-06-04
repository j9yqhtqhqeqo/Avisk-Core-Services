# Import requests to retrive Web Urls example HTML. TXT 
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd

# r = requests.get('https://www.sec.gov/Archives/edgar/data/320193/000032019318000145/0000320193-18-000145.txt')


class SectionProcessor:
   
    def __init__(self) -> None:
        pass

    def getSectionContent(self, FileName: str):
        with open(FileName, 'r') as fin:
            raw_10k = fin.read()

        # print(raw_10k[0:1300])

        doc_start_pattern = re.compile(r'<DOCUMENT>')
        doc_end_pattern = re.compile(r'</DOCUMENT>')
        type_pattern = re.compile(r'<TYPE>[^\n]+')

        doc_start_is = [x.end() for x in doc_start_pattern.finditer(raw_10k)]
        doc_end_is = [x.start() for x in doc_end_pattern.finditer(raw_10k)]
        # doc_types = [x[len('TYPE'):] for x in type_pattern.findall(raw_10k)]
        doc_types = [x[6:] for x in type_pattern.findall(raw_10k)]

        document ={}

        for doc_type, doc_start, doc_end in zip(doc_types, doc_start_is, doc_end_is):
            if doc_type == '10-K':
                document[doc_type]=raw_10k[doc_start:doc_end]

        regex = re.compile(r'(>Item(\s|&#160;|&nbsp;)(1A|1B|7A|7|8)\.{0,1})|(ITEM\s(1A|1B|7A|7|8))')
        # regex = re.compile(r'(Item(\s)(1A)\.{0,1})|(ITEM\s(1A))')

        matches = regex.finditer(document['10-K'])

        data = [(x.group(), x.start(), x.end()) for x in matches]
        # print(data)

        test_df = pd.DataFrame(data, columns =["item", "start", "end"])
        test_df['item'] = test_df.item.str.lower()
        # print(test_df.head())
        # Get rid of unnesesary charcters from the dataframe
        test_df.replace('&#160;',' ',regex=True,inplace=True)
        test_df.replace('&nbsp;',' ',regex=True,inplace=True)
        test_df.replace(' ','',regex=True,inplace=True)
        test_df.replace('\.','',regex=True,inplace=True)
        test_df.replace('>','',regex=True,inplace=True)

        # drop duplicates
        pos_dat = test_df.sort_values("start", ascending=True).drop_duplicates(subset=['item'], keep='last')

        pos_dat.set_index('item',inplace=True)

        # Get Item 1a
        item_1a_raw = document['10-K'][pos_dat['start'].loc['item1a']:pos_dat['start'].loc['item1b']]
        item_1a_content = BeautifulSoup(item_1a_raw,'lxml')

        print(item_1a_content.get_text("\n\n")[1:1000])


section_processor = SectionProcessor()
section_processor.getSectionContent("33769-0001193125-13-267502.txt")