import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.io as pio
from io import BytesIO
from typing import List, Optional, Tuple

pio.templates.default = "plotly_dark"

st.set_page_config(
    page_title="Spotify Analytics",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded",
)

def inject_custom_css():
    """
    Injects custom CSS to style the app in a Spotify-like theme.
    """
    spotify_green = "#1DB954"
    spotify_black = "#191414"
    spotify_light_grey = "#B3B3B3"
    
    st.markdown(f"""
    <style>
        /* Base */
        html, body, [class*="st-"] {{
            font-family: 'Inter', 'Helvetica Neue', 'Arial', sans-serif;
            color: {spotify_light_grey};
        }}
        .stApp {{
            background-color: {spotify_black};
        }}

        /* Headings */
        h1, h2, h3 {{
            color: #FFFFFF !important;
        }}
        
        /* Sidebar */
        .st-emotion-cache-16txtl3 {{
            background-color: #090909; /* Slightly lighter black for sidebar */
            border-right: 1px solid #282828;
        }}
        .st-emotion-cache-16txtl3 .st-emotion-cache-1d8prh {{
            color: #FFFFFF; /* Sidebar title color */
        }}

        /* Buttons */
        .stButton>button {{
            background-color: {spotify_green};
            color: #FFFFFF;
            border: none;
            border-radius: 500px;
            padding: 10px 24px;
            font-weight: bold;
            transition: all 0.2s ease-in-out;
        }}
        .stButton>button:hover {{
            background-color: #1ED760;
            transform: scale(1.05);
            color: #FFFFFF;
        }}
        .stButton>button:focus {{
            box-shadow: 0 0 0 2px {spotify_black}, 0 0 0 4px {spotify_green};
            background-color: {spotify_green};
            color: #FFFFFF;
        }}

        /* Metrics */
        .st-emotion-cache-1tpl0xr {{
            background-color: #282828;
            border: 1px solid #282828;
            border-radius: 12px;
            padding: 20px;
        }}
        .st-emotion-cache-1tpl0xr .st-emotion-cache-1r6slb0 {{
            color: {spotify_light_grey}; /* Metric label */
        }}
        .st-emotion-cache-1tpl0xr .st-emotion-cache-10y5sf6 {{
            color: #FFFFFF; /* Metric value */
            font-size: 2.5rem;
        }}

        /* File Uploader */
        .st-emotion-cache-13m3d8v {{
            background-color: #282828;
            border-radius: 8px;
        }}

        /* Charts */
        .js-plotly-plot {{
            border-radius: 12px;
        }}
        
        /* Success/Info Messages */
        .st-emotion-cache-1wivap2 {{
             background-color: rgba(29, 185, 84, 0.1);
             border: 1px solid {spotify_green};
             border-radius: 8px;
        }}
    </style>
    """, unsafe_allow_html=True)


@st.cache_data(ttl=3600)
def load_data(uploaded_files: List[BytesIO]) -> Optional[pd.DataFrame]:
    """
    Loads one or more Spotify history JSON files into a single DataFrame.
    """
    if not uploaded_files:
        return None
    
    all_dfs = []
    for file in uploaded_files:
        try:
            file.seek(0)
            df = pd.read_json(file)
            all_dfs.append(df)
        except ValueError:
            st.error(f"Error reading {file.name}. Is it a valid JSON file?")
            return None
            
    if not all_dfs:
        return None
        
    combined_df = pd.concat(all_dfs, ignore_index=True)
    return combined_df

