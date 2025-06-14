import sys
from pathlib import Path
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))

from Utilities.TriangleChartHelper import radar_factory
from DBEntities.DashboardDBEntitties import ExposurePathwayDBEntity, InternalizationDBEntity, MitigationDBEntity, Top10_Chart_DB_Entity, Triangle_Chart_DB_Entity, YOY_DB_Entity, Exposure_Control_Chart_DB_Entity
from DBEntities.DashboardDBManager import DashboardDBManager, Triangle_Chart_DB_Entity
from DBEntities.DashboardDBEntitties import ExposurePathwayDBEntity
import numpy as np
import pandas as pd



class AviskAPIM:

    def __init__(self) -> None:
        self.sl_sector = None
        self.sl_company = None
        self.sl_year_start = None
        self.sl_exposure_selected = None

        self.exposure_list = []
        self.dataset = pd.DataFrame()
        self.dataset_all = pd.DataFrame()
        self.dataset_year = pd.DataFrame()
        self.dataset_ranked = pd.DataFrame()
        self.triangle_dataset = pd.DataFrame()
        self.exp_control_dataset = pd.DataFrame()

        self.load_sector_company_year_list()
      

    def load_sector_company_year_list(self):
        self.dataset_sector_sl, self.dataset_sector_comp_sl, self.dataset_year_sl, self.dataset_doctype_sl = DashboardDBManager(
                "Development").get_sector_company_year_doctype_list()

    def load_data_for_top10_chart(self, from_file=False):

        if (from_file == True):

            self.exposure_list = self.get_exposure_list_from_file()
            df = pd.DataFrame([vars(exposure)
                               for exposure in self.exposure_list])
            self.dataset = df.round(2)

        else:
            self.exposure_list = DashboardDBManager("Development").get_top10_exposure_control_measures(
                self.sl_year_start, self.sl_company)
            df = pd.DataFrame([vars(exposure)
                              for exposure in self.exposure_list])
            self.dataset = df.round(2)
        
        return self.dataset

    def load_data_for_triangles_chart(self):

        self.exposure_list = DashboardDBManager("Development").get_triangle_measures(
            self.sl_year_start, self.sl_company)

        df = pd.DataFrame([vars(exposure) for exposure in self.exposure_list])

        self.triangle_dataset = df.round(2)
        # if (not self.triangle_dataset is None):
        #     print(self.triangle_dataset)

        return self.triangle_dataset

    def load_data_for_yoy_chart(self):

        self.exposure_list = DashboardDBManager(
            "Development").get_yoy_measures(self.sl_company)

        df = pd.DataFrame([vars(exposure) for exposure in self.exposure_list])

        self.yoy_dataset = df.round(2)
        self.dataset_ranked = None
        if (not self.yoy_dataset is None and self.yoy_dataset.size > 0):
            # print(self.yoy_dataset)

            self.chart_header = 'Sector:'+self.sl_sector + ', Company:' + self.sl_company

            self.yoy_dataset["Rank"] = self.yoy_dataset.groupby('year')["exposure_score"].rank(
                ascending=False, method='first')

            data_filter = self.yoy_dataset["Rank"] <= 5

            self.dataset_ranked = self.yoy_dataset.where(data_filter).dropna().sort_values(by=[
                'sector_exposure_path_name', 'exposure_score'])

            # if (not self.dataset_ranked is None):
            #     print(self.dataset_ranked)
        return self.dataset_ranked
    
    def load_data_for_exposure_control_chart(self):

        self.exposure_list = DashboardDBManager(
            "Development").get_exposure_vs_control_measures(self.sl_year_start, self.sl_company)

        df = pd.DataFrame([vars(exposure) for exposure in self.exposure_list])

        self.exp_control_dataset = df.round(2)
        return self.exp_control_dataset


# startup = AviskAPIM()
