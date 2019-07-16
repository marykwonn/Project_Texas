import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import numpy as np
import pandas as pd
import plotly.graph_objs as go
import pyodbc

# mapbox_access_token = 'pk.eyJ1Ijoia3dvbm0iLCJhIjoiY2p4MHk0NTlhMDF4bjN6bnp6bm8xcmswOSJ9.OANG2d0eU8VCjsShWpccgQ'
# USE MARKDOWN FOR HTML

# connect to DB server
server = 'CKCWBDA2'
database = 'BDA_RWI'
username = 'BDA_READ'
password = 'readonly'
cnxn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server}; SERVER=' + server + '; DATABASE=' + database + '; UID=' + username + '; PWD=' + password)
cursor = cnxn.cursor()

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.LUX])

SSMS_QUERY = pd.read_sql_query(
    '''SELECT
        [PROJECT_NAME],
        [WELL_COMMON_NAME],
        [API_SUFFIX],
        [MD],
        [TVDSS] * -1 as [TVDSS],
        [MAP_NORTHING],
        [MAP_EASTING],
        [mrkname],
        [top_perf],
        [bot_perf],
        [frac_flag],
        [perf_status]
        FROM [BDA_RWI].[dbo].[surveys_markers_perfs_v] where [WELL_COMMON_NAME] in ('D716', 'D500', 'B623', 'D719', 'B605', 'B634', 'D547', 'D725')
        order by [MD] asc ;''', cnxn
)


def clean(query):
    """
    Clean, filter query
    Create differentiated well names based on API suffix

    PARAMETERS:
        INPUT: SQL QUERY
        OUTPUT: DATAFRAME
    """

    query['mrkname'] = query['mrkname'].str.strip()
    query['mrkname'] = query['mrkname'].replace('F0', 'FO')
    # drop rows with null API suffixes
    query = query.dropna(subset=['API_SUFFIX'])
    # add new column [WELL COMMON NAME+APISUFFIX]
    query['NEW_WELL_NAME'] = query['WELL_COMMON_NAME'] + "_" + query['API_SUFFIX'].map(str)

    return query

def make_trace(well_name):
    """
    Plot all given well bore points
    PARAMETERS:
        INPUT: WELL NAME
        OUTPUT: PLOTLY DATA TRACE FOR WELL
    """

    well_coord = df.loc[df['NEW_WELL_NAME'] == well_name]  # filtered df

    x = well_coord['MAP_EASTING']
    y = well_coord['MAP_NORTHING']
    z = well_coord['TVDSS']

    trace = go.Scatter3d(
        x=x, y=y, z=z,
        mode='lines',
        line=dict(width=3,
                  color='#f542f2'),
        name=well_name,
        legendgroup=well_name,
    )

    return trace

def make_marker_trace(well_name):
    """
    Plot color-coded markers of a given well name.
    Relies on marker_colordict. Color dictionary for all markers.
    PARAMETERS:
        INPUT: WELL NAME
        OUTPUT: PLOTLY DATA TRACE FOR WELL MARKERS
    """

    well_coord = df.loc[df['NEW_WELL_NAME'] == well_name]  # filtered df
    well_coord = well_coord[pd.notnull(well_coord['mrkname'])]  # filter out null values for marker name
    grouped = well_coord.groupby('mrkname').first()
    marker_index = grouped.index
    mrk_clr = marker_index.map(marker_colordict)

    x = np.concatenate([grouped['MAP_EASTING']], axis=0)
    y = np.concatenate([grouped['MAP_NORTHING']], axis=0)
    z = np.concatenate([grouped['TVDSS']], axis=0)

    trace = go.Scatter3d(
        x=x, y=y, z=z,
        mode='markers+text',
        marker=dict(color=mrk_clr,
                    size=5),
        name=well_name + "<br>" + "Markers",
        text=marker_index,
        textposition="middle right",
        textfont=dict(
            size=10),
        legendgroup=well_name,
        # hoverinfo = 'text',   <--------- gives only the text
        showlegend=True
    )

    return trace

