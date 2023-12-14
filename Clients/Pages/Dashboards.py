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

    df = pd.read_excel(
        "/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Source Code/Data-Testing/Data Extracts/Exposure Pathway Extract Dec 13.xlsx")

    dataset_original = df[["Company", "Year", "Document", "ESG Category",
                           "Exposure Pathway", "Clusters", "Score"]].round(2)

    data_filter = dataset_original["Company"] == 'Chesapeake Energy'
    dataset_comp = dataset_original.where(data_filter).dropna()
    data_filter = dataset_comp["Year"] == 2022
    dataset_year = dataset_comp.where(data_filter).dropna()
    data_filter = dataset_year["Document"] == 'Sustainability Report'
    dataset = dataset_year.where(data_filter).dropna()

    c = (
        alt.Chart(dataset)
        .mark_circle()
        .encode(x="Clusters", y="Score", size="Score", color='ESG Category', tooltip=["ESG Category", "Exposure Pathway", "Clusters", "Score"]).properties(
            title='Exposure Pathway Clusters vs. Score').configure_title(
            fontSize=20,
            font='Courier',
            anchor='middle')
        .configure_axisX()
        .configure_legend(
            strokeColor='gray',
            fillColor='#EEEEEE',
            padding=5,
            cornerRadius=2,
            labelFontSize=8, titleFontSize=10 )
        .configure_axis(grid=True)
        .interactive()
        .configure_range(
                category={'scheme': 'dark2'})
    )

    # c.configure_title(
    #     fontSize=20,
    #     font='Courier',
    #     anchor='start',
    #     color='red'
    # )
    st.altair_chart(c, use_container_width=True)


st_altair_chart()


# def draw_exposure_pathway_scatter_plot():
#     df = pd.read_excel(
#         "/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Source Code/Data-Testing/Data Extracts/Exposure Pathway Extract Dec 13.xlsx")

#     dataset_original = df[["Company", "Year", "Document", "ESG Category",
#                            "Exposure Pathway", "Clusters", "Score"]]

#     data_filter = dataset_original["Company"] == 'Chesapeake Energy'
#     dataset_comp = dataset_original.where(data_filter).dropna()
#     data_filter = dataset_comp["Year"] == 2022
#     dataset_year = dataset_comp.where(data_filter).dropna()
#     data_filter = dataset_year["Document"] == 'Sustainability Report'
#     dataset = dataset_year.where(data_filter).dropna()

#     # print(dataset)

#     max_clusters = dataset["Clusters"].max()
#     max_scores = dataset["Score"].max()

#     company = (dataset["Company"].drop_duplicates().to_numpy())[0]
#     year = int((dataset["Year"].drop_duplicates().to_numpy())[0])
#     document = (dataset["Document"].drop_duplicates().to_numpy())[0]

#     plot_title = company + '  '+str(year)+'  '+document

#     fig, ax = plt.subplots()
#     fig.suptitle('Exposure Pathway Cluster Scoring', weight='bold')
#     plt.title(plot_title, loc='left', fontsize=8, weight='bold')

#     plt.xlim(0, max_clusters + 5)
#     plt.ylim(0, max_scores + 10)
#     plt.xticks()
#     plt.yticks()

#     plt.xlabel('Clusters', weight='bold')
#     plt.ylabel('Score', weight='bold')
#     plt.tight_layout()

#     # data_filter =  dataset_original["Year"] =='2022'
#     # dataset = dataset_comp.where(data_filter).dropna()

#     # Climate
#     data_filter = dataset["ESG Category"] == 'Climate'
#     data_slice_climate = dataset.where(data_filter).dropna()
#     size = data_slice_climate["Score"] * 100
#     scat_climate = ax.scatter(data_slice_climate["Clusters"], data_slice_climate["Score"],
#                               c='b', s=size, alpha=0.5, label='Climate')

#     scat_climate.my_data = data_slice_climate
#     cursor = mplcursors.cursor(
#         scat_climate, hover=mplcursors.HoverMode.Transient)
#     cursor.connect("add", on_add)

#     # Bio Diversity
#     data_filter = dataset["ESG Category"] == 'Bio Diversity'
#     data_slice_bd = dataset.where(data_filter).dropna()
#     size = data_slice_bd["Score"] * 100
#     scat_bd = ax.scatter(data_slice_bd["Clusters"], data_slice_bd["Score"],
#                          c='g', s=size, alpha=0.5, label='Bio Diversity')

#     scat_bd.my_data = data_slice_bd
#     cursor = mplcursors.cursor(scat_bd, hover=mplcursors.HoverMode.Transient)
#     cursor.connect("add", on_add)

#  # Business Strategy
#     data_filter = dataset["ESG Category"] == 'Business Strategy'
#     data_slice_bs = dataset.where(data_filter).dropna()
#     # print(data_slice_bs)
#     size = data_slice_bs["Score"] * 100
#     scat_bs = ax.scatter(data_slice_bs["Clusters"], data_slice_bs["Score"],
#                          c='r', s=size, alpha=0.5, label='Business Strategy')
#     scat_bs.my_data = data_slice_bs
#     cursor = mplcursors.cursor(scat_bs, hover=mplcursors.HoverMode.Transient)
#     cursor.connect("add", on_add)

