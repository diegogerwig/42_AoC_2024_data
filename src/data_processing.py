import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Define campus color mapping
CAMPUS_COLORS = {
    'UDZ': '#00FF00',  # Green
    'BCN': '#FFD700',  # Yellow
    'MAL': '#00FFFF',  # Cyan
    'MAD': '#FF00FF'   # Magenta
}

def load_data():
    """Load and cache data from scraper silently"""
    @st.cache_data(ttl=300)  # Cache for 5 minutes
    def _load():
        import sys
        import io
        from src.scraper import AOCScraper
        
        # Temporarily redirect stdout to capture scraper output
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        
        try:
            scraper = AOCScraper()
            df = scraper.scrape_data()
            
            # Reset stdout
            sys.stdout = old_stdout
            
            return df.sort_values('points', ascending=False).reset_index(drop=True)
        except Exception as e:
            # Reset stdout even if there's an error
            sys.stdout = old_stdout
            raise e
    
    return _load()

def get_current_aoc_day(df):
    """Get current day based on available day columns"""
    return len([col for col in df.columns if col.startswith('day_')])

def create_metrics_dataframe(df, is_global=True):
    """Create a formatted dataframe for metrics"""
    current_day = get_current_aoc_day(df)
    max_possible_stars = current_day * 2

    if is_global:
        success_rate = (df['total_stars'].sum() / (len(df) * max_possible_stars)) * 100
        
        data = {
            'Section': ['🌍 Global'],
            'Students': [len(df)],
            'Points (Avg / Max)': [f"{df['points'].mean():.1f} / {df['points'].max():.1f}"],
            'Streak (Avg / Max)': [f"{df['streak'].mean():.1f} / {df['streak'].max()}"],
            'Stars (Gold / Silver)': [f"{int(df['gold_stars'].sum())} / {int(df['silver_stars'].sum())}"],
            'Success Rate': [f"{success_rate:.1f}%"]
        }
    else:
        data = []
        for campus in sorted(df['campus'].unique()):
            campus_data = df[df['campus'] == campus]
            campus_success = (campus_data['total_stars'].sum() / 
                               (len(campus_data) * max_possible_stars)) * 100
            
            # Create colored campus name
            colored_campus = f"<span style='color: {CAMPUS_COLORS[campus]}'>🏛️ {campus}</span>"
            
            data.append({
                'Section': colored_campus,
                'Students': len(campus_data),
                'Points (Avg/Max)': f"{campus_data['points'].mean():.1f} / {campus_data['points'].max():.1f}",
                'Streak (Avg/Max)': f"{campus_data['streak'].mean():.1f} / {campus_data['streak'].max()}",
                'Stars (Gold/Silver)': f"{int(campus_data['gold_stars'].sum())} / {int(campus_data['silver_stars'].sum())}",
                'Success Rate': f"{campus_success:.1f}%"
            })
    return pd.DataFrame(data)

def plot_stars_distribution(df):
    """Plot distribution of gold and silver stars"""
    melted_df = pd.melt(
        df,
        value_vars=['gold_stars', 'silver_stars'],
        var_name='star_type',
        value_name='count'
    )
    # Convert star_type to categorical
    melted_df['star_type'] = pd.Categorical(melted_df['star_type'])
    
    fig = px.box(
        melted_df,
        x='star_type',
        y='count',
        color='star_type',
        points='all',
        color_discrete_map={
            'gold_stars': '#FFD700',
            'silver_stars': '#C0C0C0'
        },
        title='Stars Distribution',
        category_orders={"star_type": ["gold_stars", "silver_stars"]}
    )
    
    fig.update_layout(height=500, title_x=0.5)
    return fig

# def plot_success_heatmap(df):
#     """Create challenge success heatmap"""
#     day_columns = [col for col in df.columns if col.startswith('day_')]
#     success_matrix = df[day_columns].values
    
#     fig = go.Figure(data=go.Heatmap(
#         z=success_matrix.T,
#         colorscale=[
#             [0, 'white'],
#             [0.5, '#C0C0C0'],
#             [1, '#FFD700']
#         ],
#         zmin=0,
#         zmax=2
#     ))
    
#     fig.update_layout(
#         title='Challenge Success Status',
#         title_x=0.5,
#         xaxis_title='Participant Index',
#         yaxis_title='Day',
#         height=500
#     )
#     return fig


