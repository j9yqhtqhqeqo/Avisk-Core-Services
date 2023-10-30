
class DataValidationException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)
        self.document_id:int
        self.document_name:str
        self.error_type: int
        self.NEW_KEYWORDS_FOUND = 1

    def get_error_description(self):
        if(self.error_type == self.NEW_KEYWORDS_FOUND):
            return ('New Keywords Found - Please run validation for document:' + self.document_name)
    
    def init_exception(self, document_id, document_name,error_type):
        self.document_id = document_id
        self.document_name = document_name
        self.error_type = error_type
