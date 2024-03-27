class ExposurePathwayDBEntity:

    def __init__(self,  Company, Year,  Document_Type, ESG_Category,   Exposure_Pathway, Clusters, Score, Sector='') -> None:
        self.Sector = Sector
        self.Company = Company
        self.Year   = Year
        self.Document_Type = Document_Type
        self.ESG_Category=ESG_Category
        self.Exposure_Pathway=Exposure_Pathway
        self.Clusters =Clusters
        self.Score=Score


class InternalizationDBEntity:
    def __init__(self, Company='', Year=0,  Document_Type='', ESG_Category='',   Exposure_Pathway='', Internalization='', Clusters=0, Score=0, Sector='') -> None:
        self.Sector = Sector
        self.Company = Company
        self.Year   = Year
        self.Document_Type = Document_Type
        self.ESG_Category=ESG_Category
        self.Exposure_Pathway=Exposure_Pathway
        self.Clusters =Clusters
        self.Score=Score
        self.Internalization = Internalization


class MitigationDBEntity:
    def __init__(self, Company='', Year=0,  Document_Type='', ESG_Category='',   Exposure_Pathway='', Internalization='', Mitigation_Class="", Mitigation_Sub_Class="", Clusters=0, Score=0, Sector='') -> None:
        self.Sector = Sector
        self.Company = Company
        self.Year = Year
        self.Document_Type = Document_Type
        self.ESG_Category = ESG_Category
        self.Exposure_Pathway = Exposure_Pathway
        self.Mitigation_Class = Mitigation_Class
        self.Mitigation_Sub_Class = Mitigation_Sub_Class
        self.Clusters = Clusters
        self.Score = Score
        self.Internalization = Internalization

class SectorYearDBEntity:
    def __init__(self, Sector='',SectorId=0, Year=0) -> None:
        self.Sector = Sector
        self.Year = Year
        self.SectorId = SectorId



class Reporting_DB_Entity:
        def __init__(self, unique_key=0,DocumentId=0,Sector='',SectorId=0,Year=0, ExposurePathId=0) -> None:
            self.unique_key = unique_key
            self.DocumentId = DocumentId
            self.sector_id=SectorId
            self.Sector = Sector
            self.Year = Year
            self.ExposurePathId = ExposurePathId
