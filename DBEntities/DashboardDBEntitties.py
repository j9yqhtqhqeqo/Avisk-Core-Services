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
    def __init__(self, Company, Year,  Document_Type, ESG_Category,   Exposure_Pathway, Internalization, Clusters, Score) -> None:
        self.Company = Company
        self.Year   = Year
        self.Document_Type = Document_Type
        self.ESG_Category=ESG_Category
        self.Exposure_Pathway=Exposure_Pathway
        self.Clusters =Clusters
        self.Score=Score
        self.Internalization = Internalization
