import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import altair as alt
from vega_datasets import data

import streamlit as st 
cars = data.cars()

print(cars.head())
click = alt.selection_multi(encodings=['color'])


hist = alt.Chart(cars).mark_bar().encode(
    x='count()',
    y='Origin',
    color=alt.condition(click, 'Origin', alt.value('lightgray'))
).add_selection(
    click
)


scatter = alt.Chart(cars).mark_point().encode(
    x='Horsepower:Q',
    
    y='Miles_per_Gallon:Q',
    color='Origin:N'
).transform_filter(
    click
)

st.altair_chart(hist & scatter )
