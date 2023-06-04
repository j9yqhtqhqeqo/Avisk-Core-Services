class DocumentHeaderDBEntity:
    def __init__(self) -> None:
        self.document_id :int  
        self.document_name
        self.reporting_year :int  
        self.reporting_quarter :int  
        self.conformed_name :str  
        self.sic_code :str  
        self.sic_code_4_digit:int 
        self.irs_number :int 
        self.state_of_incorporation :str  
        self.fiscal_year_end :int 
        self.form_type :str  
        self.street_1 :str  
        self.city :str 
        self.state :str  
        self.zip :str