@st.cache_data(ttl=3600)
def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Preprocesses the raw Spotify data.
    - Converts timestamps
    - Extracts time features
    - Calculates playback time in minutes
    """

    column_map = {
        'ts': 'endTime',
        'ms_played': 'msPlayed',
        'master_metadata_track_name': 'trackName',
        'master_metadata_album_artist_name': 'artistName'
    }
    
    required_cols = list(column_map.keys())
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        st.error(
            "Your JSON files are missing required columns. "
            f"The script needs: {', '.join(required_cols)}. "
            f"Your file is missing: {', '.join(missing_cols)}. "
            "Are you sure this is the 'StreamingHistory' file?"
        )
        return None
        
    df = df.rename(columns=column_map)

    df['endTime'] = pd.to_datetime(df['endTime'])
    
    df['minutesPlayed'] = df['msPlayed'] / 60000
    
    df['hour'] = df['endTime'].dt.hour
    df['day_of_week'] = df['endTime'].dt.day_name()
    df['month'] = df['endTime'].dt.month_name()
    df['year'] = df['endTime'].dt.year
    df['date'] = df['endTime'].dt.date
    
    df = df[df['minutesPlayed'] > 0.5].copy() 
    
    df['artistName'] = df['artistName'].fillna('Unknown Artist')
    df['trackName'] = df['trackName'].fillna('Unknown Track')
    
    return df

@st.cache_data(ttl=3600)
def calculate_sessions(df: pd.DataFrame, gap_threshold_minutes: int = 30) -> pd.DataFrame:
    """
    Identifies listening sessions based on a time gap threshold.
    Returns a DataFrame with session details.
    """
    df_sorted = df.sort_values(by='endTime')
    
    df_sorted['time_diff'] = df_sorted['endTime'].diff().dt.total_seconds() / 60
    
    session_threshold = gap_threshold_minutes
    df_sorted['new_session'] = (df_sorted['time_diff'] > session_threshold).astype(int)
    
    df_sorted['session_id'] = df_sorted['new_session'].cumsum()
    
    session_df = df_sorted.groupby('session_id').agg(
        session_start=('endTime', 'min'),
        session_end=('endTime', 'max'),
        total_minutes=('minutesPlayed', 'sum'),
        total_tracks=('trackName', 'count')
    )
    
    session_df['session_duration_minutes'] = (
        session_df['session_end'] - session_df['session_start']
    ).dt.total_seconds() / 60
    
    session_df = session_df[session_df['total_tracks'] > 1].copy()
    
    return session_df


def plot_top_items(df: pd.DataFrame, column: str, title: str, n: int = 15) -> None:
    """
    Generates an interactive bar chart for top N items (tracks or artists).
    """
    if column not in df.columns:
        st.warning(f"Column '{column}' not found in data.")
        return
        
    top_items = df.groupby(column)['minutesPlayed'].sum().nlargest(n).reset_index()
    
    fig = px.bar(
        top_items,
        x='minutesPlayed',
        y=column,
        orientation='h',
        title=title,
        color='minutesPlayed',
        color_continuous_scale='Greens',
        text='minutesPlayed'
    )
    fig.update_layout(
        yaxis={'categoryorder':'total ascending'},
        xaxis_title="Total Minutes Played",
        yaxis_title=None,
        margin=dict(l=0, r=0, t=40, b=0),
        plot_bgcolor="#191414",
        paper_bgcolor="#191414",
        font_color="#FFFFFF"
    )
    fig.update_traces(
        texttemplate='%{x:.0f} min', 
        textposition='outside'
    )
    st.plotly_chart(fig, use_container_width=True)

def plot_listening_heatmap(df: pd.DataFrame) -> None:
    """
    Generates an interactive heatmap of listening activity by day and hour.
    """
    day_hour_activity = df.groupby(['day_of_week', 'hour'])['minutesPlayed'].sum().unstack().fillna(0)
    
    weekdays_order = [
        "Monday", "Tuesday", "Wednesday", "Thursday", 
        "Friday", "Saturday", "Sunday"
    ]
    day_hour_activity = day_hour_activity.reindex(weekdays_order)
    
    fig = px.imshow(
        day_hour_activity,
        title='Listening Heatmap (Day of Week vs. Hour of Day)',
        labels=dict(x="Hour of Day", y="Day of Week", color="Minutes Played"),
        color_continuous_scale='Greens'
    )
    fig.update_layout(
        xaxis=dict(tickmode='linear', dtick=2),
        plot_bgcolor="#191414",
        paper_bgcolor="#191414",
        font_color="#FFFFFF",
        margin=dict(l=0, r=0, t=40, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)

def plot_listening_over_time(df: pd.DataFrame) -> None:
    """
    Generates an interactive line chart of listening minutes over time.
    """
    daily_activity = df.set_index('endTime').resample('D')['minutesPlayed'].sum().reset_index()
    
    fig = px.line(
        daily_activity,
        x='endTime',
        y='minutesPlayed',
        title='Listening Activity Over Time',
        labels={'endTime': 'Date', 'minutesPlayed': 'Minutes Played'}
    )
    fig.update_traces(line_color='#1DB954', fill='tozeroy', fillcolor='rgba(29, 185, 84, 0.2)')
    fig.update_layout(
        plot_bgcolor="#191414",
        paper_bgcolor="#191414",
        font_color="#FFFFFF",
        margin=dict(l=0, r=0, t=40, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)


def get_summary_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generates summary DataFrames for artists and tracks.
    """
    top_artists_summary = (
        df.groupby('artistName')['minutesPlayed']
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    
    top_tracks_summary = (
        df.groupby(['trackName', 'artistName'])['minutesPlayed']
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    
    return top_artists_summary, top_tracks_summary

def to_excel(dfs: List[pd.DataFrame], sheet_names: List[str]) -> BytesIO:
    """
    Writes multiple DataFrames to an in-memory Excel file.
    """
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for df, sheet_name in zip(dfs, sheet_names):
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    processed_data = output.getvalue()
    return processed_data

def main():
    """
    The main Streamlit application logic.
    """
    inject_custom_css()
    
    with st.sidebar:
        st.markdown(
            "<h1>🎵 Spotify Analytics</h1>", 
            unsafe_allow_html=True
        )
        st.markdown(
            "Upload your **extended streaming history** JSON files "
            "(`StreamingHistoryX.json`) to get started."
        )
        
        uploaded_files = st.file_uploader(
            "Upload your `StreamingHistoryX.json` files",
            type=["json"],
            accept_multiple_files=True
        )
        
        st.markdown("---")
        st.markdown(
            "Built with ❤️ by a data enthusiast. "
        )

    if not uploaded_files:
        st.info("Upload your Spotify data in the sidebar to generate your personal dashboard.")
        st.image(
            "https://placehold.co/1200x400/191414/1DB954?text=Your+Spotify+Dashboard&font=inter",
            use_column_width=True
        )
        return

    raw_df = load_data(uploaded_files)
    if raw_df is None:
        return
        
    df = preprocess_data(raw_df)
    if df is None:
        return
        
    session_df = calculate_sessions(df)

    st.title("Your Personal Spotify Dashboard")
    st.markdown("Here's a deep dive into your listening habits.")
    
    st.header("At a Glance")
    total_minutes = df['minutesPlayed'].sum()
    total_hours = total_minutes / 60
    total_days = total_hours / 24
    unique_tracks = df['trackName'].nunique()
    unique_artists = df['artistName'].nunique()
    avg_session_length = session_df['session_duration_minutes'].mean() if not session_df.empty else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            label="Total Hours Listened", 
            value=f"{total_hours:,.1f}"
        )
    with col2:
        st.metric(
            label="Total Days Listened", 
            value=f"{total_days:,.1f}"
        )
    with col3:
        st.metric(
            label="Unique Tracks", 
            value=f"{unique_tracks:,}"
        )
    with col4:
        st.metric(
            label="Avg. Session (min)", 
            value=f"{avg_session_length:,.1f}"
        )

    st.markdown("---")

    st.header("Your Listening Patterns")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        plot_listening_heatmap(df)
    with col2:
        daily_activity = df.groupby('day_of_week')['minutesPlayed'].sum().reindex([
            "Monday", "Tuesday", "Wednesday", "Thursday", 
            "Friday", "Saturday", "Sunday"
        ]).reset_index()
        fig_daily = px.bar(
            daily_activity,
            x='day_of_week',
            y='minutesPlayed',
            title='Total Listening by Day',
            color='minutesPlayed',
            color_continuous_scale='Greens'
        )
        fig_daily.update_layout(
            plot_bgcolor="#191414", 
            paper_bgcolor="#191414", 
            font_color="#FFFFFF",
            xaxis_title=None,
            yaxis_title="Minutes Played"
        )
        st.plotly_chart(fig_daily, use_container_width=True)

    plot_listening_over_time(df)

    st.markdown("---")

    st.header("Your Top Picks")
    
    col1, col2 = st.columns(2)
    with col1:
        plot_top_items(
            df, 
            'artistName', 
            'Your Top 15 Artists (by Minutes Played)'
        )
    with col2:
        plot_top_items(
            df, 
            'trackName', 
            'Your Top 15 Tracks (by Minutes Played)'
        )

    st.markdown("---")
    
    st.header("A Note on Genres")
    st.info(
        "**Why no genre analysis?** Your 'Extended Streaming History' files from Spotify "
        "do not include genre data for each track. \n\n"
        "To perform a genre analysis, one would need to use the Spotify Web API to look up "
        "the genre for each of your top artists. This is a great next step for the project!"
    )
    
    st.markdown("---")

    st.header("Export Your Summary")
    st.markdown(
        "Download an Excel file containing your top artists and tracks."
    )
    
    top_artists, top_tracks = get_summary_data(df)
    excel_data = to_excel(
        [top_artists, top_tracks], 
        ['Top Artists', 'Top Tracks']
    )
    
    st.download_button(
        label="📥 Download Summary (Excel)",
        data=excel_data,
        file_name="spotify_summary.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if __name__ == "__main__":
    main()