def make_perf_trace(well_name):
    """
    Plot perfs of a given well name. Provides perf position and status.
    PARAMETERS:
        INPUT: WELL NAME
        OUTPUT: PLOTLY DATA TRACE FOR WELL PERFS
    """

    well_coord = df.loc[df['NEW_WELL_NAME'] == well_name]  # filtered df
    well_coord = well_coord[pd.notnull(well_coord['perf_status'])]
    well_coord.loc[well_coord['mrkname'].isnull(), 'mrkname'] = 'N/A'

    perf_status_color = {'INACTIVE': '#f57b42', 'ACTIVE': 'green'}
    perf_clr = well_coord['perf_status'].map(perf_status_color)

    trace = go.Scatter3d(
        x=well_coord['MAP_EASTING'], y=well_coord['MAP_NORTHING'], z=well_coord['TVDSS'],
        mode='markers',
        marker=dict(color=perf_clr,
                    size=5,
                    symbol='diamond',
                    opacity=.1),
        name=well_name + ' Perfs',
        text='Top Perf: ' + well_coord['top_perf'].astype(str) + "<br>" + "Bottom Perf: " + well_coord[
            'bot_perf'].astype(str) + "<br>" + 'Perf Status: ' + well_coord['perf_status'].astype(str) + "<br>" +
             "Marker: " + well_coord['mrkname'],
        legendgroup='Perfs',
        # hoverinfo = 'text',   <--------- gives only the text
        showlegend=True
    )

    return trace

def make_frac_trace(well_name):
    """
    Plot fracs of a given well name. Indicates T/F for frac location.
    PARAMETERS:
        INPUT: WELL NAME
        OUTPUT: PLOTLY DATA TRACE FOR WELL FRACS
    """
    well_coord = df.loc[df['NEW_WELL_NAME'] == well_name]  # filtered df
    well_coord = well_coord.loc[(well_coord.frac_flag == 'F') | (well_coord.frac_flag == 'X')]

    trace = go.Scatter3d(
        x=well_coord['MAP_EASTING'], y=well_coord['MAP_NORTHING'], z=well_coord['TVDSS'],
        mode='markers',
        marker=dict(color='black',
                    size=5,
                    symbol='diamond',
                    opacity=.08),
        name=well_name + ' Fracs',
        text="Fracs: True" + "<br>" + "Marker: " + well_coord['mrkname'],
        legendgroup='Fracs',
        # hoverinfo = 'text',   <--------- gives only the text
        showlegend=True
    )

    return trace


def add_fault(fault):
    data = pd.read_csv(r'Y:\Jensen\%s' % fault, sep=" ", header=None, skiprows=20)

    x = data[data.columns[0]].values
    y = data[data.columns[1]].values
    z = data[data.columns[2]].values * -1

    trace = go.Mesh3d(
        x=x, y=y, z=z,
        color='#00FFFF',
        opacity=0.50,
        name=fault
    )

    return trace


"""
WILL USE AGAIN ONCE LAT/LONG ONLINE!!!!!!!!!!

# def generate_well_map(df):
#     grouped = df.groupby('WELL_COMMON_NAME')
#     well_long = np.concatenate(grouped['LONGITUDE'].unique(), axis=0)
#     well_lat = np.concatenate(grouped['LATITUDE'].unique(), axis=0)
#     project_name = np.concatenate(grouped['PROJECT_NAME'].unique(), axis=0)
#     well_index = grouped['PROJECT_NAME'].unique().index
#
#     data = [go.Scattermapbox(
#         lat=well_lat,
#         lon=well_long,
#         mode="markers",
#         marker=dict(size=9,
#                     color='red'
#                     ),
#         text=project_name + '<br>' + well_index
#         # can add name,
#         # selected points = index
#         # custom data)
#     )]
#
#     layout = go.Layout(
#         autosize=True,
#         hovermode='closest',
#         mapbox=go.layout.Mapbox(
#             accesstoken=mapbox_access_token,
#             bearing=0,
#             pitch=0,
#             zoom=15,
#             center=go.layout.mapbox.Center(lat=33.76004, lon=-118.18054)),
#         height=700
#     )
#
#     return {'data': data, 'layout': layout}
"""

