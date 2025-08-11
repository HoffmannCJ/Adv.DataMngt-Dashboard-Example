import pandas as pd                 # Für Datenanalyse und -manipulation (Umgang mit DataFrames)
import streamlit as st              # Für die Erstellung von Webanwendungen im Bereich Data Science
import great_expectations as gx     # Für Datenqualitätsprüfungen und Validierungen von Datensätzen
import plotly.graph_objects as go   # Für interaktive Diagramme und Visualisierungen (Graph Objects)
import kagglehub                    # Download von Datensätzen via KaggleHub
import shutil                       # Datei- und Ordneroperationen
import os                           # Zugriff auf Betriebssystemfunktionen
import json                         # JSON-Verarbeitung


# ------------------------------ Dataset laden --------------------------------#
path = kagglehub.dataset_download("ahmedmohamed2003/cafe-sales-dirty-data-for-cleaning-training")
notebook_dir = os.getcwd()
for root, dirs, files in os.walk(path):
    for file in files:
        src_file = os.path.join(root, file)
        dst_file = os.path.join(notebook_dir, file)
        shutil.copy2(src_file, dst_file)

df = pd.read_csv("dirty_cafe_sales.csv", sep=",")
df["Total Spent"] = pd.to_numeric(df["Total Spent"], errors="coerce")
df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")

# ------------------------------ Streamlit-Seitenkonfiguration --------------------------------#
st.set_page_config(page_title="Datenqualitäts-Dashboard", layout="wide")
st.markdown("### Datenqualitätsdashboard für einen Datensatz")

# ----------------------------------- Layout Unterteilung  ------------------------------------#
col1, _, col2 = st.columns([47, 6, 47])

# Inhalt linke Spalte
with col1:
    st.markdown("""
    #### Rohdaten Beschreibung:
    Der Datensatz enthält **10.000** Zeilen mit synthetischen Daten, die Verkaufstransaktionen in einem Café darstellen.
    Dieser Datensatz ist absichtlich „unsauber“ und enthält fehlende Werte, inkonsistente Daten und Fehler, um ein realistisches Szenario für das Dashboard zu schaffen.
    """)
    st.dataframe(df, height=120)

    success_count = 4
    if success_count >= 6:
        status, color, progress = "🥇 Gold", "gold", 1.0
    elif success_count >= 4:
        status, color, progress = "🥈 Silber", "silver", success_count / 6
    elif success_count >= 2:
        status, color, progress = "🥉 Bronze", "#cd7f32", success_count / 6
    else:
        status, color, progress = "❌ Keine Auszeichnung", "red", success_count / 6

    # JSON-Datei mit Testergebnissen laden
    try:
        with open("test_results.json", "r", encoding="utf-8") as f:
            loaded_results = json.load(f)
    except FileNotFoundError:
        loaded_results = []
        st.warning("⚠️ Keine test_results.json gefunden.")

    # Visualisierung der Testergebnisse
    sub_col1, sub_col2 = st.columns([75, 25])
    if loaded_results:
        sub_col1.table(pd.DataFrame(loaded_results))
    else:
        sub_col1.write("Keine Testergebnisse vorhanden.")

    with sub_col2:
        st.markdown(f"<h4 style='color:{color};'>{status}</h4>", unsafe_allow_html=True)
        st.markdown(f"""
            <div style="height: 150px; width: 80px; background: #e0e0e0; border-radius: 10px; margin: auto; position: relative;">
                <div style="position: absolute; bottom: 0; width: 100%; height: {progress * 100}%; background: {color}; border-radius: 10px;"></div>
            </div>
            <p style="text-align: center;">{success_count}/6 Tests</p>
        """, unsafe_allow_html=True)

# ----------------------------------- Rechte Spalte ------------------------------------------#
with col2:
    st.markdown("#### Kennzahlen und Diagramme:")

    # Dummy-Werte (müssen ggf. aus Validierung stammen)
    # Fehlerhafte Zeilen aus JSON berechnen
    if loaded_results:
        # Summe aller fehlerhaften Werte
        total_errors = sum(item["Fehler"] for item in loaded_results)
        error_records = total_errors
    else:
        error_records = 0  # <-- Hier anpassen, wenn aus JSON/Analyse berechnet
    error_percentage = round((error_records / len(df)) * 100, 1)
    empty_rows = df.isnull().any(axis=1).sum()
    empty_rows_percentage = round((empty_rows / len(df)) * 100, 1)

    sub_colr1, sub_colr2 = st.columns(2)

    # Donut-Diagramm fehlerhafte Datensätze
    with sub_colr1:
        fig = go.Figure(go.Pie(
            values=[error_percentage, 100 - error_percentage],
            labels=['Fehlerhaft', 'Korrekt'],
            hole=0.7,
            marker=dict(colors=['#FFA500', '#4CAF50']),
            textinfo='none'
        ))
        fig.update_layout(
            title=dict(text="Anteil fehlerhafter Datensätze (%)", font=dict(size=14)),
            annotations=[dict(text=f"{error_percentage}%", x=0.5, y=0.5, font_size=24, showarrow=False)],
            showlegend=False,
            margin=dict(t=40, b=20, l=0, r=0),
            width=200,
            height=200,
        )
        st.plotly_chart(fig, use_container_width=True)

    # Donut-Diagramm fehlende Werte
    with sub_colr2:
        fig_empty = go.Figure(go.Pie(
            values=[empty_rows_percentage, 100 - empty_rows_percentage],
            labels=['Zeilen mit leeren Zellen', 'Gefüllt'],
            hole=0.7,
            marker=dict(colors=['#FFA500', '#4CAF50']),
            textinfo='none'
        ))
        fig_empty.update_layout(
            title=dict(text="Anteil Zeilen mit fehlenden Werten (%)", font=dict(size=14)),
            annotations=[dict(text=f"{empty_rows_percentage}%", x=0.5, y=0.5, font_size=24, showarrow=False)],
            showlegend=False,
            margin=dict(t=40, b=20, l=0, r=0),
            width=200,
            height=200,
        )
        st.plotly_chart(fig_empty, use_container_width=True)

    # Fehlende Werte pro Spalte
    missing_percent = (df.isna().sum() / len(df)) * 100
    missing_percent = missing_percent[missing_percent > 0]

    if not missing_percent.empty:
        fig_missing = go.Figure([
            go.Bar(
                x=missing_percent.index,
                y=missing_percent.values,
                text=[f"{v:.2f}%" for v in missing_percent.values],
                textposition="outside",
                marker=dict(color=missing_percent.values, colorscale="Blues")
            )
        ])
        fig_missing.update_layout(
            title=dict(text="Prozent fehlender Werte pro Spalte", y=0.95),
            xaxis=dict(tickangle=-40),
            yaxis=dict(title="Prozent (%)"),
            template="plotly_white",
            margin=dict(t=50, b=140),
            height=350
        )
        fig_missing.update_yaxes(range=[0, 40])
        st.plotly_chart(fig_missing, use_container_width=True)
