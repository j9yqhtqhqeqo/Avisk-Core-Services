import sys
from pathlib import Path
import os
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))

from Services.InsightGenerator import file_folder_keyWordSearchManager
from Services.InsightGenerator import PARM_STAGE1_FOLDER
from Services.InsightGenerator import Insight_Generator
from Services.InsightGenerator import triangulation_Insight_Generator
from Utilities.Lookups import Lookups


key_word_search_mgr = file_folder_keyWordSearchManager(
    folder_path=PARM_STAGE1_FOLDER)
key_word_search_mgr.validation_mode = True

key_word_search_mgr.generate_keyword_location_map_for_exposure_pathway()

key_word_search_mgr.generate_keyword_location_map_for_internalization()

key_word_search_mgr.generate_keyword_location_map_for_mitigation()

# exp_int_insght_generator = Insight_Generator()
# print("Generating Insights for Exposure Pathway Dictionary Terms")

# exp_int_insght_generator.generate_insights_with_2_factors(
#     Lookups().Exposure_Pathway_Dictionary_Type)

# print("Generating Insights for Internalization Dictionary Terms")
# exp_int_insght_generator.generate_insights_with_2_factors(
#     Lookups().Internalization_Dictionary_Type)

# mitigation_insight_gen = triangulation_Insight_Generator()
# mitigation_insight_gen.generate_mitigation_exp_insights()
# mitigation_insight_gen.generate_mitigation_int_insights()
# mitigation_insight_gen.generate_exp_int_insights()
# mitigation_insight_gen.generate_mitigation_exp_int_insights()