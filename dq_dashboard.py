
import pandas as pd                 # Für Datenanalyse und -manipulation (Umgang mit DataFrames)
import streamlit as st              # Für die Erstellung von Webanwendungen im Bereich Data Science
import great_expectations as gx     # Für Datenqualitätsprüfungen und Validierungen von Datensätzen
import plotly.graph_objects as go   # Für interaktive Diagramme und Visualisierungen (Graph Objects)
import kagglehub                    # Download von Datensätzen via KaggleHub
import shutil                       # Datei- und Ordneroperationen
import os                           # Zugriff auf Betriebssystemfunktionen


# Dataset direkt als DataFrame laden
# Download latest version
path = kagglehub.dataset_download("ahmedmohamed2003/cafe-sales-dirty-data-for-cleaning-training")
notebook_dir = os.getcwd()
for root, dirs, files in os.walk(path):
    for file in files:
        src_file = os.path.join(root, file)
        dst_file = os.path.join(notebook_dir, file)
        shutil.copy2(src_file, dst_file)
df = pd.read_csv("dirty_cafe_sales.csv", sep=",")

df["Total Spent"] = pd.to_numeric(df["Total Spent"], errors="coerce") # Werte konvergiert, weil z.B. richtige Werte nur nicht python konform --> DQ
df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")



# ------------------------------ Streamlit-Seitenkonfiguration --------------------------------#
st.set_page_config(page_title="Datenqualitäts-Dashboard", layout="wide") # Breite des Dashboards auf volle Breite setzen
st.markdown("### Datenqualitätsdashboard für einen Datensatz") # Titel des Dashboards am Anfang der Seite

# ----------------------------------- Layout Unterteilung  ------------------------------------#
col1, _, col2 = st.columns([47, 6, 47]) # Erstellung zwei Spalten mit Abstand dazwischen

# Inhalt linke Spalte
with col1:
    st.markdown("""
    #### Rohdaten Beschreibung:
    Der Datensatz enthält **10.000** Zeilen mit synthetischen Daten, die Verkaufstransaktionen in einem Café darstellen.
    Dieser Datensatz ist absichtlich „unsauber“ und enthält fehlende Werte, inkonsistente Daten und Fehler, um ein realistisches Szenario für das Dashboard zu schaffen.
    """)
    st.dataframe(df, height=120) #Höhe minimieren, damit nur Vorschaudaten angezeigt werden


#-------------------- Datenqualitätsprüfungen (NICHT TEIL DER HAUPTAUFGABE) ------------------#
# GE-Setup linke Spalte: Umgebung erstellen, df registrieren, Batch (Daten Momentaufnahme) definieren
    context = gx.get_context()
    data_asset = context.data_sources.add_pandas(name="transactions").add_dataframe_asset(name="transactions_asset")
    batch = data_asset.add_batch_definition_whole_dataframe("transactions_batch").get_batch(
        batch_parameters={"dataframe": df}
    )

# Konkrete Regeln für die Datenqualitätsprüfungen definieren
# z.B. Keine NULL-Werte in "Transaction ID", "Transaction ID" ist eindeutig etc. siehe Regel
# Regeln sind frei ausgedacht, weil nicht Teil der Hauptaufgabe
    suite = gx.ExpectationSuite(name="transaction_suite")
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="Transaction ID"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeUnique(column="Transaction ID"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeBetween(column="Quantity", min_value=1, max_value=10))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeBetween(column="Total Spent", min_value=0, strict_min=True))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeInSet(column="Payment Method", value_set=["Credit Card", "Cash", "Digital Wallet"]))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToMatchRegex(column="Transaction Date", regex=r"^\d{4}-\d{2}-\d{2}$"))
    context.suites.add(suite)

# Der Validator prüft Batch anhand der Regeln
# Das Ergebnis (success/fail, Fehleranzahlen) wird als JSON Struktur gespeichert
# Anahnd der Tests können Kennzahlen festgehalten werden, die für weitere Visualisierungen dienen
    validator = context.get_validator(batch=batch, expectation_suite=suite) 
    results_dict = validator.validate().to_json_dict()
    error_records = sum(res["result"].get("unexpected_count", 0) for res in results_dict["results"])  # Zählt die Gesamtzahl der abweichenden Werte
    success_count = sum(res.get("success", False) for res in results_dict["results"])  # Zählt, wie viele Prüfungen erfolgreich waren
    total_checks = len(results_dict["results"])  # Ermittelt die Gesamtzahl der durchgeführten Prüfungen
    progress = success_count / total_checks if total_checks > 0 else 0  # vor allem für Visualisierung

    # Medaille-Status basierend auf der Anzahl erfolgreicher Prüfungen
    if success_count >= 6:
        status, color, progress = "🥇 Gold", "gold", 1.0
    elif success_count >= 4:
        status, color = "🥈 Silber", "silver"
    elif success_count >= 2:
        status, color = "🥉 Bronze", "#cd7f32"
    else:
        status, color = "❌ Keine Auszeichnung", "red"

    # --- Testergebnisse umbenennen, für Tabelle ---
    expectation_to_name = {
        ("expect_column_values_to_not_be_null", "Transaction ID"): "Transaktion ID nicht null",
        ("expect_column_values_to_be_unique", "Transaction ID"): "Transaktion ID eindeutig",
        ("expect_column_values_to_be_between", "Quantity"): "Quantity 1-10",
        ("expect_column_values_to_be_between", "Total Spent"): "Total Spent > 0",
        ("expect_column_values_to_be_in_set", "Payment Method"): "Zahlungsmethode gültig",
        ("expect_column_values_to_match_regex", "Transaction Date"): "Datum YYYY-MM-DD",
    }






 

    test_results = [
            {
                # Liest den passenden Namen der Erwartung aus dem Mapping
                "Test": expectation_to_name.get(
                    (res["expectation_config"]["type"], res["expectation_config"]["kwargs"].get("column", "")),
                    f"Unbekannte Prüfung ({res['expectation_config']['type']})"
                ),
                # Speichert den Status als Häkchen (erfolgreich) oder Kreuz (fehlgeschlagen)
                "Status": "✅" if res.get("success", False) else "❌",
                # Anzahl der fehlerhaften (unerwarteten) Werte für diesen Test
                "Fehler": res.get("result", {}).get("unexpected_count", 0)
            }
            # Schleife über alle Validierungsergebnisse
            for res in results_dict.get("results", [])
        ]   