#     # Human Capital
#     data_filter = dataset["ESG Category"] == 'Human Capital'
#     data_slice_hc = dataset.where(data_filter).dropna()
#     # print(data_slice_hc)
#     size = data_slice_hc["Score"] * 100
#     scat_hc = ax.scatter(data_slice_hc["Clusters"], data_slice_hc["Score"],
#                          c='y', s=size, alpha=0.5, label='Human Capital')
#     scat_hc.my_data = data_slice_hc
#     cursor = mplcursors.cursor(scat_hc, hover=mplcursors.HoverMode.Transient)
#     cursor.connect("add", on_add)

#     # Socio-economic Inequality
#     data_filter = dataset["ESG Category"] == 'Socio-economic Inequality'
#     data_slice_sei = dataset.where(data_filter).dropna()
#     # print(data_slice_sei)
#     size = data_slice_sei["Score"] * 100
#     scat_si = ax.scatter(data_slice_sei["Clusters"], data_slice_sei["Score"],
#                          c='m', s=size, alpha=0.5, label='Socio-economic Inequality')

#     scat_si.my_data = data_slice_sei
#     cursor = mplcursors.cursor(scat_si, hover=mplcursors.HoverMode.Transient)
#     cursor.connect("add", on_add)

#     # Water
#     data_filter = dataset["ESG Category"] == 'Water'
#     data_slice_water = dataset.where(data_filter).dropna()
#     # print(data_slice_water)
#     size = data_slice_water["Score"] * 100

#     scat_w = ax.scatter(data_slice_water["Clusters"], data_slice_water["Score"],
#                         c='w', s=size, alpha=0.5, label='Water', edgecolors='black')

#     scat_w.my_data = data_slice_water
#     cursor = mplcursors.cursor(scat_w, hover=mplcursors.HoverMode.Transient)
#     cursor.connect("add", on_add)

#     lgnd = ax.legend(loc='upper right', fontsize=8)
#     for handle in lgnd.legend_handles:
#         handle.set_sizes([50.0])

#     st.pyplot(plt.gcf())

#     # plt.plot()
#     # fig_html = mpld3.fig_to_html(fig)

#     # components.html(fig_html, height=600)


# def on_add(sel):
#     local_data_df = sel.artist.my_data
#     annotation = (local_data_df.iloc[sel.index]["Exposure Pathway"] +
#                   "\nClusters:" + str(int(local_data_df.iloc[sel.index]["Clusters"])) +
#                   "\nScore:" + str(int(local_data_df.iloc[sel.index]["Score"])))
#     sel.annotation.set(text=annotation)


# def st_scatter_plot():
#     df = pd.read_excel(
#         "/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Source Code/Data-Testing/Data Extracts/Exposure Pathway Extract Dec 13.xlsx")

#     dataset_original = df[["Company", "Year", "Document", "ESG Category",
#                            "Exposure Pathway", "Clusters", "Score"]]

#     data_filter = dataset_original["Company"] == 'Chesapeake Energy'
#     dataset_comp = dataset_original.where(data_filter).dropna()
#     data_filter = dataset_comp["Year"] == 2022
#     dataset_year = dataset_comp.where(data_filter).dropna()
#     data_filter = dataset_year["Document"] == 'Sustainability Report'
#     dataset = dataset_year.where(data_filter).dropna()

#     # print(dataset)

#     max_clusters = dataset["Clusters"].max()
#     max_scores = dataset["Score"].max()

#     company = (dataset["Company"].drop_duplicates().to_numpy())[0]
#     year = int((dataset["Year"].drop_duplicates().to_numpy())[0])
#     document = (dataset["Document"].drop_duplicates().to_numpy())[0]

#     plot_title = company + '  '+str(year)+'  '+document

#     fig, ax = plt.subplots()
#     fig.suptitle('Exposure Pathway Cluster Scoring', weight='bold')
#     plt.title(plot_title, loc='left', fontsize=8, weight='bold')

#     plt.xlim(0, max_clusters + 5)
#     plt.ylim(0, max_scores + 10)
#     plt.xticks()
#     plt.yticks()

#     plt.xlabel('Clusters', weight='bold')
#     plt.ylabel('Score', weight='bold')
#     plt.tight_layout()

#     # data_filter =  dataset_original["Year"] =='2022'
#     # dataset = dataset_comp.where(data_filter).dropna()

#     # Climate
#     data_filter = dataset["ESG Category"] == 'Climate'
#     data_slice_climate = dataset.where(data_filter).dropna()
#     size = data_slice_climate["Score"] * 100
#     scat_climate = st_scatter_plot(data_slice_climate["Clusters"], data_slice_climate["Score"],
#                               c='b', s=size, alpha=0.5, label='Climate')

#     scat_climate.my_data = data_slice_climate
#     cursor = mplcursors.cursor(
#         scat_climate, hover=mplcursors.HoverMode.Transient)
#     cursor.connect("add", on_add)


# chart_data = pd.DataFrame(np.random.randn(20, 4), columns=[
#                           "col1", "col2", "col3", "col4"])

# st.scatter_chart(
#     chart_data,
#     x='col1',
#     y=['col2', 'col3'],
#     size='col4',
#     color=['#FF0000', '#0000FF'],  # Optional
# )
# # draw_exposure_pathway_scatter_plot()
