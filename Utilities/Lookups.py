class Lookups:
    def __init__(self) -> None:
        self.Exposure_Pathway_Dictionary_Type = 1000
        self.Internalization_Dictionary_Type = 1001
        self.Mitigation_Dictionary_Type = 1002
        self.Mitigation_Exp_Insight_Type = 1003
        self.Mitigation_Int_Insight_Type = 1004
        self.Exp_Int_Insight_Type = 1005
        self.Mitigation_Exp_INT_Insight_Type = 1006
        self.Keyword_Hit_Save = 2000
        self.Exposure_Save = 2001
        self.Internalization_Save = 2002

class Content_Type:
    def __init__(self) -> None:
        self.sustainbility_report = 1
        self.TenK_Report = 2

class Processing_Type:
    def __init__(self) -> None:
        self.KEYWORD_GEN_EXP = 1
        self.KEYWORD_GEN_INT = 2
        self.KEYWORD_GEN_MIT = 3
        self.EXPOSURE_INSIGHTS_GEN = 4
        self.INTERNALIZATION_INSIGHTS_GEN = 5
        self.Mitigation_Exp_Insight_GEN = 6
        self.Mitigation_Int_Insight_GEN = 7
        self.Exp_Int_Insight_GEN = 8
        self.Mitigation_Exp_INT_Insight_GEN = 9

class DB_Connection:
     def __init__(self):
        self.DEV_DB_CONNECTION_STRING = 'DRIVER={ODBC Driver 18 for SQL Server};SERVER=avisk-dev-server.database.windows.net;UID=aviskdbadmin;PWD=Qf8wiegqej8h!;database=avisk-dev'
