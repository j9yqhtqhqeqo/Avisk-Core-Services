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
    def __init__(self, Sector,Year) -> None:
        self.Sector = Sector
        self.Year = Year
