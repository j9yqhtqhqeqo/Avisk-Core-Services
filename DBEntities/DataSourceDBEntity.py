class DataSourceDBEntity:
    def __init__(self, unique_id=None, company_name=None, year=None,content_type=None, content_type_desc='', source_type=None,source_url=None,processed_ind=None, document_name=None) -> None:
        self.unique_id = unique_id
        self.company_name = company_name
        self.year = year
        self.content_type = content_type
        self.content_type_desc = content_type_desc
        self.source_type = source_type
        self.source_url = source_url
        self.processed_ind = processed_ind
        self.document_name = document_name