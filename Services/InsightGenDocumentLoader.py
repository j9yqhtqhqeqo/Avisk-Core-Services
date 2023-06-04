



PARM_LOGFILE = (r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Log/InsightGenLog/')
PARM_SOURCE_INPUT_PATH = (r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/FormDownloads/10K/')
PARM_REPROCESS_PATH = (r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/ReProcessDocHeaders/')
PARM_PROCESSED_PATH = (r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/FormDownloads/10KProcessed/')

PARM_FORM_PREFIX = 'https://www.sec.gov/Archives/'
PARM_BGNYEAR = 2022  # User selected bgn period.  Earliest available is 1993
PARM_ENDYEAR = 2022  # User selected end period.
PARM_BGNQTR = 1  # Beginning quarter of each year
PARM_ENDQTR = 4  # Ending quarter of each year


from DocumentProcessor import tenKXMLProcessor



class InsightGenDocumentLoader:
    def __init__(self) -> None:
        pass

    def get_Document_content(self, document_path:str):
        
        document_path = self._find_fully_qualified_path()
        full_document_path = document_path
        ten_k_XMLProcessor = tenKXMLProcessor()
        # ten_k_XMLProcessor.initProcessorParams(f_input_file_path=document_path,)
        
    
    def _find_fully_qualified_path():
        pass