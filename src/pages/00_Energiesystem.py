import json
import os
from datetime import date, datetime, time, timedelta

import altair as alt
import darkdetect
import pandas as pd
import streamlit as st
from streamlit import session_state as ss


# %% MARK: Read Input Data
@st.cache_data
def read_input_data():
    """Read in input data all at once."""
    inputpath = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '..', 'input'
        ))
    ss.all_heat_load = pd.read_csv(
        os.path.join(inputpath, 'heat_load.csv'),
        sep=';', index_col=0, parse_dates=True
        )
    ss.eco_data = pd.read_csv(
        os.path.join(inputpath, 'eco_data.csv'),
        sep=';', index_col=0, parse_dates=True
        )
    ss.all_el_prices = ss.eco_data['El Price'].to_frame()

# %% MARK: Parameters
is_dark = darkdetect.isDark()
shortnames = {
    'Wärmepumpe': 'hp',
    'Gas- und Dampfkratwerk': 'ccet',
    'Blockheizkraftwerk': 'ice',
    'Solarthermie': 'sol',
    'Spitzenlastkessel': 'plb',
    'Wärmespeicher': 'tes'
}
longnames = {
    'hp': 'Wärmepumpe',
    'ccet': 'Gas- und Dampfkratwerk',
    'ice': 'Blockheizkraftwerk',
    'sol': 'Solarthermie',
    'plb': 'Spitzenlastkessel',
    'tes': 'Wärmespeicher'
}

read_input_data()

unitpath = os.path.join(__file__, '..', '..', 'input', 'param_units.json')
with open(unitpath, 'r', encoding='utf-8') as file:
    ss.param_units = json.load(file)
unitinputpath = os.path.join(__file__, '..', '..', 'input', 'unit_inputs.json')
with open(unitinputpath, 'r', encoding='utf-8') as file:
    ss.unit_inputs = json.load(file)

# %% MARK: Sidebar
with st.sidebar:
    if is_dark:
        logo = os.path.join(
            __file__, '..', '..', 'img', 'Logo_ZNES_mitUnisV2_dark.svg'
            )
    else:
        logo = os.path.join(
            __file__, '..', '..', 'img', 'Logo_ZNES_mitUnisV2.svg'
            )
    st.image(logo, use_column_width=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ['System', 'Anlagen', 'Wärme', 'Elektrizität', 'Gas']
    )

# %% MARK: Energy System
with tab1:
    st.header('Auswahl des Wärmeversorgungssystem')

    units = st.multiselect(
        'Wähle die Wärmeversorgungsanlagen aus, die im System verwendet werden '
        + 'können.',
        list(shortnames.keys()),
        placeholder='Wärmeversorgungsanlagen'
        )

    col_topo, _ = st.columns([1, 2])

    topopath = os.path.join(__file__, '..', '..', 'img', 'es_topology_')
    if units:
        col_topo.image(f'{topopath}header.png', use_column_width=True)
        for unit in units:
            col_topo.image(
                f'{topopath+shortnames[unit]}.png', use_column_width=True
                )

# %% MARK: Unit Parameters
with tab2:
    st.header('Parametrisierung der Wärmeversorgungsanlagen')

    for unit in units:
        params = ss.param_units[shortnames[unit]]
        with st.expander(unit):
            col_tech, col_econ = st.columns(2, gap='large')

            col_tech.subheader('Technische Parameter')
            for uinput, uinfo in ss.unit_inputs['Technische Parameter'].items():
                if uinput in ss.param_units[shortnames[unit]]:
                    if uinput == 'balanced':
                        ss.param_units[shortnames[unit]][uinput] = col_tech.toggle(
                            uinfo['name'],
                            value=ss.param_units[shortnames[unit]][uinput]
                        )
                    else:
                        if uinfo['unit'] == '%':
                            ss.param_units[shortnames[unit]][uinput] *= 100
                        if uinfo['unit'] == '':
                            label = uinfo['name']
                        else:
                            label = f"{uinfo['name']} in {uinfo['unit']}"
                        ss.param_units[shortnames[unit]][uinput] = (
                            col_tech.number_input(
                                label,
                                value=float(
                                    ss.param_units[shortnames[unit]][uinput]
                                    ),
                                min_value=uinfo['min'],
                                max_value=uinfo['max'],
                                step=(uinfo['max']-uinfo['min'])/100,
                                key=f'input_{shortnames[unit]}_{uinput}'
                                )
                            )
                        if uinfo['unit'] == '%':
                            ss.param_units[shortnames[unit]][uinput] /= 100

            col_econ.subheader('Ökonomische Parameter')
            for uinput, uinfo in ss.unit_inputs['Ökonomische Parameter'].items():
                if uinput in ss.param_units[shortnames[unit]]:
                    ss.param_units[shortnames[unit]][uinput] = (
                        col_econ.number_input(
                            f"{uinfo['name']} in {uinfo['unit']}",
                            value=float(
                                ss.param_units[shortnames[unit]][uinput]
                                ),
                            min_value=uinfo['min'],
                            max_value=uinfo['max'],
                            step=(uinfo['max']-uinfo['min'])/100,
                            key=f'input_{shortnames[unit]}_{uinput}'
                            )
                        )

