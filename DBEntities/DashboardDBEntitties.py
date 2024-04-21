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
    def __init__(self, Sector='',SectorId=0, Year=0, Company_Name='') -> None:
        self.Sector = Sector
        self.Year = Year
        self.SectorId = SectorId
        self.Company_Name = Company_Name


class Reporting_DB_Entity:
        def __init__(self, unique_key=0,DocumentId=0,Sector='',SectorId=0,Year=0, ExposurePathId=0) -> None:
            self.unique_key = unique_key
            self.DocumentId = DocumentId
            self.sector_id=SectorId
            self.Sector = Sector
            self.Year = Year
            self.ExposurePathId = ExposurePathId

class Top10_Chart_DB_Entity:
    def __init__(self, top10_company_exposure='', degree_of_control_sector_normalized=0, degree_of_control_company_normalized=0, top10_sector_exposure='') -> None:
        self.top10_company_exposure = top10_company_exposure
        self.degree_of_control_sector_normalized = degree_of_control_sector_normalized
        self.degree_of_control_company_normalized = degree_of_control_company_normalized
        self.top10_sector_exposure = top10_sector_exposure


