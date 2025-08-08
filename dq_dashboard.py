import pandas as pd
import streamlit as st
import great_expectations as gx
import plotly.graph_objects as go

from great_expectations.core.expectation_suite import ExpectationSuite

# ------------------- CSV-Datei direkt laden ---------------------- #
# Stelle sicher, dass die Datei im gleichen Ordner liegt oder Pfad anpassen
df = pd.read_csv("dirty_cafe_sales.csv", sep=",")

df["Total Spent"] = pd.to_numeric(df["Total Spent"], errors="coerce")
df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")


# ------------------------------ Streamlit-Seitenkonfiguration --------------------------------#
st.set_page_config(page_title="Datenqualitäts-Dashboard", layout="wide")
st.markdown("### Datenqualitätsdashboard für einen Datensatz")

# ----------------------------------- Layout Unterteilung  ------------------------------------#
col1, _, col2 = st.columns([47, 6, 47])

with col1:
    st.markdown("""
    #### Rohdaten Beschreibung:
    Der Datensatz enthält **10.000** Zeilen mit synthetischen Daten, die Verkaufstransaktionen in einem Café darstellen.
    Dieser Datensatz ist absichtlich „unsauber“ und enthält fehlende Werte, inkonsistente Daten und Fehler, um ein realistisches Szenario für das Dashboard zu schaffen.
    """)
    st.dataframe(df, height=120)


    # Datenqualitätsprüfungen
    context = gx.get_context()
    data_asset = context.data_sources.add_pandas(name="transactions").add_dataframe_asset(name="transactions_asset")
    batch = data_asset.add_batch_definition_whole_dataframe("transactions_batch").get_batch(
        batch_parameters={"dataframe": df}
    )

    suite_name = "transaction_suite"
    try:
        suite = context.get_expectation_suite(suite_name)
    except Exception:
        suite = ExpectationSuite(suite_name)

    if len(suite.expectations) == 0:
        suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="Transaction ID"))
        suite.add_expectation(gx.expectations.ExpectColumnValuesToBeUnique(column="Transaction ID"))
        suite.add_expectation(gx.expectations.ExpectColumnValuesToBeBetween(column="Quantity", min_value=1, max_value=10))
        suite.add_expectation(gx.expectations.ExpectColumnValuesToBeBetween(column="Total Spent", min_value=0, strict_min=True))
        suite.add_expectation(gx.expectations.ExpectColumnValuesToBeInSet(column="Payment Method", value_set=["Credit Card", "Cash", "Digital Wallet"]))
        suite.add_expectation(gx.expectations.ExpectColumnValuesToMatchRegex(column="Transaction Date", regex=r"^\d{4}-\d{2}-\d{2}$"))

    validator = context.get_validator(batch=batch, expectation_suite=suite)
    results_dict = validator.validate().to_json_dict()
    error_records = sum(res["result"].get("unexpected_count", 0) for res in results_dict["results"])
    success_count = sum(res.get("success", False) for res in results_dict["results"])
    total_checks = len(results_dict["results"])
    progress = success_count / total_checks if total_checks > 0 else 0

    if success_count >= 6:
        status, color, progress = "🥇 Gold", "gold", 1.0
    elif success_count >= 4:
        status, color = "🥈 Silber", "silver"
    elif success_count >= 2:
        status, color = "🥉 Bronze", "#cd7f32"
    else:
        status, color = "❌ Keine Auszeichnung", "red"

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
            "Test": expectation_to_name.get(
                (res["expectation_config"]["type"], res["expectation_config"]["kwargs"].get("column", "")),
                f"Unbekannte Prüfung ({res['expectation_config']['type']})"
            ),
            "Status": "✅" if res.get("success", False) else "❌",
            "Fehler": res.get("result", {}).get("unexpected_count", 0)
        }
        for res in results_dict.get("results", [])
    ]

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

with col2:
    st.markdown("#### Kennzahlen und Diagramme:")

    error_percentage = round((error_records / len(df)) * 100, 1)
    empty_rows = df.isnull().any(axis=1).sum()
    empty_rows_percentage = round((empty_rows / len(df)) * 100, 1)

    sub_colr1, sub_colr2 = st.columns(2)

    with sub_colr1:
        fig = go.Figure(go.Pie(
            values=[error_percentage, 100 - error_percentage],
            labels=['Fehlerhaft', 'Korrekt'],
            hole=0.7,
            marker=dict(colors=['#FFA500', '#4CAF50']),
            textinfo='none'
        ))
        fig.update_layout(
            title=dict(text="Anteil fehlerhafter Datensätze (%)", font=dict(size=14), x=0.5),
            annotations=[dict(text=f"{error_percentage}%", x=0.5, y=0.5, font_size=24, showarrow=False)],
            showlegend=False,
            margin=dict(t=40, b=20, l=0, r=0),
            width=200,
            height=200,
        )
        fig.update_traces(
            hovertemplate='%{label}: %{value}%',
            textinfo='none'
        )
        st.plotly_chart(fig, use_container_width=True)

    with sub_colr2:
        fig_empty = go.Figure(go.Pie(
            values=[empty_rows_percentage, 100 - empty_rows_percentage],
            labels=['Zeilen mit leeren Zellen', 'Gefüllt'],
            hole=0.7,
            marker=dict(colors=['#FFA500', '#4CAF50']),
            textinfo='none'
        ))
        fig_empty.update_layout(
            title=dict(text="Anteil Zeilen mit fehlenden Werten (%)", font=dict(size=14), x=0.5),
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