# %% MARK: Heat Load
with tab3:
    st.header('Wärmeversorgungsdaten')

    st.subheader('Wärmelastdaten')
    col_sel, col_vis = st.columns([1, 2])

    dataset_name = col_sel.selectbox(
        'Wähle die Wärmelastdaten aus, die im System zu verwenden sind',
        [*ss.all_heat_load.columns, 'Eigene Daten'],
        placeholder='Wärmelastendaten'
    )

    if dataset_name == 'Eigene Daten':
        heat_load_year = None
        tooltip = (
            'Die erste Spalte muss ein Datumsindex in stündlicher Auflösung und'
            + ' die zweite die Wärmelast in MWh beinhalten. Zusätzlich muss bei'
            + 'der csv-Datein das Trennzeichen ein Semikolon sein.'
            )
        user_file = col_sel.file_uploader(
            'Datensatz einlesen', type=['csv', 'xlsx'], help=tooltip
            )
        if user_file is None:
            col_sel.info(
                'Bitte fügen Sie eine Datei ein.'
                )
        else:
            if user_file.lower().endswith('csv'):
                heat_load = pd.read_csv(
                    user_file, sep=';', index_col=0, parse_dates=True
                    )
            elif user_file.lower().endswith('xlsx'):
                heat_load = pd.read_excel(user_file, index_col=0)

    else:
        user_file = None
        heat_load_years = ss.all_heat_load.loc[
            ~ss.all_heat_load[dataset_name].isna(), dataset_name
            ].index.year.unique()
        heat_load_year = col_sel.selectbox(
            'Wähle das Jahr der Wärmelastdaten aus',
            heat_load_years, index=len(heat_load_years)-1,
            placeholder='Betrachtungsjahr'
        )
        yearmask = ss.all_heat_load.index.year == heat_load_year
        heat_load = ss.all_heat_load.loc[yearmask, dataset_name]
        heat_load = heat_load[heat_load.notna()].to_frame()

    dates = None
    if dataset_name != 'Eigene Daten':
        precise_dates = col_sel.toggle(
            'Exakten Zeitraum wählen', key='prec_dates_heat_load'
        )
        if precise_dates:
            dates = col_sel.date_input(
                'Zeitraum auswählen:',
                value=(
                    date(int(heat_load_year), 3, 28),
                    date(int(heat_load_year), 7, 2)
                    ),
                min_value=date(int(heat_load_year), 1, 1),
                max_value=date(int(heat_load_year), 12, 31),
                format='DD.MM.YYYY', key='date_picker_heat_load'
                )
            dates = [
                datetime(year=d.year, month=d.month, day=d.day) for d in dates
                ]
            heat_load = heat_load.loc[dates[0]:dates[1], :]

        scale_hl = col_sel.toggle('Daten skalieren')
        if scale_hl:
            scale_method = col_sel.selectbox('Methode', ['Faktor', 'Erweitert'])
            if scale_method == 'Faktor':
                scale_factor = col_sel.number_input(
                    'Skalierungsfaktor', value=1.0, step=0.1, min_value=0.0
                    )
                heat_load[dataset_name] *= scale_factor
            elif scale_method == 'Erweitert':
                scale_amp = col_sel.number_input(
                    'Stauchungsfaktor', value=1.0, step=0.1, min_value=0.0,
                    help='Staucht die Lastdaten um den Median.'
                    )
                scale_off = col_sel.number_input(
                    'Offset', value=1.0, step=0.1,
                    help='Verschiebt den Median der Lastdaten.'
                    )
                heat_load_median = heat_load[dataset_name].median()
                heat_load[dataset_name] = (
                    (heat_load[dataset_name] - heat_load_median) * scale_amp
                    + heat_load_median + scale_off
                    )
                # negative_mask = heat_load[dataset_name] < 0
                if (heat_load[dataset_name] < 0).values.any():
                    st.error(
                        'Durch die Skalierung resultiert eine negative '
                        + 'Wärmelast. Bitte den Offset anpassen.'
                        )

    if user_file is not None or dataset_name != 'Eigene Daten':
        heat_load.rename(columns={heat_load.columns[0]: 'heat_load'}, inplace=True)
        heat_load.index.names = ['Date']
        heat_load.reset_index(inplace=True)

        col_vis.altair_chart(
            alt.Chart(heat_load).mark_line(color='#EC6707').encode(
                y=alt.Y('heat_load', title='Stündliche Wärmelast in MWh'),
                x=alt.X('Date', title='Datum')
            ),
            use_container_width=True
        )

    st.subheader('Wärmeerlöse')

    heat_revenue = 80.00
    st.number_input('Wärmeerlös in €/MWh', value=heat_revenue, key='heat_revenue')

