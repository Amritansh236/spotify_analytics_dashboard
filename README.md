
# 🎧 Personal Spotify Analytics Dashboard

A **Streamlit-powered web application** that turns your personal Spotify extended streaming history into a beautiful, interactive analytics dashboard.  

This project loads, processes, and visualizes data from multiple Spotify JSON history files, allowing you to discover your **top artists**, **most-listened-to tracks**, and **unique listening patterns** over time.  

It’s designed as a **portfolio-ready example** of data-driven application development — complete with data preprocessing, sessionization logic, and a custom Spotify-inspired UI.


## 🚀 Key Features
- **Multi-File Upload:** Securely loads and combines multiple `StreamingHistoryX.json` files.  
- **Key Metrics:** "At a Glance" KPIs including total hours listened, unique tracks, and unique artists.  
- **Top Artists & Tracks:** Interactive bar charts of your most-played artists and tracks by total minutes.  
- **Listening Heatmap:** 2D heatmap visualizing your listening habits by day of week and hour of day.  
- **Activity Timeline:** Line chart showing your listening activity over your entire history.  
- **Session Analysis:** Custom logic to identify "listening sessions" (continuous play with breaks < 30 min) and calculate average session length.  
- **Custom UI:** Polished, responsive dark-mode interface inspired by Spotify’s brand, built with custom CSS in Streamlit.  
- **Data Export:** Download a summary of your top artists and tracks as an `.xlsx` file.  

## 🧠 Tech Stack
- **Language:** Python  
- **Framework:** Streamlit  
- **Data Manipulation:** Pandas  
- **Visualization:** Plotly Express  
- **Export:** XlsxWriter  

## 🛠️ How to Run Locally

1. **Clone the repository:**
   ```
   git clone https://github.com/your-username/your-repo-name.git
   cd your-repo-name
   ```

2. **Request your data from Spotify:**

   * Go to your [Spotify Account Privacy Settings](https://www.spotify.com/account/privacy/).
   * Request your **Extended streaming history (audio, video, and interactive)**.
   * Spotify will email you a download link in a few days — you’ll get files like `StreamingHistory0.json`, `StreamingHistory1.json`, etc.

3. **Set up a virtual environment (recommended):**

   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. **Install dependencies:**
   Create a `requirements.txt` file containing:

   ```
   pandas
   streamlit
   plotly
   xlsxwriter
   ```

   Then run:

   ```bash
   pip install -r requirements.txt
   ```

5. **Run the app:**

   ```bash
   streamlit run spotify_dashboard.py
   ```

6. **Open the app:**
   Visit [http://localhost:8501](http://localhost:8501) in your browser and upload your `.json` files.
