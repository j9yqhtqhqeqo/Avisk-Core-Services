import os
import datetime as dt
import time
import pathlib
PARM_TENK_OUTPUT_PATH = (r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Extracted10K/QTR1')


class IndexDescriptors:
    def __init__(self, line):
        self.err = False
        parts = line.strip('\n').split('_')

        self.new_name = parts[4]+'-'+parts[5]
        if len(parts) == 6:
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


input_path = f'{PARM_TENK_OUTPUT_PATH}'
file_list = sorted(os.listdir(input_path))

for file in file_list:
    print(file)
    parts = file.strip('\n').split('_')
    new_name = parts[4]+'-'+parts[5]
    os.rename(f'{PARM_TENK_OUTPUT_PATH}/{file}',f'{PARM_TENK_OUTPUT_PATH}/{new_name}')