df = clean(SSMS_QUERY)

unique_markers = df.dropna(subset=['mrkname'])
unique_markers = unique_markers['mrkname'].unique()

marker_all = ['A', 'AA', 'AB', 'AC', 'AD', 'AE', 'AI', 'AM', 'AO', 'AR', 'AU', 'AX', 'BA', 'F', 'FO',
              'G', 'G4', 'G5', 'G6', 'H', 'H1', 'HX', 'HX1', 'HXA', 'HXB', 'HXC', 'HXO', 'J', 'K', 'M',
              'M1', 'S', 'T', 'W', 'X', 'Y', 'Y4', 'Z']

marker_colors = ['#1f77b4', '#ff7f0e', '#d62728', '#8c564b', '#2ca02c', '#a667bd', '#e377b5', '#7f7f7f', '#6522bd',
                 '#17c5cf']
# color index for markers
marker_colordict = {i: marker_colors[j % len(marker_colors)] for j, i in enumerate(marker_all)}

# data tuple for all traces
data_traces = []

for i in df['NEW_WELL_NAME'].unique():
    trace = make_trace(i)
    data_traces.append(trace)

    marker_trace = make_marker_trace(i)
    data_traces.append(marker_trace)

for i in df['NEW_WELL_NAME'].unique():
    trace = make_perf_trace(i)
    data_traces.append(trace)

for i in df['NEW_WELL_NAME'].unique():
    trace = make_frac_trace(i)
    data_traces.append(trace)

data_traces.append(add_fault('LBU FLT'))

"""
START BODY CONTENT FOR DASH APP
"""
body = dbc.Container([
    dbc.Row(dbc.Col(html.H1('KD Tree Plot'))),
    dbc.Row([
        dbc.Col([
            html.Label('Select Pool'),
            dcc.Dropdown(id='region',
                         # options=[{'label': i, 'value': i} for i in unique_markers],
                         options=[
                             {'label': 'LB 1', 'value': 'Region 1'},
                             {'label': 'LB 2', 'value': 'Region 2'},
                             {'label': 'LB 3', 'value': 'Region 3'}
                         ],
                         placeholder='Select Region')
        ]),
        dbc.Col([
            html.Label('Select Sub-Region '),
            dcc.Dropdown(id='')
        ])
    ]),
    dbc.Row([
        dbc.Col([
            html.H3('Subsurface Map'),
            dcc.Graph(id='subsurface viz',
                      figure={'data': data_traces,
                              'layout': go.Layout(
                                  title="LBU -SAMPLE",
                                  height=1400,
                                  scene=dict(
                                      xaxis=dict(
                                          title='X (EASTING)',
                                          backgroundcolor='black',  # "rgb(200, 200, 230)",
                                          gridcolor="rgb(255, 255, 255)",
                                          showbackground=True,
                                          zerolinecolor="rgb(255, 255, 255)"
                                      ),
                                      yaxis=dict(title='Y (NORTHING)',
                                                 backgroundcolor='black',  # "rgb(230, 200,230)",
                                                 gridcolor="rgb(255, 255, 255)",
                                                 showbackground=True,
                                                 zerolinecolor="rgb(255, 255, 255)"
                                                 ),
                                      zaxis=dict(title='SUBSURFACE Z',
                                                 backgroundcolor='black',  # "rgb(230, 230,200)",
                                                 gridcolor="rgb(255, 255, 255)",
                                                 showbackground=True,
                                                 zerolinecolor="rgb(255, 255, 255)"
                                                 )
                                  )
                              )
                              },
                      )
        ])]),
    dbc.Row([
        dbc.Col([
            html.H3('Well Map'),
            #dcc.Graph(figure=generate_well_map(df))
        ])

    ])

], fluid=True)

app.layout = html.Div(body)

# run the server
if __name__ == '__main__':
    app.run_server(debug=False)
# dash will automatically refresh browser when change in code when debug = True
