# Import requests to retrive Web Urls example HTML. TXT 
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd





# Import requests to retrive Web Urls example HTML. TXT 
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd


class SectionProcessor:
   
    def __init__(self) -> None:
        pass

    def getSectionContent(self, FileName: str):
        with open(FileName, 'r') as fin:
            raw_10k = fin.read()

        # # print(raw_10k[0:1300])

        doc_start_pattern = re.compile(r'<DOCUMENT>')
        doc_end_pattern = re.compile(r'</DOCUMENT>')

        
        type_pattern = re.compile(r'<TYPE>[^\n]+')

        doc_start_is = doc_start_pattern.search(raw_10k).start()
        doc_end_is = doc_end_pattern.search(raw_10k).end()
        print(doc_start_is)
        print(doc_end_is)
        
        raw_basic = raw_10k[doc_start_is:doc_end_is]
        # doc_types = [x[len('TYPE'):] for x in type_pattern.findall(raw_10k)]
        # doc_types = [x[6:] for x in type_pattern.findall(raw_10k)]
        # for doc_type, doc_start, doc_end in zip(doc_types, doc_start_is, doc_end_is):
        #     if doc_type == '10-K':
        #         document[doc_type]=raw_10k[doc_start:doc_end]

      
        item_1a_content = BeautifulSoup(raw_basic,'html.parser')
        sourcedata = item_1a_content.get_text().encode('utf-8')
        untagged_data = sourcedata.decode('utf-8', errors='ignore')

        tagged_data = re.sub(r'(?<=[\w\r\:\.\;\) *])\n', r"<LINESEP>", untagged_data)
        tagged_data_no_newline = re.sub(r'\n', r"", tagged_data)
        final_data_1 = re.sub(r'<LINESEP>\s*Item', '<LINESEP>ITEM', tagged_data_no_newline)
        final_data = re.sub(r'ITEM<LINESEP>\s*', 'ITEM ', final_data_1)              
        back_to_orig_data = re.sub(r'<LINESEP>', '\n', final_data)   


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

         
section_processor = SectionProcessor()
# section_processor.getSectionContent("10254-0001564590-16-014606.txt")
# section_processor.getSectionContent("0000020212-06-000018.txt")
# section_processor.getSectionContent("103682-0001193125-16-480850.txt")
# section_processor.getSectionContent("32567-0001264931-14-000431.txt")