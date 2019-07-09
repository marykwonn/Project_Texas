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

# connect to DB
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
        FROM [BDA_RWI].[dbo].[surveys_markers_perfs_v] where [WELL_COMMON_NAME] in ('A374','A547','A363','A533', 'A774', 'A403','A536', 'A369', 'A750', 'A401', 'A820', 'A540', 'J155', 'B750', 'J448', 'A360', 'A754', 'J331', 'J343')
        order by [MD] asc ;''', cnxn
)



# function to create differentiate well names based on API suffix
def new_well_name(df):
    # drop rows with null API suffixes
    df = df.dropna(subset=['API_SUFFIX'])
    # add new column [WELL COMMON NAME+APISUFFIX]
    df['NEW_WELL_NAME'] = df['WELL_COMMON_NAME'] + "_" + df['API_SUFFIX'].map(str)

    return df

df = new_well_name(SSMS_QUERY)

df['mrkname'] = df['mrkname'].str.strip()
df['mrkname'] = df['mrkname'].replace('F0', 'FO')
unique_markers = df.dropna(subset=['mrkname'])
unique_markers = unique_markers['mrkname'].unique()

marker_all = ['A', 'AA', 'AB', 'AC', 'AD', 'AE', 'AI', 'AM', 'AO', 'AR', 'AU', 'AX', 'BA', 'F', 'FO',
              'G', 'G4', 'G5', 'G6', 'H', 'H1', 'HX', 'HX1', 'HXA', 'HXB', 'HXC', 'HXO', 'J', 'K', 'M',
              'M1', 'S', 'T', 'W', 'X', 'Y', 'Y4', 'Z']

marker_colors = ['#1f77b4', '#ff7f0e', '#d62728', '#8c564b', '#2ca02c', '#a667bd', '#e377b5', '#7f7f7f', '#6522bd',
                 '#17c5cf']
# color index for markers
marker_colordict = {i: marker_colors[j % len(marker_colors)] for j, i in enumerate(marker_all)}

# data bracket for the all traces
data_traces = []


def make_trace(well_name):
    well_coord = df.loc[df['NEW_WELL_NAME'] == well_name]  # filtered df

    x = well_coord['MAP_EASTING']
    y = well_coord['MAP_NORTHING']
    z = well_coord['TVDSS']
    mrk = well_coord['mrkname']

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


ff = pd.read_csv(r'C:\Users\kwonm\Documents\TEST\fault files\WILM.csv')

ff['Z'] *= -1

"""def add_fault():

    trace = go.Surface (
        x = ff['X'],
        y = ff['Y'],
        z = ff['Z'],
    )

    return trace"""


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

# data_traces.append(add_fault())

'''def generate_well_map(df):
    grouped = df.groupby('WELL_COMMON_NAME')
    well_long = np.concatenate(grouped['LONGITUDE'].unique(), axis=0)
    well_lat = np.concatenate(grouped['LATITUDE'].unique(), axis=0)
    project_name = np.concatenate(grouped['PROJECT_NAME'].unique(), axis=0)
    well_index = grouped['PROJECT_NAME'].unique().index

    data = [go.Scattermapbox(
        lat=well_lat,
        lon=well_long,
        mode="markers",
        marker=dict(size=9,
                    color='red'
                    ),
        text=project_name + '<br>' + well_index
        # can add name,
        # selected points = index
        # custom data)
    )]

    layout = go.Layout(
        autosize=True,
        hovermode='closest',
        mapbox=go.layout.Mapbox(
            accesstoken=mapbox_access_token,
            bearing=0,
            pitch=0,
            zoom=15,
            center=go.layout.mapbox.Center(lat=33.76004, lon=-118.18054)),
        height=700
    )

    return {'data': data, 'layout': layout}'''


body = dbc.Container([
    dbc.Row(dbc.Col(html.H1('KD Tree Plot'))),
    dbc.Row([
        dbc.Col([
            html.Label('Select Marker'),
            dcc.Dropdown(id='multi-dropdown',
                         options=[{'label': i, 'value': i} for i in unique_markers],
                         placeholder='Filter by Marker Name', multi=True)
        ])
    ]),
    dbc.Row([
        dbc.Col([
            html.H3('Subsurface Map'),
            dcc.Graph(id='subsurface viz',
                      figure={'data': data_traces,
                              'layout': go.Layout(
                                  # '#3d3b72'
                                  title="LBU -SAMPLE",
                                  clickmode='event+select',
                                  height=1400,
                                  scene=dict(
                                      xaxis=dict(
                                          title='X (EASTING)',
                                          # backgroundcolor='black',  # "rgb(200, 200, 230)",
                                          # gridcolor="rgb(255, 255, 255)",
                                          # showbackground=True,
                                          #zerolinecolor="rgb(255, 255, 255)"
                                      ),
                                      yaxis=dict(title='Y (NORTHING)',
                                                 # backgroundcolor='black',  # "rgb(230, 200,230)",
                                                 # gridcolor="rgb(255, 255, 255)",
                                                 # showbackground=True,
                                                 #zerolinecolor="rgb(255, 255, 255)"
                                                 ),
                                      zaxis=dict(title='SUBSURFACE Z',
                                                 # backgroundcolor='black',  # "rgb(230, 230,200)",
                                                 # gridcolor="rgb(255, 255, 255)",
                                                 # showbackground=True,
                                                 #zerolinecolor="rgb(255, 255, 255)"
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
    # dbc.Row([
    #    dbc.Col([
    #     dash_table.DataTable(
    #    id= 'table',
    # columns = [{

    #    }]

    #  )
    #  ])
   # ])
], fluid=True)

app.layout = html.Div(body)

# run the server
if __name__ == '__main__':
    app.run_server(debug=False)
# dash will automatically refresh browser when change in code when debug = True