# %% MARK: Electricity
with tab4:
    st.header('Elektrizitätsversorgungsdaten')
    col_elp, col_vis_el = st.columns([1, 2])

    col_elp.subheader('Spotmarkt Strompreisdaten')

    el_prices_years = list(ss.all_el_prices.index.year.unique())
    el_prices_year = col_elp.selectbox(
        'Wähle das Jahr der Strompreisdaten aus',
        el_prices_years, index=el_prices_years.index(heat_load_year),
        placeholder='Betrachtungsjahr'
    )
    el_prices = ss.all_el_prices[ss.all_el_prices.index.year == el_prices_year]

    precise_dates = col_elp.toggle(
        'Exakten Zeitraum wählen', key='prec_dates_el_prices'
        )
    if precise_dates:
        el_dates = col_elp.date_input(
            'Zeitraum auswählen:',
            value=dates if dates is not None else (
                date(int(heat_load_year), 3, 28),
                date(int(heat_load_year), 7, 2)
                ),
            min_value=date(int(heat_load_year), 1, 1),
            max_value=date(int(heat_load_year), 12, 31),
            format='DD.MM.YYYY', key='date_picker_el_prices'
            )
        el_dates = [
            datetime(year=d.year, month=d.month, day=d.day) for d in el_dates
            ]
        el_prices = el_prices.loc[el_dates[0]:el_dates[1], :]

    nr_steps_hl = len(heat_load.index)
    nr_steps_el = len(el_prices.index)
    if nr_steps_hl != nr_steps_el:
        st.error(
            f'Die Anzahl der Zeitschritte der Wärmelastdaten ({nr_steps_hl}) '
            + f'stimmt nicht mit denen der Strompreiszeitreihe ({nr_steps_el}) '
            + 'überein. Bitte die Daten angleichen.'
            )

    col_elp.subheader('Strompreisbestandteile')
    # csv einlesen
    # for schleife wie bei Anlagenparameter

    col_vis_el.subheader('Spotmarkt Strompreise')
    el_prices.reset_index(inplace=True)
    col_vis_el.altair_chart(
        alt.Chart(el_prices).mark_line(color='#00395B').encode(
            y=alt.Y('El Price', title='Day-Ahead Spotmarkt Strompreise in €/MWh'),
            x=alt.X('Date', title='Datum')
            ),
        use_container_width=True
        )

    col_vis_el.subheader('Emissionsfaktoren des Strommixes')

# %% MARK: Gas
with tab5:
    st.header('Gasversorgungsdaten')