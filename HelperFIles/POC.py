import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import altair as alt
from vega_datasets import data

temp_text = 'abc,def,ijk,'

new_text = temp_text.rstrip(',')

print(temp_text)
print(new_text)