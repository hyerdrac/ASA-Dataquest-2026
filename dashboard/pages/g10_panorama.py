from __future__ import annotations
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, dcc, html
from pages.common import make_metric_card

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / 'data' / 'out'
TWINS_PATH = DATA_DIR / 'g10_pano_ikizler.csv'
SERIES_PATH = DATA_DIR / 'g10_pano_seriler.csv'
class DataValidationError(ValueError): pass

CLUSTER_NAMES = {1: 'Pre-transition', 2: 'Early transition', 3: 'Mid-transition', 4: 'Late-transition', 5: 'Post-transition'}
CLUSTER_COLORS = {1: '#2166AC', 2: '#67A9CF', 3: '#D9D9D9', 4: '#EF8A62', 5: '#B2182B'}
CLUSTER_EN = CLUSTER_NAMES
LABEL_EN = {'Benzer':'Similar','Çok benzer':'Very similar','Tarihte benzeri yok':'No historical twin'}

def load_data():
    missing=[str(p) for p in (TWINS_PATH,SERIES_PATH) if not p.exists()]
    if missing: raise DataValidationError('Missing required data file(s): ' + ', '.join(missing))
    twins=pd.read_csv(TWINS_PATH); series=pd.read_csv(SERIES_PATH)
    req_t={'iso3','country','query_year','rank','twin_iso3','twin_country','twin_year','distance','label'}
    req_s={'iso3','country','region','year','is_projection','cluster','cluster_name','tfr','lex','median_age','pop_millions','back_step'}
    if not req_t.issubset(twins.columns): raise DataValidationError(f'{TWINS_PATH.name} missing columns: {sorted(req_t-set(twins.columns))}')
    if not req_s.issubset(series.columns): raise DataValidationError(f'{SERIES_PATH.name} missing columns: {sorted(req_s-set(series.columns))}')
    twins['query_year']=pd.to_numeric(twins.query_year,errors='coerce').astype('Int64')
    twins['rank']=pd.to_numeric(twins['rank'],errors='coerce')
    twins['distance']=pd.to_numeric(twins.distance,errors='coerce')
    for c in ['year','cluster','tfr','lex','median_age','pop_millions']:
        series[c]=pd.to_numeric(series[c],errors='coerce')
    series['is_projection']=series.is_projection.astype(bool)
    return twins,series

TEXT = '#1F2937'
GRID = '#E5E7EB'
BORDER = '#D1D5DB'
PROJECTION = '#9CA3AF'
LINE_COLOR = '#0072B2'
BAND_COLOR = 'rgba(0,114,178,0.16)'

def _base(fig, height=420):
    fig.update_layout(template='plotly_white',height=height,margin=dict(l=24,r=24,t=54,b=24),font=dict(family='Inter, Arial, sans-serif',color=TEXT,size=12),legend_title_text='',
                      paper_bgcolor='#FFFFFF',plot_bgcolor='#FFFFFF',
                      xaxis=dict(gridcolor=GRID,linecolor=BORDER),yaxis=dict(gridcolor=GRID,linecolor=BORDER))
    return fig

def build_layout(data, show_back_link=True):
    twins,series=data
    countries=sorted(twins[['iso3','country']].drop_duplicates().itertuples(index=False,name=None),key=lambda x:x[1])
    default='TUR' if any(x[0]=='TUR' for x in countries) else (countries[0][0] if countries else None)
    years=sorted(twins.query_year.dropna().astype(int).unique().tolist())
    return html.Main(className='g10-dashboard',children=[
      html.A('← Back to Dashboard Hub',href='/',className='hub-back') if show_back_link else None,
      html.Header([html.Div('G10 · DEMOGRAPHIC PANORAMA',className='g10-eyebrow'),html.H1('Demographic Twins & Long-Run Trajectories'),html.P('Find countries with similar demographic profiles and follow fertility, life expectancy, median age and population from 1950 to 2050.')],className='g10-header'),
      html.Div([html.Div([html.Label('Country'),dcc.Dropdown(id='g10-country',options=[{'label':f'{c} ({i})','value':i} for i,c in countries],value=default,clearable=False)],className='g10-filter'),html.Div([html.Label('Twin search year'),dcc.Dropdown(id='g10-year',options=[{'label':str(y),'value':y} for y in years],value=2023 if 2023 in years else (years[0] if years else None),clearable=False)],className='g10-filter')],className='g10-filters'),
      html.Div(id='g10-kpis',className='g10-kpis'),
      html.Section([html.Div([html.H2('Closest demographic twins'),html.P('Ranked matches for the selected country and reference year; lower distance means a closer match.')],className='g10-section-heading'),dcc.Graph(id='g10-twins-chart',config={'displayModeBar':False}),html.Div(id='g10-twin-table',className='g10-twin-table')],className='g10-panel'),
      html.Section([html.Div([html.H2('Demographic trajectory'),html.P('Historical observations and projections through 2050. Shaded bands show 95% intervals when available.')],className='g10-section-heading'),html.Div([dcc.RadioItems(id='g10-metric',options=[{'label':'Total fertility rate','value':'tfr'},{'label':'Life expectancy','value':'lex'},{'label':'Median age','value':'median_age'},{'label':'Population','value':'pop_millions'}],value='tfr',inline=True,className='g10-radio')]),dcc.Graph(id='g10-series-chart',config={'displayModeBar':False}),dcc.Graph(id='g10-cluster-chart',config={'displayModeBar':False})],className='g10-panel'),
      html.Div('Source: supplied demographic series and demographic-twin ranking files. Projection values are shown as supplied.',className='g10-note')])

