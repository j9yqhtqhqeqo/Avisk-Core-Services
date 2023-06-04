############################################################################################################
# Master Insight Generator File
# 
#
############################################################################################################
from LogDetails import LogGenerator as lg
import datetime as dt
from InsightGeneratorDBManager import InsightGeneratorDBManager

PARM_LOGFILE = (r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Log/InsightGenerator')
PARM_FORM_PREFIX = 'https://www.sec.gov/Archives/'


class insightGenerator:
    def __init__(self) -> None:
        self.log_file_path = f'{PARM_LOGFILE} {dt.datetime.now().strftime("%c")}.txt'
          
        self.sic_code: int
        self.company_list:any
        self.exp_dictionary_terms: any
        self.int_dictionary_terms: any
        self.insightList = []

        self.errors: any
        
    
    def _get_company_list(self):
        pass


    def generate_insights(self,company_list:any):
        self.company_list = self._get_company_list()
    
        for company in self.company_list:
            self._load_content()
            self._get_parsed_content()
            self._create_proximity_map()
            self._save_insights()
    
    def _get_dictionary_terms(self):
        pass

    def _create_proximity_map(self):
        pass

    def _get_parsed_content(self):
        pass

    def _load_content(self):
        pass

    def _save_insights(self):
        pass

    def remove_insights(self):
        pass


class insights:
    def __init__(self) -> None:
        self.document_section:str
        self.document_id:str
        self.cluster_terms = dict()
        self.frequency:int

    def add_proximity_info(self,term:str, distance:int):
        self.cluster_terms.update({term:distance})


class tenK_Insight_Generator(insightGenerator):
    def __init__(self) -> None:
        super().__init__()




# insights = insights()

# insights.add_proximity_info("water", 5)
# insights.add_proximity_info("drauhgt", 8)
# insights.add_proximity_info("fire", 6)
# insights.add_proximity_info("rain", 9)

# print(insights.cluster_terms)