# Visualisierung der Testergebnisse und ein bisschen html bzw css für die Darstellung
    sub_col1, sub_col2 = st.columns([75, 25])
    sub_col1.table(pd.DataFrame(test_results))

    with sub_col2:
        st.markdown(f"<h4 style='color:{color};'>{status}</h4>", unsafe_allow_html=True)
        st.markdown(f"""
            <div style="height: 150px; width: 80px; background: #e0e0e0; border-radius: 10px; margin: auto; position: relative;">
                <div style="position: absolute; bottom: 0; width: 100%; height: {progress * 100}%; background: {color}; border-radius: 10px;"></div>
            </div>
            <p style="text-align: center;">{success_count}/6 Tests</p>
        """, unsafe_allow_html=True)


# ----------------------------------- Rechte Spalte ------------------------------------------#
# Darstellung von Kennzahlen und Diagrammen zur Datenqualität.
# Es werden prozentuale Anteile fehlerhafter Datensätze und Zeilen mit fehlenden Werten berechnet
# und anschließend als Kreisdiagramme sowie Balkendiagramme visualisiert.
with col2:
    st.markdown("#### Kennzahlen und Diagramme:")

    # Berechnung der relativen Anteile von fehlerhaften Datensätzen und Zeilen mit fehlenden Werten
    error_percentage = round((error_records / len(df)) * 100, 1)
    empty_rows = df.isnull().any(axis=1).sum()
    empty_rows_percentage = round((empty_rows / len(df)) * 100, 1)

    # Unterteilung der rechten Spalte in zwei Diagrammspalten
    sub_colr1, sub_colr2 = st.columns(2)

    # Visualisiert den prozentualen Anteil fehlerhafter Datensätze als Donut-Diagramm für relative Darstellung mit konkreter Prozentzahl
    with sub_colr1:
        fig = go.Figure(go.Pie(
            values=[error_percentage, 100 - error_percentage],
            labels=['Fehlerhaft', 'Korrekt'],
            hole=0.7,
            marker=dict(colors=['#FFA500', '#4CAF50']),
            textinfo='none'
        ))
        fig.update_layout(
            title=dict(text="Anteil fehlerhafter Datensätze (%)", font=dict(size=14), x=0.5, xanchor='center', yanchor='top'),
            annotations=[dict(text=f"{error_percentage}%", x=0.5, y=0.5, font_size=24, showarrow=False)],
            showlegend=False,
            margin=dict(t=40, b=20, l=0, r=0),
            width=200,
            height=200,
        )
        fig.update_traces(
            hovertemplate='%{label}: %{value}%',  # Zeigt beim Hover den Anteil an
            textinfo='none'
        )
        st.plotly_chart(fig, use_container_width=True)

    # Visualisiert den prozentualen Anteil von Zeilen mit fehlenden Werten (NaNs) als Donut-Diagramm
    with sub_colr2:
        fig_empty = go.Figure(go.Pie(
            values=[empty_rows_percentage, 100 - empty_rows_percentage],
            labels=['Zeilen mit leeren Zellen', 'Gefüllt'],
            hole=0.7,
            marker=dict(colors=['#FFA500', '#4CAF50']),
            textinfo='none'
        ))
        fig_empty.update_layout(
            title=dict(text="Anteil Zeilen mit fehlenden Werten (%)", font=dict(size=14), x=0.5, xanchor='center', yanchor='top'),
            annotations=[dict(text=f"{empty_rows_percentage}%", x=0.5, y=0.5, font_size=24, showarrow=False)],
            showlegend=False,
            margin=dict(t=40, b=20, l=0, r=0),
            width=200,
            height=200,
        )
        fig_empty.update_traces(
            hovertemplate='%{label}: %{value}%',    
            textinfo='none'
        )
        st.plotly_chart(fig_empty, use_container_width=True)

    # --- Fehlende Werte pro Spalte ---
    # Berechnet und visualisiert den Prozentsatz fehlender Werte pro Spalte als Balkendiagramm.
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