def register_callbacks(app,data):
    twins,series=data
    @app.callback(Output('g10-kpis','children'),Output('g10-twins-chart','figure'),Output('g10-twin-table','children'),Output('g10-series-chart','figure'),Output('g10-cluster-chart','figure'),Input('g10-country','value'),Input('g10-year','value'),Input('g10-metric','value'))
    def update(iso,query_year,metric):
        if not iso:
            empty=_base(go.Figure()); return [],empty,html.Div('No country selected.'),empty,empty
        crows=twins[(twins.iso3==iso)&(twins.query_year==query_year)].sort_values('rank')
        s=series[series.iso3==iso].sort_values('year').copy()
        country=s.country.iloc[0] if not s.empty else (twins[twins.iso3==iso].country.iloc[0] if (twins.iso3==iso).any() else iso)
        current=s[s.year==query_year]
        pop=f"{current.pop_millions.iloc[0]:,.1f}M" if not current.empty and pd.notna(current.pop_millions.iloc[0]) else '—'
        fertility=f"{current.tfr.iloc[0]:.2f}" if not current.empty and pd.notna(current.tfr.iloc[0]) else '—'
        life=f"{current.lex.iloc[0]:.1f} years" if not current.empty and pd.notna(current.lex.iloc[0]) else '—'
        kpis=[make_metric_card('Population',pop,f'{query_year} value'),make_metric_card('Total fertility rate',fertility,f'{query_year} children per woman'),make_metric_card('Life expectancy',life,f'{query_year} at birth'),make_metric_card('Twin matches',str(len(crows)),'ranked matches available')]
        if crows.empty:
            twinfig=_base(go.Figure()); twinfig.add_annotation(text='No twin rankings available for this selection.',showarrow=False)
            table=html.P('No matches available for this country and year.')
        else:
            crows=crows.head(3).copy(); crows['rank_label']=crows['rank'].map(lambda x:f'#{int(x)}' if pd.notna(x) else '')
            crows['label_en']=crows.label.map(LABEL_EN).fillna(crows.label)
            twinfig=px.bar(crows.sort_values('distance',ascending=True),x='distance',y='twin_country',orientation='h',color='distance',color_continuous_scale='Blues',text='distance',hover_data={'twin_iso3':True,'twin_year':True,'label_en':True,'distance':':.3f'})
            twinfig.update_traces(texttemplate='%{text:.3f}',textposition='outside',cliponaxis=False)
            twinfig.update_layout(yaxis_title='',xaxis_title='Demographic distance (lower is closer)',coloraxis_showscale=False)
            table=html.Div([html.Div([html.Div(f"#{int(r.rank)} · {r.twin_country}",className='g10-twin-name'),html.Div(f"{r.twin_iso3} · profile year {int(r.twin_year)} · {LABEL_EN.get(r.label,r.label)} · distance {r.distance:.3f}",className='g10-twin-meta')],className='g10-twin-row') for r in crows.itertuples()])
        if s.empty:
            linefig=_base(go.Figure()); linefig.add_annotation(text='No trajectory data available.',showarrow=False)
            clfig=_base(go.Figure()); clfig.add_annotation(text='No cluster history available.',showarrow=False)
        else:
            labels={'tfr':('Total fertility rate','Children per woman','tfr_lo95','tfr_hi95'),'lex':('Life expectancy','Years','lex_lo95','lex_hi95'),'median_age':('Median age','Years','median_age_lo95','median_age_hi95'),'pop_millions':('Population','Millions','pop_lo95_millions','pop_hi95_millions')}
            title,unit,low,high=labels.get(metric,labels['tfr'])
            linefig=go.Figure()
            if low in s and high in s and s[low].notna().any() and s[high].notna().any():
                linefig.add_trace(go.Scatter(x=s.year,y=s[high],mode='lines',line=dict(width=0),showlegend=False,hoverinfo='skip',name='Upper 95% interval'))
                linefig.add_trace(go.Scatter(x=s.year,y=s[low],mode='lines',line=dict(width=0),fill='tonexty',fillcolor=BAND_COLOR,showlegend=False,hoverinfo='skip',name='95% interval'))
            linefig.add_trace(go.Scatter(x=s.year,y=s[metric],mode='lines',name=title,line=dict(color=LINE_COLOR,width=2.5),customdata=s[['is_projection']].astype(str).values,hovertemplate='Year %{x}<br>'+title+': %{y:.2f}<br>Projection: %{customdata[0]}<extra></extra>'))
            proj=s[s.is_projection]
            if not proj.empty: linefig.add_vline(x=float(proj.year.min()),line_dash='dash',line_color=PROJECTION,annotation_text='Projection begins')
            linefig.update_layout(title=f'{country} · {title}',xaxis_title='Year',yaxis_title=unit)
            clusters=s.groupby(['year','cluster','cluster_name'],as_index=False).pop_millions.sum()
            clusters['cluster_name']=clusters.apply(lambda r:CLUSTER_NAMES.get(int(r.cluster),r.cluster_name),axis=1)
            color_map = {CLUSTER_NAMES[i]: CLUSTER_COLORS[i] for i in CLUSTER_NAMES}
            clfig=px.area(clusters,x='year',y='pop_millions',color='cluster_name',groupnorm='percent',title='Population distribution across transition stages',labels={'year':'Year','pop_millions':'Share of population (%)','cluster_name':'Transition stage'},category_orders={'cluster_name':[CLUSTER_NAMES[i] for i in range(1,6)]},color_discrete_map=color_map)
            clfig.update_layout(yaxis_ticksuffix='%')
        return kpis,_base(twinfig),table,_base(linefig,440),_base(clfig,380)
