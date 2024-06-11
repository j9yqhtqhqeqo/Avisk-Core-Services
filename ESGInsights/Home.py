import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
from pylab import *
import mplcursors
import streamlit as st
import mpld3
import streamlit.components.v1 as components
import altair as alt


def st_altair_chart():

    df = pd.read_excel("Exposure Pathway Extract Dec 13.xlsx")

    dataset_original = df[["Company", "Year", "Document Type", "ESG Category",
                           "Exposure Pathway", "Clusters", "Score"]].round(2)

    data_filter = dataset_original["Company"] == 'Chesapeake Energy'
    dataset_comp = dataset_original.where(data_filter).dropna()
    data_filter = dataset_comp["Year"] == 2022
    dataset_year = dataset_comp.where(data_filter).dropna()
    data_filter = dataset_year["Document Type"] == 'Sustainability Report'
    dataset = dataset_year.where(data_filter).dropna()

    c = (
        alt.Chart(dataset_original)
        .mark_circle()
        .encode(alt.X("Clusters").scale(domain=(0, 100)), y="Score", size="Score", color='ESG Category', tooltip=["ESG Category", "Exposure Pathway", "Clusters", "Score"])
        .properties( height = 600,
            title='ESG Insights.ai').configure_title(
            fontSize=20,
            font='Courier',
            anchor='middle')
        .configure_axis(grid=True)
        .interactive()
        .configure_range(
                category={'scheme': 'dark2'})
    )

    st.altair_chart(c, use_container_width=True)


st_altair_chart()