def plot_star_totals_by_campus(df):
    """
    Create a line chart that shows the total number of stars per day for each campus.

    Parameters:
    df (pandas.DataFrame): DataFrame containing the data, with columns for each day and columns for the stars per campus.

    Returns:
    plotly.graph_objects.Figure: Plotly Figure object representing the chart.
    """
    day_columns = [col for col in df.columns if col.startswith('day_')]
    campuses = [col for col in df.columns if col not in day_columns]

    fig = go.Figure()

    for campus in campuses:
        fig.add_trace(go.Scatter(
            x=day_columns,
            y=df[campus],
            mode='lines+markers',
            name=campus
        ))

    fig.update_layout(
        title='Total Stars by Campus per Day',
        xaxis_title='Day',
        yaxis_title='Number of Stars',
        height=500
    )

    return fig


def plot_success_rate(df):
    """Plot success rate over time by campus"""
    current_day = get_current_aoc_day(df)
    day_columns = [f'day_{i}' for i in range(1, current_day + 1)]
    success_data = []
    
    # Usar un enfoque más directo sin groupby
    for campus in df['campus'].unique():
        # Filtrar datos para cada campus
        campus_mask = df['campus'] == campus
        for day in day_columns:
            day_num = int(day.split('_')[1])
            # Calcular la tasa de finalización
            success = (df[campus_mask][day] > 0).sum() / campus_mask.sum() * 100
            success_data.append({
                'Day': day_num,
                'Rate': success,
                'Campus': campus  # No necesitamos una tupla aquí
            })
    
    # Crear DataFrame con los resultados
    success_df = pd.DataFrame(success_data)
    
    # Crear el gráfico
    fig = px.line(
        success_df,
        x='Day',
        y='Rate',
        color='Campus',
        title='Daily Success Rate by Campus',
        labels={'Rate': 'Success Rate (%)'},
        color_discrete_map=CAMPUS_COLORS
    )
    
    fig.update_layout(height=500, title_x=0.5)
    return fig

def plot_points_vs_days(df):
    """Create scatter plot of points vs completed days"""
    df = df.copy()
    df['campus'] = pd.Categorical(df['campus'])
    
    fig = px.scatter(
        df,
        x="completed_days",
        y="points",
        color="campus",
        size="total_stars",
        hover_data=["login"],
        title="Points vs Days Completed",
        color_discrete_map=CAMPUS_COLORS
    )
    
    fig.update_layout(height=500, title_x=0.5)
    return fig

def plot_campus_progress(df):
    """Create radar chart of campus performance"""
    # Crear una copia y convertir campus a categoría
    df = df.copy()
    df['campus'] = pd.Categorical(df['campus'])
    
    # Calcular estadísticas sin usar groupby
    campus_stats = pd.DataFrame()
    
    for campus in df['campus'].unique():
        campus_data = df[df['campus'] == campus]
        stats = {
            'points': campus_data['points'].mean(),
            'streak': campus_data['streak'].mean(),
            'completed_days': campus_data['completed_days'].mean(),
            'gold_stars': campus_data['gold_stars'].mean(),
            'silver_stars': campus_data['silver_stars'].mean()
        }
        campus_stats[campus] = pd.Series(stats)
    
    campus_stats = campus_stats.round(2)
    
    fig = go.Figure()
    
    for campus in campus_stats.columns:
        fig.add_trace(go.Scatterpolar(
            r=campus_stats[campus],
            theta=campus_stats.index,
            name=campus,
            line_color=CAMPUS_COLORS.get(campus, '#808080')
        ))
    
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, showticklabels=True)),
        showlegend=True,
        title='Campus Performance Overview',
        height=500,
        title_x=0.5
    )
    return fig

def plot_points_distribution(df):
    """Create box plot of points distribution by campus"""
    df = df.copy()
    df['campus'] = pd.Categorical(df['campus'])
    
    fig = px.box(
        df,
        x="campus",
        y="points",
        color="campus",
        points="all",
        title="Points Distribution by Campus",
        color_discrete_map=CAMPUS_COLORS
    )
    
    fig.add_hline(
        y=df['points'].median(),
        line_dash="dash",
        line_color="gray",
        annotation_text=f"Global Median: {df['points'].median():.1f}"
    )
    
    fig.update_layout(height=500, title_x=0.5, showlegend=False)
    return fig