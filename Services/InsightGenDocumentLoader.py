from DocumentProcessor import tenKXMLProcessor
from Utilities.PathConfiguration import path_config

# Configuration-based paths (environment-aware)
PARM_LOGFILE = path_config.get_document_loader_log_path()
PARM_SOURCE_INPUT_PATH = path_config.get_source_input_path()
PARM_REPROCESS_PATH = path_config.get_reprocess_path()
PARM_PROCESSED_PATH = path_config.get_processed_path()

# Constants that don't change by environment
PARM_FORM_PREFIX = 'https://www.sec.gov/Archives/'
PARM_BGNYEAR = 2022  # User selected bgn period.  Earliest available is 1993
PARM_ENDYEAR = 2022  # User selected end period.
PARM_BGNQTR = 1  # Beginning quarter of each year
PARM_ENDQTR = 4  # Ending quarter of each year


class InsightGenDocumentLoader:
    def __init__(self) -> None:
        pass

    def get_Document_content(self, document_path: str):

        document_path = self._find_fully_qualified_path()
        full_document_path = document_path
        ten_k_XMLProcessor = tenKXMLProcessor()
        # ten_k_XMLProcessor.initProcessorParams(f_input_file_path=document_path,)

    def _find_fully_qualified_path():
        pass
