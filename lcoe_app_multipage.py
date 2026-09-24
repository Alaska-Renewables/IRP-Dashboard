# app.py
# Streamlit dashboard for scenario LCOE and carrier-level summaries
# pip install streamlit pandas numpy plotly openpyxl

import io
import math
import numpy as np
import pandas as pd
import streamlit as st
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import json
import datetime

st.set_page_config(
    page_title="Simulation LCOE Dashboard", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------
# Page Navigation
# -----------------------------
st.sidebar.markdown("## Navigation")
page = st.sidebar.selectbox("Select Page", ["📊 Main Results", "🔍 Sensitivity Analysis", "⚡ Generator Breakdown"])

# Configuration Management
# -----------------------------
st.sidebar.markdown("---")
st.sidebar.markdown("## 💾 Configuration Management")

# Initialize session state for configurations
if 'saved_configs' not in st.session_state:
    st.session_state.saved_configs = {}

def save_current_config(config_name, params, cost_df=None, fuel_df=None):
    """Save current configuration to session state with optional cost/fuel data."""
    config = {
        'name': config_name,
        'timestamp': datetime.datetime.now().isoformat(),
        'parameters': params.copy(),
        'cost_data': serialize_dataframe_to_json(cost_df),
        'fuel_data': serialize_dataframe_to_json(fuel_df)
    }
    st.session_state.saved_configs[config_name] = config
    return config

def load_config(config_name):
    """Load configuration from session state."""
    if config_name in st.session_state.saved_configs:
        config = st.session_state.saved_configs[config_name]
        return {
            'parameters': config.get('parameters', {}),
            'cost_data': config.get('cost_data', None),
            'fuel_data': config.get('fuel_data', None)
        }
    return None

def export_configs_json():
    """Export all configurations as JSON."""
    return json.dumps(st.session_state.saved_configs, indent=2)

def import_configs_json(json_str):
    """Import configurations from JSON."""
    try:
        imported_configs = json.loads(json_str)
        st.session_state.saved_configs.update(imported_configs)
        return True, len(imported_configs)
    except Exception as e:
        return False, str(e)

def serialize_dataframe_to_json(df):
    """Convert a DataFrame to a JSON-serializable format (CSV string in dict)."""
    if df is None or df.empty:
        return None
    import io
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    return {'_type': 'dataframe_csv', 'csv_data': csv_buffer.getvalue()}

def deserialize_dataframe_from_json(data):
    """Convert JSON-serialized DataFrame back to DataFrame."""
    if data is None or not isinstance(data, dict):
        return None
    if data.get('_type') != 'dataframe_csv':
        return None
    import io
    csv_buffer = io.StringIO(data['csv_data'])
    return pd.read_csv(csv_buffer)

# Configuration save/load interface
with st.sidebar.expander("🔧 Save & Load Configurations"):
    st.markdown("**Save Current Settings:**")
    
    # Get default configuration name based on current timestamp
    default_name = f"Config_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}"
    new_config_name = st.text_input("Configuration Name:", value=default_name)
    
    if st.button("💾 Save Current Configuration", type="primary"):
        if new_config_name.strip():
            # We'll collect the actual parameters later when we modify the sidebar inputs
            st.session_state.pending_save = new_config_name.strip()
        else:
            st.error("Please enter a configuration name")
    
    st.markdown("**Export/Import:**")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📤 Export All") and st.session_state.saved_configs:
            export_json = export_configs_json()
            st.download_button(
                label="📥 Download JSON",
                data=export_json,
                file_name=f"lcoe_configs_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json"
            )
    
    with col2:
        uploaded_config = st.file_uploader("Import JSON", type="json", key="config_import")
        if uploaded_config:
            import_json = uploaded_config.read().decode()
            success, result = import_configs_json(import_json)
            if success:
                st.success(f"✅ Imported {result} configurations")
            else:
                st.error(f"❌ Import failed: {result}")
    
    st.markdown("**Load Saved Configuration:**")
    if st.session_state.saved_configs:
        config_options = list(st.session_state.saved_configs.keys())
        selected_config = st.selectbox("Select Configuration:", options=[""] + config_options)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📁 Load Configuration") and selected_config:
                st.session_state.load_config = selected_config
        with col2:
            if st.button("🗑️ Delete") and selected_config:
                del st.session_state.saved_configs[selected_config]
        
        # Show configuration details
        if selected_config and selected_config in st.session_state.saved_configs:
            config = st.session_state.saved_configs[selected_config]
            st.caption(f"Saved: {config['timestamp'][:19].replace('T', ' ')}")
    else:
        st.info("No saved configurations")
    
    st.markdown("**Reset to Defaults:**")
    if st.button("🔄 Reset All Filters & Costs", help="Clear all filters and revert to original input file values"):
        # Clear all filter session states to show all scenarios
        keys_to_remove = [key for key in st.session_state.keys() if key.startswith('filter_multiselect_')]
        for key in keys_to_remove:
            del st.session_state[key]
        
        # Reset all sidebar parameters to defaults
        config_defaults = {
            'start_year': 2030,
            'end_year': 2049,
            'use_global_discount': True,
            'global_discount_rate': 5.0,
            'capex_treatment_index': 1,
            'asset_life_years': 30
        }
        
        # Reset sidebar input session states
        st.session_state.start_year_input = config_defaults['start_year']
        st.session_state.end_year_input = config_defaults['end_year']
        st.session_state.use_global_discount_input = config_defaults['use_global_discount']
        st.session_state.global_discount_rate_input = config_defaults['global_discount_rate']
        st.session_state.capex_treatment_input_index = config_defaults['capex_treatment_index']
        st.session_state.asset_life_years_input = config_defaults['asset_life_years']
        
        # Reset wind override parameters
        st.session_state.wind_override_enabled = False
        st.session_state.wind_capex = 1500.0
        st.session_state.wind_capex_year = 2030
        st.session_state.wind_first_year = 2030
        st.session_state.wind_discount = 5.0
        st.session_state.wind_var_cost = 0.0
        st.session_state.wind_var_esc = 2.5
        st.session_state.wind_fixed_cost = 30.0
        st.session_state.wind_fixed_esc = 2.5
        
        # Reset solar override parameters
        st.session_state.solar_override_enabled = False
        st.session_state.solar_capex = 1200.0
        st.session_state.solar_capex_year = 2030
        st.session_state.solar_first_year = 2030
        st.session_state.solar_discount = 5.0
        st.session_state.solar_var_cost = 0.0
        st.session_state.solar_var_esc = 2.5
        st.session_state.solar_fixed_cost = 20.0
        st.session_state.solar_fixed_esc = 2.5
        
        # Reset cost editor data to original input file values
        if 'gen_costs' in st.session_state:
            del st.session_state['gen_costs']
        if 'fuel_costs' in st.session_state:
            del st.session_state['fuel_costs']
        
        # Set flag to force reload of original data files
        st.session_state.force_data_reload = True
        
        st.success("✅ All filters and settings reset to defaults!")

# -----------------------------
# Helpers
# -----------------------------
def to_float(x):
    if pd.isna(x):
        return np.nan
    if isinstance(x, (int, float, np.number)):
        return float(x)
    s = str(x).strip().replace(",", "")
    # handle percent-like "2.5%" -> 0.025
    if s.endswith("%"):
        try:
            return float(s[:-1]) / 100.0
        except:
            return np.nan
    try:
        return float(s)
    except:
        return np.nan

def escalate(value_base, rate, years_elapsed):
    """Escalate a value from base by annual rate for 'years_elapsed'."""
    if pd.isna(value_base) or pd.isna(rate):
        return np.nan
    return float(value_base) * ((1.0 + float(rate)) ** int(years_elapsed))

def discount_factor(rate, years_elapsed):
    """Present-value discount factor for year offset (0-based)."""
    return 1.0 / ((1.0 + float(rate)) ** int(years_elapsed))

def capital_recovery_factor(rate, life_years):
    r = float(rate)
    n = int(life_years)
    if n <= 0:
        return 1.0
    if r == 0:
        return 1.0 / n
    return (r * (1 + r) ** n) / ((1 + r) ** n - 1)

def safe_strip_list(cell):
    """Parse comma-separated strings like 'Fire_Island, Eva_Creek' to list."""
    if pd.isna(cell):
        return []
    return [c.strip() for c in str(cell).split(",") if str(c).strip()]

def generation_weighted_cf(df):
    """Generation-weighted CF by carrier within a scenario."""
    # CF = Gen / (Capacity*8760) for each generator -> weight by capacity or by gen?
    # Use capacity-weighted average of provided CF% if present; fall back to Gen/(Cap*8760)
    if "Capacity_Factor_pct" in df.columns:
        cf = (df["Capacity_Factor_pct"].astype(float) / 100.0).clip(lower=0)
    else:
        cap = df["Scenario_Capacity_MW"].astype(float).clip(lower=0)
        gen = df["Total_Generation_MWh"].astype(float).clip(lower=0)
        cf = (gen / (cap * 8760.0)).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    cap_w = df["Scenario_Capacity_MW"].astype(float).clip(lower=0)
    return (cf * cap_w).sum() / (cap_w.sum() if cap_w.sum() else 1.0)

# -----------------------------
# Sidebar: Inputs & Uploads
# -----------------------------
st.sidebar.header("Inputs & Files")

st.sidebar.markdown("**1) Upload operations (per generator per scenario)**")
ops_file = st.sidebar.file_uploader("Operations file (CSV or Excel)", type=["csv","xlsx","xls"], key="ops")
st.sidebar.markdown("**2) Upload generator cost inputs**")
cost_file = st.sidebar.file_uploader("Generator costs (CSV or Excel)", type=["csv","xlsx","xls"], key="costs")
st.sidebar.markdown("**3) Upload base year fuel prices**")
fuel_file = st.sidebar.file_uploader("Fuel prices (CSV or Excel)", type=["csv","xlsx","xls"], key="fuel")

# Reset filters when new data is uploaded to show all scenarios by default
if ops_file is not None:
    # Check if this is a new file upload by comparing with stored filename
    current_ops_filename = getattr(ops_file, 'name', None)
    if 'last_ops_filename' not in st.session_state:
        st.session_state.last_ops_filename = None
    
    # If a new operations file is uploaded, clear all filter session state
    if st.session_state.last_ops_filename != current_ops_filename:
        st.session_state.last_ops_filename = current_ops_filename
        # Clear all filter session states to show all scenarios by default
        keys_to_remove = [key for key in st.session_state.keys() if key.startswith('filter_multiselect_')]
        for key in keys_to_remove:
            del st.session_state[key]

# Reset cost editor data when new cost files are uploaded
if cost_file is not None:
    current_cost_filename = getattr(cost_file, 'name', None)
    if 'last_cost_filename' not in st.session_state:
        st.session_state.last_cost_filename = None
    
    if st.session_state.last_cost_filename != current_cost_filename:
        st.session_state.last_cost_filename = current_cost_filename
        # Clear generator cost editor session state to revert to file values
        if 'gen_costs' in st.session_state:
            del st.session_state['gen_costs']

# Reset fuel editor data when new fuel files are uploaded  
if fuel_file is not None:
    current_fuel_filename = getattr(fuel_file, 'name', None)
    if 'last_fuel_filename' not in st.session_state:
        st.session_state.last_fuel_filename = None
    
    if st.session_state.last_fuel_filename != current_fuel_filename:
        st.session_state.last_fuel_filename = current_fuel_filename
        # Clear fuel cost editor session state to revert to file values
        if 'fuel_costs' in st.session_state:
            del st.session_state['fuel_costs']

st.sidebar.markdown("---")
st.sidebar.markdown("**Time Horizon & Finance**")

# Handle configuration loading
config_defaults = {
    'start_year': 2030,
    'end_year': 2049,
    'use_global_discount': True,
    'global_discount_rate': 5.0,
    'capex_treatment_index': 1,
    'asset_life_years': 30
}

# Load configuration if requested
loaded_config = None
if 'load_config' in st.session_state:
    config_result = load_config(st.session_state.load_config)
    if config_result:
        config_name = st.session_state.load_config
        loaded_config = config_result['parameters']
        loaded_cost_data = config_result['cost_data']
        loaded_fuel_data = config_result['fuel_data']
        
        # Restore cost and fuel DataFrames to session state
        if loaded_cost_data is not None:
            st.session_state.loaded_cost_df = deserialize_dataframe_from_json(loaded_cost_data)
        if loaded_fuel_data is not None:
            st.session_state.loaded_fuel_df = deserialize_dataframe_from_json(loaded_fuel_data)
        
        # Update session state with loaded values - Sidebar inputs
        st.session_state.start_year_input = loaded_config.get('start_year', config_defaults['start_year'])
        st.session_state.end_year_input = loaded_config.get('end_year', config_defaults['end_year'])
        st.session_state.use_global_discount_input = loaded_config.get('use_global_discount', config_defaults['use_global_discount'])
        st.session_state.global_discount_rate_input = loaded_config.get('global_discount_rate', config_defaults['global_discount_rate'])
        st.session_state.capex_treatment_input_index = loaded_config.get('capex_treatment_index', config_defaults['capex_treatment_index'])
        st.session_state.asset_life_years_input = loaded_config.get('asset_life_years', config_defaults['asset_life_years'])
        
        # Wind override parameters
        st.session_state.wind_override_enabled = loaded_config.get('wind_override_enabled', False)
        st.session_state.wind_capex = loaded_config.get('wind_capex', 1500.0)
        st.session_state.wind_capex_year = loaded_config.get('wind_capex_year', 2030)
        st.session_state.wind_first_year = loaded_config.get('wind_first_year', 2030)
        st.session_state.wind_discount = loaded_config.get('wind_discount', 5.0)
        st.session_state.wind_var_cost = loaded_config.get('wind_var_cost', 0.0)
        st.session_state.wind_var_esc = loaded_config.get('wind_var_esc', 2.5)
        st.session_state.wind_fixed_cost = loaded_config.get('wind_fixed_cost', 30.0)
        st.session_state.wind_fixed_esc = loaded_config.get('wind_fixed_esc', 2.5)
        
        # Solar override parameters
        st.session_state.solar_override_enabled = loaded_config.get('solar_override_enabled', False)
        st.session_state.solar_capex = loaded_config.get('solar_capex', 1200.0)
        st.session_state.solar_capex_year = loaded_config.get('solar_capex_year', 2030)
        st.session_state.solar_first_year = loaded_config.get('solar_first_year', 2030)
        st.session_state.solar_discount = loaded_config.get('solar_discount', 5.0)
        st.session_state.solar_var_cost = loaded_config.get('solar_var_cost', 0.0)
        st.session_state.solar_var_esc = loaded_config.get('solar_var_esc', 2.5)
        st.session_state.solar_fixed_cost = loaded_config.get('solar_fixed_cost', 20.0)
        st.session_state.solar_fixed_esc = loaded_config.get('solar_fixed_esc', 2.5)
        
        # Load filter parameters
        for key, value in loaded_config.items():
            if key.startswith('filter_'):
                # Convert filter parameter keys to multiselect keys
                multiselect_key = key.replace('filter_', 'filter_multiselect_')
                st.session_state[multiselect_key] = value
        
        # Clear the load flag
        del st.session_state.load_config
        st.sidebar.success(f"✅ Loaded configuration: {config_name}")

# Initialize session state if not present
if 'start_year_input' not in st.session_state:
    st.session_state.start_year_input = config_defaults['start_year']
if 'end_year_input' not in st.session_state:
    st.session_state.end_year_input = config_defaults['end_year']
if 'use_global_discount_input' not in st.session_state:
    st.session_state.use_global_discount_input = config_defaults['use_global_discount']
if 'global_discount_rate_input' not in st.session_state:
    st.session_state.global_discount_rate_input = config_defaults['global_discount_rate']
if 'capex_treatment_input_index' not in st.session_state:
    st.session_state.capex_treatment_input_index = config_defaults['capex_treatment_index']
if 'asset_life_years_input' not in st.session_state:
    st.session_state.asset_life_years_input = config_defaults['asset_life_years']

# Input controls with configuration support
start_year = st.sidebar.number_input(
    "Start year", 
    min_value=2000, max_value=2100, 
    value=st.session_state.start_year_input, 
    step=1, key="start_year_input"
)

end_year = st.sidebar.number_input(
    "End year (inclusive)", 
    min_value=start_year, max_value=2100, 
    value=st.session_state.end_year_input, 
    step=1, key="end_year_input"
)

use_global_discount = st.sidebar.checkbox(
    "Use global discount rate for LCOE (override per-generator rates)", 
    value=st.session_state.use_global_discount_input,
    key="use_global_discount_input"
)

global_discount_rate = st.sidebar.number_input(
    "Global discount rate (%)", 
    min_value=0.0, max_value=100.0, 
    value=st.session_state.global_discount_rate_input, 
    step=0.1, key="global_discount_rate_input"
) / 100.0

st.sidebar.markdown("**Capital Cost Treatment**")
capex_treatment_options = ["Upfront (PV in first in-horizon year)", "Annualized (CRF over life)"]

capex_treatment = st.sidebar.selectbox(
    "How to include CAPEX in LCOE?",
    options=capex_treatment_options, 
    index=st.session_state.capex_treatment_input_index,
    key="capex_treatment_input"
)

asset_life_years = st.sidebar.number_input(
    "Asset life (years) for annualization", 
    min_value=1, max_value=60, 
    value=st.session_state.asset_life_years_input, 
    step=1, key="asset_life_years_input"
)

# Set default values for removed inputs
repeat_ops_each_year = True
hours_per_year = 8760

# -----------------------------
# Load data (with examples if empty) - Cached for performance
# -----------------------------
@st.cache_data
def load_any(fileobj):
    if fileobj is None:
        return None
    name = fileobj.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(fileobj)
    return pd.read_excel(fileobj)

@st.cache_data  
def process_operations_data(_ops_df, selected_filters):
    """Process and filter operations data with caching."""
    # Apply filters
    mask = pd.Series(True, index=_ops_df.index)
    for c, choices in selected_filters.items():
        if choices:
            mask = mask & (_ops_df[c].astype(str).isin(choices))
    
    return _ops_df[mask].copy()

# Example fallback (so the app can run without uploads)
ops_df = load_any(ops_file)
if ops_df is None:
    # Create example data with gas, wind, and solar generators
    base_scenario = "No_AK_Intertie_Upgrade_S00_Wind3_DC0_Geo0_NLoad30"
    ops_df = pd.DataFrame({
        "Scenario": [base_scenario]*7,
        "Generator": ["Plant2A-2CC","SPP-3CC","Plant1-3","Wind_Farm_1","Wind_Farm_2","Solar_Plant_1","Solar_Plant_2"],
        "Carrier": ["gas","gas","gas","wind","wind","solar","solar"],
        "Bus": ["central","central","central","central","northern","central","southern"],
        "Scenario_Capacity_MW": [122,176,32.9,150,200,100,75],
        "Capacity_Modified": [False]*7,
        "param_wind_projects_count":[3]*7,
        "param_wind_projects":["Fire_Island, Eva_Creek, Delta_Wind"]*7,
        "param_solar_projects_count":[2]*7,
        "param_solar_projects":["Houston_Solar, Fairbanks_Solar"]*7,
        "param_bradley_as_reservoir":[True]*7,
        "param_single_LBA":[True]*7,
        "param_datacenter_central_mw":[0]*7,
        "param_datacenter_central_cf":[0.8]*7,
        "param_gen_healy_1_p_nom":[0]*7,
        "param_gen_healy_2_p_nom":[0]*7,
        "param_gen_new_CC_central_p_nom":[0]*7,
        "param_gen_new_CC_northern_p_nom":[0]*7,
        "param_gen_new_CC_southern_p_nom":[0]*7,
        "param_gen_new_geo_healy_marginal_cost":[0]*7,
        "param_gen_new_geo_healy_p_nom":[100]*7,
        "param_link_healy_central_p_nom":[0]*7,
        "param_link_northern_healy_p_nom":[75]*7,
        "param_load_load_northern_p_set_scale":[150]*7,
        "Total_Generation_MWh":[1140861.04, 1635749.28, 2001.04357, 525600.0, 700800.0, 175200.0, 131400.0],
        "Capacity_Factor_pct":[106.7502283, 106.0962329, 0.694314989, 40.0, 40.0, 20.0, 20.0],  # CF>100% can occur if nameplate differs; not used directly for gen
        "Curtailment_pct":[0]*7,
        "Max_Output_MW":[175.68, 253.44, 42.441, 150.0, 200.0, 100.0, 75.0],
        "Min_Output_MW":[100.04, 144.32, 0.239275708, 0.0, 0.0, 0.0, 0.0],
        "Hours_Operating":[8322,8322,79, 3504, 3504, 1752, 1752],
        "Curtailed_Energy_MWh":[0]*7,
        "Heat_Rate_MMBtu_per_MWh":[7.5,7.5,14.0,0.0,0.0,0.0,0.0],
        "Fuel_Consumption_MMBtu":[8556457.8, 12268119.6, 28014.60998, 0.0, 0.0, 0.0, 0.0],
    })

# Check if cost/fuel data was restored from a saved configuration
if 'loaded_cost_df' in st.session_state:
    cost_df = st.session_state.loaded_cost_df
else:
    cost_df = load_any(cost_file)
    
if cost_df is None:
    cost_df = pd.DataFrame({
        "Generator":["Plant2A-2CC","SPP-3CC","Plant1-3","Plant2-7","Wind_Farm_1","Wind_Farm_2","Solar_Plant_1","Solar_Plant_2"],
        "Carrier":["gas","gas","gas","gas","wind","wind","solar","solar"],
        "Non-fuel var cost escalation rate (%/yr)":["2.5%"]*4 + ["2.0%"]*2 + ["1.5%"]*2,
        "Fixed Production escalation rate (%/yr)":["2.50%"]*4 + ["2.00%"]*2 + ["1.50%"]*2,
        "Capital cost ($/kW)":[0,0,0,0,1600,1500,1300,1200],
        "Capital cost year":[2030]*8,
        "Discount rate (%)":["5%"]*4 + ["4.5%"]*2 + ["4.0%"]*2,
        "First year":[2030]*8,
        "2024 Non-fuel var cost ($/MWh)":[8,8,4,4,0,0,0,0],
        "2024 Fixed Production cost ($/kW-yr)":[24,32,43,24,35,30,25,20],
    })

if 'loaded_fuel_df' in st.session_state:
    fuel_df = st.session_state.loaded_fuel_df
else:
    fuel_df = load_any(fuel_file)
    
if fuel_df is None:
    fuel_df = pd.DataFrame({
        "Fuel":["gas","diesel","naphtha","coal","landfill","hydro","wind","solar","geo","slack"],
        "2024 Fuel cost ($/MMBtu)":[12,20,19,5,0,0,0,0,0,0],
        "Fuel escalation rate (%/yr)":["2.5%"]*10
    })

# Standardize column names a bit
ops_df.columns = [c.strip() for c in ops_df.columns]
cost_df.columns = [c.strip() for c in cost_df.columns]
fuel_df.columns = [c.strip() for c in fuel_df.columns]

# Clear the loaded dataframes from session state after use
if 'loaded_cost_df' in st.session_state:
    del st.session_state['loaded_cost_df']
if 'loaded_fuel_df' in st.session_state:
    del st.session_state['loaded_fuel_df']

# Force reload of original data if reset button was pressed
if st.session_state.get('force_data_reload', False):
    # Clear any remaining editor session state to ensure clean reload
    if 'gen_costs' in st.session_state:
        del st.session_state['gen_costs']
    if 'fuel_costs' in st.session_state:
        del st.session_state['fuel_costs']
    
    # Set a new reset counter to force new editor keys
    if 'reset_counter' not in st.session_state:
        st.session_state.reset_counter = 0
    st.session_state.reset_counter += 1
    
    # Reload original cost data from file (or fallback to example data)
    if cost_file is not None:
        cost_df = load_any(cost_file)
        cost_df.columns = [c.strip() for c in cost_df.columns]
    else:
        cost_df = pd.DataFrame({
            "Generator":["Plant2A-2CC","SPP-3CC","Plant1-3","Plant2-7","Wind_Farm_1","Wind_Farm_2","Solar_Plant_1","Solar_Plant_2"],
            "Carrier":["gas","gas","gas","gas","wind","wind","solar","solar"],
            "Non-fuel var cost escalation rate (%/yr)":["2.5%"]*4 + ["2.0%"]*2 + ["1.5%"]*2,
            "Fixed Production escalation rate (%/yr)":["2.50%"]*4 + ["2.00%"]*2 + ["1.50%"]*2,
            "Capital cost ($/kW)":[0,0,0,0,1600,1500,1300,1200],
            "Capital cost year":[2030]*8,
            "Discount rate (%)":["5%"]*4 + ["4.5%"]*2 + ["4.0%"]*2,
            "First year":[2030]*8,
            "2024 Non-fuel var cost ($/MWh)":[8,8,4,4,0,0,0,0],
            "2024 Fixed Production cost ($/kW-yr)":[24,32,43,24,35,30,25,20],
        })
        cost_df.columns = [c.strip() for c in cost_df.columns]
    
    # Reload original fuel data from file (or fallback to example data)
    if fuel_file is not None:
        fuel_df = load_any(fuel_file)
        fuel_df.columns = [c.strip() for c in fuel_df.columns]
    else:
        fuel_df = pd.DataFrame({
            "Fuel":["gas","diesel","naphtha","coal","landfill","hydro","wind","solar","geo","slack"],
            "2024 Fuel cost ($/MMBtu)":[12,20,19,5,0,0,0,0,0,0],
            "Fuel escalation rate (%/yr)":["2.5%"]*10
        })
        fuel_df.columns = [c.strip() for c in fuel_df.columns]
    
    # Clear the flag
    del st.session_state.force_data_reload

# Create dynamic editor keys to force refresh after reset
gen_costs_key = f"gen_costs_{st.session_state.get('reset_counter', 0)}"
fuel_costs_key = f"fuel_costs_{st.session_state.get('reset_counter', 0)}"

# -----------------------------
# Wind and Solar Cost Override Options
# -----------------------------

# Initialize configuration saving variable
current_config_to_save = None
if 'pending_save' in st.session_state:
    config_name = st.session_state.pending_save
    
    # Collect current configuration parameters (sidebar inputs)
    current_config_to_save = {
        'start_year': start_year,
        'end_year': end_year,
        'use_global_discount': use_global_discount,
        'global_discount_rate': global_discount_rate * 100.0,  # Store as percentage
        'capex_treatment_index': capex_treatment_options.index(capex_treatment),
        'asset_life_years': asset_life_years
    }

st.markdown("### 🔄 Wind & Solar Cost Override Options")
st.markdown("Override individual wind and solar generator costs with standardized technology-specific values.")

with st.expander("🌬️ Wind Technology Cost Overrides"):
    use_wind_override = st.checkbox("Use standardized wind costs for all wind generators", value=False, key="wind_override_enabled")
    
    if use_wind_override:
        wind_col1, wind_col2 = st.columns(2)
        
        with wind_col1:
            wind_capex = st.number_input("Wind Capital Cost ($/kW)", min_value=0.0, value=1500.0, step=50.0, key="wind_capex")
            wind_capex_year = st.number_input("Wind Capital Cost Year", min_value=2020, max_value=2050, value=2030, step=1, key="wind_capex_year")
            wind_first_year = st.number_input("Wind First Year", min_value=2020, max_value=2050, value=2030, step=1, key="wind_first_year")
            wind_discount_rate = st.number_input("Wind Discount Rate (%)", min_value=0.0, max_value=20.0, value=5.0, step=0.1, key="wind_discount") / 100.0
        
        with wind_col2:
            wind_var_cost = st.number_input("Wind 2024 Non-fuel Var Cost ($/MWh)", min_value=0.0, value=0.0, step=0.1, key="wind_var_cost")
            wind_var_esc = st.number_input("Wind Non-fuel Var Cost Escalation (%/yr)", min_value=0.0, max_value=10.0, value=2.5, step=0.1, key="wind_var_esc") / 100.0
            wind_fixed_cost = st.number_input("Wind 2024 Fixed Production Cost ($/kW-yr)", min_value=0.0, value=30.0, step=1.0, key="wind_fixed_cost")
            wind_fixed_esc = st.number_input("Wind Fixed Production Escalation (%/yr)", min_value=0.0, max_value=10.0, value=2.5, step=0.1, key="wind_fixed_esc") / 100.0
    else:
        # Default values when not in override mode
        wind_capex = 1500.0
        wind_capex_year = 2030
        wind_first_year = 2030
        wind_discount_rate = 0.05
        wind_var_cost = 0.0
        wind_var_esc = 0.025
        wind_fixed_cost = 30.0
        wind_fixed_esc = 0.025

with st.expander("☀️ Solar Technology Cost Overrides"):
    use_solar_override = st.checkbox("Use standardized solar costs for all solar generators", value=False, key="solar_override_enabled")
    
    if use_solar_override:
        solar_col1, solar_col2 = st.columns(2)
        
        with solar_col1:
            solar_capex = st.number_input("Solar Capital Cost ($/kW)", min_value=0.0, value=1200.0, step=50.0, key="solar_capex")
            solar_capex_year = st.number_input("Solar Capital Cost Year", min_value=2020, max_value=2050, value=2030, step=1, key="solar_capex_year")
            solar_first_year = st.number_input("Solar First Year", min_value=2020, max_value=2050, value=2030, step=1, key="solar_first_year")
            solar_discount_rate = st.number_input("Solar Discount Rate (%)", min_value=0.0, max_value=20.0, value=5.0, step=0.1, key="solar_discount") / 100.0
        
        with solar_col2:
            solar_var_cost = st.number_input("Solar 2024 Non-fuel Var Cost ($/MWh)", min_value=0.0, value=0.0, step=0.1, key="solar_var_cost")
            solar_var_esc = st.number_input("Solar Non-fuel Var Cost Escalation (%/yr)", min_value=0.0, max_value=10.0, value=2.5, step=0.1, key="solar_var_esc") / 100.0
            solar_fixed_cost = st.number_input("Solar 2024 Fixed Production Cost ($/kW-yr)", min_value=0.0, value=20.0, step=1.0, key="solar_fixed_cost")
            solar_fixed_esc = st.number_input("Solar Fixed Production Escalation (%/yr)", min_value=0.0, max_value=10.0, value=2.5, step=0.1, key="solar_fixed_esc") / 100.0
    else:
        # Default values when not in override mode
        solar_capex = 1200.0
        solar_capex_year = 2030
        solar_first_year = 2030
        solar_discount_rate = 0.05
        solar_var_cost = 0.0
        solar_var_esc = 0.025
        solar_fixed_cost = 20.0
        solar_fixed_esc = 0.025

if use_wind_override or use_solar_override:
    st.info("💡 **Override Behavior**: When enabled, these standardized costs will replace the individual generator costs for all wind/solar generators in the cost table below. This is useful for sensitivity analysis and standardizing renewable technology assumptions.")

# Note: Configuration saving logic moved to after all variables are defined

# -----------------------------
# Shared Data Processing (available to both pages)
# -----------------------------

# Editable cost tables
st.markdown("### Cost Inputs (editable)")
with st.expander("Generator Cost Inputs"):
    edited_cost = st.data_editor(cost_df, use_container_width=True, num_rows="dynamic", key=gen_costs_key)
with st.expander("Fuel Costs (base year)"):
    edited_fuel = st.data_editor(fuel_df, use_container_width=True, num_rows="dynamic", key=fuel_costs_key)

cost_df = edited_cost.copy()
fuel_df = edited_fuel.copy()

# Parse numeric columns
for col in ["Non-fuel var cost escalation rate (%/yr)",
            "Fixed Production escalation rate (%/yr)",
            "Discount rate (%)",
            "2024 Non-fuel var cost ($/MWh)",
            "2024 Fixed Production cost ($/kW-yr)",
            "Capital cost ($/kW)"]:
    if col in cost_df.columns:
        cost_df[col] = cost_df[col].apply(to_float)

if "2024 Fuel cost ($/MMBtu)" in fuel_df.columns:
    fuel_df["2024 Fuel cost ($/MMBtu)"] = fuel_df["2024 Fuel cost ($/MMBtu)"].apply(to_float)

if "Fuel escalation rate (%/yr)" in fuel_df.columns:
    fuel_df["Fuel escalation rate (%/yr)"] = fuel_df["Fuel escalation rate (%/yr)"].apply(to_float)

# -----------------------------
# Apply Wind & Solar Cost Overrides
# -----------------------------
override_summary = []

if use_wind_override:
    wind_mask = cost_df["Carrier"].str.lower() == "wind"
    if wind_mask.any():
        wind_generators = cost_df[wind_mask]["Generator"].tolist()
        override_summary.append(f"🌬️ **Wind Override Applied**: {len(wind_generators)} generators")
        override_summary.append(f"   - Generators: {', '.join(wind_generators)}")
        override_summary.append(f"   - Capital Cost: ${wind_capex:,.0f}/kW")
        override_summary.append(f"   - Fixed O&M: ${wind_fixed_cost:,.0f}/kW-yr")
        
        cost_df.loc[wind_mask, "Capital cost ($/kW)"] = wind_capex
        cost_df.loc[wind_mask, "Capital cost year"] = wind_capex_year
        cost_df.loc[wind_mask, "First year"] = wind_first_year
        cost_df.loc[wind_mask, "Discount rate (%)"] = wind_discount_rate
        cost_df.loc[wind_mask, "2024 Non-fuel var cost ($/MWh)"] = wind_var_cost
        cost_df.loc[wind_mask, "Non-fuel var cost escalation rate (%/yr)"] = wind_var_esc
        cost_df.loc[wind_mask, "2024 Fixed Production cost ($/kW-yr)"] = wind_fixed_cost
        cost_df.loc[wind_mask, "Fixed Production escalation rate (%/yr)"] = wind_fixed_esc

if use_solar_override:
    solar_mask = cost_df["Carrier"].str.lower() == "solar"
    if solar_mask.any():
        solar_generators = cost_df[solar_mask]["Generator"].tolist()
        override_summary.append(f"☀️ **Solar Override Applied**: {len(solar_generators)} generators")
        override_summary.append(f"   - Generators: {', '.join(solar_generators)}")
        override_summary.append(f"   - Capital Cost: ${solar_capex:,.0f}/kW")
        override_summary.append(f"   - Fixed O&M: ${solar_fixed_cost:,.0f}/kW-yr")
        
        cost_df.loc[solar_mask, "Capital cost ($/kW)"] = solar_capex
        cost_df.loc[solar_mask, "Capital cost year"] = solar_capex_year
        cost_df.loc[solar_mask, "First year"] = solar_first_year
        cost_df.loc[solar_mask, "Discount rate (%)"] = solar_discount_rate
        cost_df.loc[solar_mask, "2024 Non-fuel var cost ($/MWh)"] = solar_var_cost
        cost_df.loc[solar_mask, "Non-fuel var cost escalation rate (%/yr)"] = solar_var_esc
        cost_df.loc[solar_mask, "2024 Fixed Production cost ($/kW-yr)"] = solar_fixed_cost
        cost_df.loc[solar_mask, "Fixed Production escalation rate (%/yr)"] = solar_fixed_esc

if override_summary:
    st.success("### 🎯 Cost Overrides Applied\n" + "\n".join(override_summary))

# Filters for param_* columns and Bus
param_cols = [c for c in ops_df.columns if c.startswith("param_")]
# Add Bus column to filtering if it exists
additional_filter_cols = []
if 'Bus' in ops_df.columns:
    additional_filter_cols.append('Bus')

all_filter_cols = param_cols + additional_filter_cols
st.markdown("### Filters")

# Handle filter configuration loading
filter_defaults = {}
for c in all_filter_cols:
    vals = sorted(pd.unique(ops_df[c].astype(str)))
    # Default to showing ALL values (no filtering) when app first opens
    filter_defaults[f"filter_{c}"] = vals

# Load filter configuration if available
if loaded_config:
    for c in all_filter_cols:
        filter_key = f"filter_{c}"
        multiselect_key = f"filter_multiselect_{c}"
        if filter_key in loaded_config:
            # Validate that loaded values still exist in current data
            vals = sorted(pd.unique(ops_df[c].astype(str)))
            loaded_values = loaded_config[filter_key]
            # Only use values that still exist in current dataset
            valid_values = [v for v in loaded_values if v in vals]
            filter_defaults[filter_key] = valid_values if valid_values else vals
            # Update session state for the multiselect widget
            st.session_state[multiselect_key] = valid_values if valid_values else vals

with st.expander("Filter by parameters (param_*) and Bus"):
    selected = {}
    
    # Bus filter (if available)
    if 'Bus' in ops_df.columns:
        vals = sorted(pd.unique(ops_df['Bus'].astype(str)))
        filter_key = f"filter_Bus"
        multiselect_key = f"filter_multiselect_Bus"
        default_vals = filter_defaults.get(filter_key, vals)
        
        # Initialize session state if not present - DEFAULT TO ALL VALUES
        if multiselect_key not in st.session_state:
            st.session_state[multiselect_key] = vals
        
        # Validate session state values against current data
        session_vals = st.session_state[multiselect_key]
        valid_session_vals = [v for v in session_vals if v in vals]
        
        # If no valid values from session state, use all available values
        if not valid_session_vals:
            valid_session_vals = vals
            st.session_state[multiselect_key] = valid_session_vals
        
        selected['Bus'] = st.multiselect(
            'Bus', 
            options=vals, 
            default=valid_session_vals,
            key=multiselect_key
        )
    
    # Param filters
    for c in param_cols:
        vals = sorted(pd.unique(ops_df[c].astype(str)))
        filter_key = f"filter_{c}"
        multiselect_key = f"filter_multiselect_{c}"
        default_vals = filter_defaults.get(filter_key, vals)
        
        # Initialize session state if not present - DEFAULT TO ALL VALUES
        if multiselect_key not in st.session_state:
            st.session_state[multiselect_key] = vals  # Use all values as default, not filter_defaults
        
        # Validate session state values against current data
        # Only use session state values that actually exist in current dataset
        session_vals = st.session_state[multiselect_key]
        valid_session_vals = [v for v in session_vals if v in vals]
        
        # If no valid values from session state, use all available values
        if not valid_session_vals:
            valid_session_vals = vals
            # Update session state with valid values
            st.session_state[multiselect_key] = valid_session_vals
        
        # For large cardinality, default to all; allow multi-select
        selected[c] = st.multiselect(
            c, 
            options=vals, 
            default=valid_session_vals,
            key=multiselect_key
        )

# Note: current_config_to_save is already initialized earlier in the code

# Note: Configuration saving logic moved to after wind/solar override parameters are defined

# Apply filters with caching
ops_f = process_operations_data(ops_df, selected)
st.caption(f"Filtered rows: {len(ops_f):,} of {len(ops_df):,}")

# Check for single LBA + Bus filter warning
if 'Bus' in selected and selected['Bus']:
    # Check if Bus filter is active (not showing all buses)
    all_buses = sorted(pd.unique(ops_df['Bus'].astype(str)))
    bus_filter_active = len(selected['Bus']) < len(all_buses)
    
    # Check if any filtered scenarios have single_LBA = True
    if bus_filter_active and 'param_single_LBA' in ops_f.columns:
        single_lba_scenarios = ops_f[ops_f['param_single_LBA'].astype(str).str.lower().isin(['true', '1', 'yes'])]
        if not single_lba_scenarios.empty:
            filtered_buses = ', '.join(selected['Bus'])
            st.warning(f"""
            ⚠️ **Single LBA + Bus Filter Warning**
            
            You are viewing results for bus(es): **{filtered_buses}** while including scenarios where 
            `param_single_LBA = TRUE`. When the entire Railbelt grid is modeled as a single Load Balancing Area (LBA), 
            calculating financial results for only a portion of the system without properly accounting for 
            transmission flows will result in inaccurate cost estimates.
            
            **Recommendation**: When using Bus filters, only compare scenarios with `param_single_LBA = FALSE` 
            to ensure accurate regional cost analysis.
            """)

# Create fuel mapping (needed by both pages)
fuel_map = dict(zip(fuel_df["Fuel"].astype(str), fuel_df["2024 Fuel cost ($/MMBtu)"]))

# Create fuel escalation mapping by fuel type
if "Fuel escalation rate (%/yr)" in fuel_df.columns:
    fuel_esc_map = dict(zip(fuel_df["Fuel"].astype(str), fuel_df["Fuel escalation rate (%/yr)"]))
else:
    fuel_esc_map = {}

# Shared data processing for both pages
# Merge ops with generator cost inputs (by Generator; fall back on Carrier for fuel price)
gen_cost = cost_df.rename(columns={
    "Non-fuel var cost escalation rate (%/yr)":"nfu_esc",
    "Fixed Production escalation rate (%/yr)":"fpu_esc",
    "Capital cost ($/kW)":"capex_per_kw",
    "Discount rate (%)":"disc_rate_gen",
    "2024 Non-fuel var cost ($/MWh)":"nfu_2024",
    "2024 Fixed Production cost ($/kW-yr)":"fpu_2024",
})

ops_f = ops_f.merge(gen_cost, on=["Generator","Carrier"], how="left", validate="m:1")

# Map fuel escalation rates to operations data by Carrier
ops_f["fuel_esc"] = ops_f["Carrier"].astype(str).map(fuel_esc_map).fillna(0.0)

# Clean numerics
for col in ["Scenario_Capacity_MW","Total_Generation_MWh","Fuel_Consumption_MMBtu"]:
    if col in ops_f.columns:
        ops_f[col] = ops_f[col].apply(to_float).fillna(0.0)

for col in ["fuel_esc","nfu_esc","fpu_esc","nfu_2024","fpu_2024","capex_per_kw","disc_rate_gen"]:
    if col in ops_f.columns:
        ops_f[col] = ops_f[col].apply(to_float)

if "Capital cost year" in ops_f.columns:
    ops_f["Capital cost year"] = ops_f["Capital cost year"].apply(lambda x: int(to_float(x)) if not pd.isna(to_float(x)) else np.nan)
if "First year" in ops_f.columns:
    ops_f["First year"] = ops_f["First year"].apply(lambda x: int(to_float(x)) if not pd.isna(to_float(x)) else np.nan)

# Handle shared generation project cost allocation for multi-LBA scenarios
if 'param_single_LBA' in ops_f.columns:
    # Identify multi-LBA scenarios
    multi_lba_scenarios = ops_f[ops_f['param_single_LBA'].astype(str).str.lower().isin(['false', '0', 'no'])]
    
    if not multi_lba_scenarios.empty:
        # Find generators with the pattern "_locationBus_ownerBus" suffix
        split_projects = {}  # Will store {base_project_name: [list_of_split_generators]}
        
        for idx, row in multi_lba_scenarios.iterrows():
            generator_name = str(row['Generator'])
            
            # Check if generator name has the pattern "_locationBus_ownerBus"
            parts = generator_name.split('_')
            if len(parts) >= 3:
                # Look for pattern where last two parts could be bus names
                potential_base_name = '_'.join(parts[:-2])
                location_bus = parts[-2]
                owner_bus = parts[-1]
                
                # Check if this base project exists in the cost data
                base_project_in_costs = cost_df[cost_df['Generator'] == potential_base_name]
                if not base_project_in_costs.empty:
                    # This is a split project
                    if potential_base_name not in split_projects:
                        split_projects[potential_base_name] = []
                    split_projects[potential_base_name].append({
                        'generator': generator_name,
                        'location_bus': location_bus,
                        'owner_bus': owner_bus,
                        'capacity_mw': row['Scenario_Capacity_MW'],
                        'index': idx
                    })
        
        # Process each split project group
        for base_project, split_gens in split_projects.items():
            if len(split_gens) > 1:  # Only process if actually split
                # Get base project costs
                base_costs = cost_df[cost_df['Generator'] == base_project].iloc[0]
                
                # Apply same rates to all split components (no scaling needed since costs are per-unit rates)
                for split_gen in split_gens:
                    idx = split_gen['index']
                    
                    # Per-kW costs (use same rate)
                    per_kw_costs = ['capex_per_kw', 'fpu_2024']  # Capital cost and fixed production cost
                    for cost_col in per_kw_costs:
                        if cost_col in ops_f.columns:
                            cost_source_col = cost_col.replace('capex_per_kw', 'Capital cost ($/kW)').replace('fpu_2024', '2024 Fixed Production cost ($/kW-yr)')
                            base_cost = base_costs.get(cost_source_col)
                            if not pd.isna(base_cost):
                                ops_f.at[idx, cost_col] = float(base_cost)
                    
                    # Per-MWh costs (use same rate)
                    if 'nfu_2024' in ops_f.columns:
                        base_cost = base_costs.get('2024 Non-fuel var cost ($/MWh)')
                        if not pd.isna(base_cost):
                            ops_f.at[idx, 'nfu_2024'] = float(base_cost)
                    
                    # Percentage-based costs (use same rate)
                    percentage_costs = ['nfu_esc', 'fpu_esc', 'disc_rate_gen']
                    cost_map = {
                        'nfu_esc': 'Non-fuel var cost escalation rate (%/yr)',
                        'fpu_esc': 'Fixed Production escalation rate (%/yr)', 
                        'disc_rate_gen': 'Discount rate (%)'
                    }
                    for cost_col in percentage_costs:
                        if cost_col in ops_f.columns:
                            base_cost_col = cost_map[cost_col]
                            base_cost = base_costs.get(base_cost_col)
                            if not pd.isna(base_cost):
                                # Convert percentage string to float if needed
                                if isinstance(base_cost, str) and '%' in str(base_cost):
                                    base_cost = to_float(base_cost)
                                ops_f.at[idx, cost_col] = float(base_cost)
                    
                    # Time-based parameters (use same values)
                    time_params = ['Capital cost year', 'First year'] 
                    for param in time_params:
                        if param in ops_f.columns:
                            base_value = base_costs.get(param)
                            if not pd.isna(base_value):
                                ops_f.at[idx, param] = int(to_float(base_value)) if not pd.isna(to_float(base_value)) else np.nan
                
        # Show summary of split projects found
        if split_projects:
            # Collect unique split generator names for each base project across all scenarios
            unique_projects = {}
            for base_project, split_gens in split_projects.items():
                if base_project not in unique_projects:
                    unique_projects[base_project] = set()
                # Add all split generator names for this base project
                for gen in split_gens:
                    unique_projects[base_project].add(gen['generator'])
            
            project_list = []
            for base_project, split_names_set in unique_projects.items():
                split_names = sorted(list(split_names_set))  # Convert set to sorted list
                project_list.append(f"• **{base_project}** → {', '.join(split_names)}")
            
            # Create the complete message for the info box
            message = f"📊 **Shared Project Cost Allocation Applied**\n\n"
            message += f"Found {len(unique_projects)} unique shared projects:\n\n"
            message += "\n".join(project_list)
            
            st.info(message)

# Complete configuration saving logic (after all parameters are defined)
if current_config_to_save is not None:
    # Add filter parameters to the configuration
    for c in all_filter_cols:
        filter_key = f"filter_{c}"
        current_config_to_save[filter_key] = selected[c]
    
    # Add wind override parameters
    current_config_to_save['wind_override_enabled'] = use_wind_override
    if use_wind_override:
        current_config_to_save['wind_capex'] = wind_capex
        current_config_to_save['wind_capex_year'] = wind_capex_year
        current_config_to_save['wind_first_year'] = wind_first_year
        current_config_to_save['wind_discount'] = wind_discount_rate * 100.0  # Store as percentage
        current_config_to_save['wind_var_cost'] = wind_var_cost
        current_config_to_save['wind_var_esc'] = wind_var_esc * 100.0  # Store as percentage
        current_config_to_save['wind_fixed_cost'] = wind_fixed_cost
        current_config_to_save['wind_fixed_esc'] = wind_fixed_esc * 100.0  # Store as percentage
    
    # Add solar override parameters
    current_config_to_save['solar_override_enabled'] = use_solar_override
    if use_solar_override:
        current_config_to_save['solar_capex'] = solar_capex
        current_config_to_save['solar_capex_year'] = solar_capex_year
        current_config_to_save['solar_first_year'] = solar_first_year
        current_config_to_save['solar_discount'] = solar_discount_rate * 100.0  # Store as percentage
        current_config_to_save['solar_var_cost'] = solar_var_cost
        current_config_to_save['solar_var_esc'] = solar_var_esc * 100.0  # Store as percentage
        current_config_to_save['solar_fixed_cost'] = solar_fixed_cost
        current_config_to_save['solar_fixed_esc'] = solar_fixed_esc * 100.0  # Store as percentage
    
    # Save the complete configuration
    config_name = st.session_state.pending_save
    del st.session_state.pending_save
    save_current_config(config_name, current_config_to_save, cost_df=cost_df, fuel_df=fuel_df)
    st.sidebar.success(f"✅ Configuration saved: {config_name}")

st.title("📊 LCOE Dashboard")

if page == "📊 Main Results":
    # -----------------------------
    # Cost Data Validation
    # -----------------------------
    # Check for missing cost data after merge
    cost_columns = ["capex_per_kw", "disc_rate_gen", "nfu_2024", "fpu_2024", "nfu_esc", "fpu_esc"]
    
    missing_cost_data = []
    for col in cost_columns:
        if col in ops_f.columns:
            missing_rows = ops_f[ops_f[col].isna()]
            if not missing_rows.empty:
                missing_generators = missing_rows[["Scenario", "Generator", "Carrier"]].drop_duplicates()
                missing_cost_data.append({
                    'cost_type': col,
                    'missing_data': missing_generators
                })
    
    # Check for missing fuel escalation rates
    missing_fuel_esc = ops_f[ops_f["fuel_esc"].isna()]
    if not missing_fuel_esc.empty:
        missing_fuels = missing_fuel_esc[["Scenario", "Carrier"]].drop_duplicates()
        missing_cost_data.append({
            'cost_type': 'fuel_esc',
            'missing_data': missing_fuels
        })
    
    # Check for missing 2024 fuel costs ($/MMBtu)
    # Get unique carriers from operations data that have fuel consumption > 0
    fuel_consuming_carriers = ops_f[ops_f["Fuel_Consumption_MMBtu"] > 0]["Carrier"].unique()
    missing_fuel_costs = []
    for carrier in fuel_consuming_carriers:
        if carrier not in fuel_map or pd.isna(fuel_map.get(carrier)):
            # Find scenarios that use this fuel
            scenarios_using_fuel = ops_f[
                (ops_f["Carrier"] == carrier) & 
                (ops_f["Fuel_Consumption_MMBtu"] > 0)
            ]["Scenario"].unique()
            for scenario in scenarios_using_fuel:
                missing_fuel_costs.append({
                    "Scenario": scenario,
                    "Carrier": carrier
                })
    
    if missing_fuel_costs:
        missing_fuel_cost_df = pd.DataFrame(missing_fuel_costs).drop_duplicates()
        missing_cost_data.append({
            'cost_type': '2024_fuel_cost',
            'missing_data': missing_fuel_cost_df
        })
    
    if missing_cost_data:
        st.error("🚨 **Missing Cost Data Detected**")
        st.markdown("Some generators or fuels are missing cost inputs, which will result in incorrect LCOE calculations.")
        
        with st.expander("📋 View Missing Cost Details"):
            for missing in missing_cost_data:
                cost_type = missing['cost_type']
                missing_df = missing['missing_data']
                
                if cost_type == 'fuel_esc':
                    st.markdown(f"**Missing Fuel Escalation Rates:**")
                    st.markdown("The following fuels are missing escalation rates in the fuel cost file:")
                elif cost_type == '2024_fuel_cost':
                    st.markdown(f"**Missing 2024 Fuel Costs ($/MMBtu):**")
                    st.markdown("The following fuels are missing 2024 fuel cost data in the fuel cost file:")
                else:
                    cost_name = {
                        'capex_per_kw': 'Capital Cost',
                        'disc_rate_gen': 'Discount Rate', 
                        'nfu_2024': '2024 Non-Fuel Variable Cost',
                        'fpu_2024': '2024 Fixed Production Cost',
                        'nfu_esc': 'Non-Fuel Variable Cost Escalation',
                        'fpu_esc': 'Fixed Production Cost Escalation'
                    }.get(cost_type, cost_type)
                    
                    st.markdown(f"**Missing {cost_name}:**")
                    st.markdown("The following generators are missing cost data in the generator cost file:")
                
                st.dataframe(missing_df, use_container_width=True)
                st.markdown("---")
        
        st.info("💡 **Solution:** Update your generator cost and/or fuel cost input files to include data for all generators and fuels present in your scenarios.")
    
    # -----------------------------
    # System Load Validation
    # -----------------------------
    # Calculate total generation (system load) for each scenario
    # Exclude battery generation as it doesn't account for charging losses
    ops_f_no_battery = ops_f[ops_f["Carrier"].str.lower() != "battery"]
    scenario_loads = ops_f_no_battery.groupby("Scenario")["Total_Generation_MWh"].sum().round(1)
    unique_loads = scenario_loads.unique()
    
    # Check if all scenarios have the same system load
    if len(unique_loads) > 1:
        st.warning("⚠️ **Different System Loads Detected**")
        st.markdown("The displayed scenarios have different total system loads, which may make LCOE comparisons misleading.")
        
        # Create expandable details about load differences
        with st.expander("📊 View System Load Details"):
            load_df = scenario_loads.reset_index()
            load_df.columns = ["Scenario", "Total System Load (MWh)"]
            load_df = load_df.sort_values("Total System Load (MWh)", ascending=False)
            
            st.dataframe(load_df, use_container_width=True)
            
            min_load = scenario_loads.min()
            max_load = scenario_loads.max()
            load_variation = ((max_load - min_load) / min_load * 100)
            
            st.markdown(f"""
            **Load Statistics:**
            - Minimum Load: {min_load:,.0f} MWh
            - Maximum Load: {max_load:,.0f} MWh  
            - Variation: {load_variation:.1f}%
            """)
        
        # Find relevant parameter columns for filtering suggestions
        param_cols_for_suggestion = [c for c in ops_df.columns if c.startswith("param_") and 
                                   any(keyword in c.lower() for keyword in ['datacenter', 'load', 'growth', 'demand'])]
        
        if param_cols_for_suggestion:
            param_names = ", ".join([c.replace("param_", "") for c in param_cols_for_suggestion])
            st.info(f"💡 **Suggestion:** Filter by parameters like {param_names} to compare scenarios with similar system loads.")
        else:
            st.info("💡 **Suggestion:** Use the parameter filters to select scenarios with similar system loads for more meaningful LCOE comparisons.")
    else:
        # All scenarios have the same load - show confirmation
        total_load = unique_loads[0]
        st.success(f"✅ All {len(scenario_loads)} scenarios have the same system load: {total_load:,.0f} MWh")
    
    # -----------------------------
    # Compute system LCOE per scenario
    # -----------------------------
    # Determine which discount to use
    df_disc_rate = global_discount_rate if use_global_discount else None

    scenario_results = []
    years = list(range(int(start_year), int(end_year)+1))

    # Show progress for large datasets
    scenarios = list(ops_f.groupby("Scenario", sort=False))
    if len(scenarios) > 10:
        progress_bar = st.progress(0)
        status_text = st.empty()

    for i, (scen, sdf) in enumerate(scenarios):
        if len(scenarios) > 10:
            progress = (i + 1) / len(scenarios)
            progress_bar.progress(progress)
            status_text.text(f"Processing scenario {i+1}/{len(scenarios)}: {scen}")
        
        # Per generator static values (repeat ops each year)
        # Base values:
        gen_MWh = sdf["Total_Generation_MWh"].fillna(0.0).values
        fuel_MMBtu = sdf["Fuel_Consumption_MMBtu"].fillna(0.0).values
        cap_MW = sdf["Scenario_Capacity_MW"].fillna(0.0).values
        carriers = sdf["Carrier"].astype(str).values
        # Create mask for non-battery generators (batteries excluded from LCOE denominator)
        is_not_battery = np.array([c.lower() != "battery" for c in carriers], dtype=bool)

        # Cost parameters (per generator)
        fuel_esc = sdf["fuel_esc"].fillna(0.0).values
        nfu_esc = sdf["nfu_esc"].fillna(0.0).values
        fpu_esc = sdf["fpu_esc"].fillna(0.0).values
        nfu_2024 = sdf["nfu_2024"].fillna(0.0).values
        fpu_2024 = sdf["fpu_2024"].fillna(0.0).values
        capex_kw = sdf["capex_per_kw"].fillna(0.0).values
        cap_cost_year = sdf["Capital cost year"].fillna(np.nan).values if "Capital cost year" in sdf.columns else np.full(len(sdf), np.nan)
        first_year = sdf["First year"].fillna(np.nan).values if "First year" in sdf.columns else np.full(len(sdf), np.nan)
        gen_disc_rate = sdf["disc_rate_gen"].fillna(global_discount_rate if use_global_discount else 0.05).values
        # Fuel base prices (2024)
        base_fuel_price = np.array([fuel_map.get(f, np.nan) for f in carriers], dtype=float)

        # Aggregate across years
        pv_cost_sum = 0.0
        pv_gen_sum = 0.0

        # CAPEX handling (once per generator)
        # If upfront: include PV of capex in the first in-horizon year max(start_year, first_year)
        # If annualized: compute annual payment via CRF and include each year in horizon starting max(start_year, first_year)
        for j in range(len(sdf)):
            kw = cap_MW[j] * 1000.0
            capex_total = kw * capex_kw[j]
            if capex_total > 0:
                start_incl_year = int(max(start_year, first_year[j] if not math.isnan(first_year[j]) else start_year))
                if start_incl_year > end_year:
                    pass  # outside horizon; ignore
                else:
                    y0_offset = start_incl_year - start_year
                    r_for_capex = (global_discount_rate if use_global_discount else gen_disc_rate[j])
                    if capex_treatment.startswith("Upfront"):
                        df_y0 = discount_factor(r_for_capex, y0_offset)
                        pv_cost_sum += capex_total * df_y0
                    else:
                        crf = capital_recovery_factor(r_for_capex, asset_life_years)
                        annual_payment = capex_total * crf
                        for yr in years:
                            if yr >= start_incl_year and yr < start_incl_year + asset_life_years:
                                t = yr - start_year
                                pv_cost_sum += annual_payment * discount_factor(r_for_capex, t)

        # Yearly O&M + Fuel + (repeat ops & costs each year)
        for t, yr in enumerate(years):
            # Choose discount rate for PV of costs and gen (system-level: use global or per-generator)
            # We'll use global if selected; else generator-specific for both costs and generation
            for j in range(len(sdf)):
                r_j = (global_discount_rate if use_global_discount else gen_disc_rate[j])

                # Fuel price escalation anchored to 2024
                years_from_2024 = yr - 2024
                fuel_price_y = escalate(base_fuel_price[j], fuel_esc[j], years_from_2024)

                # Non-fuel variable and Fixed production escalation anchored to 2024
                nfu_cost_y = escalate(nfu_2024[j], nfu_esc[j], years_from_2024)  # $/MWh
                fpu_cost_y = escalate(fpu_2024[j], fpu_esc[j], years_from_2024)  # $/kW-yr

                # Costs for that generator that year
                cost_fuel = (fuel_MMBtu[j] if repeat_ops_each_year else 0.0) * (fuel_price_y if not pd.isna(fuel_price_y) else 0.0)
                cost_nfu  = (gen_MWh[j] if repeat_ops_each_year else 0.0) * (nfu_cost_y if not pd.isna(nfu_cost_y) else 0.0)
                cost_fpu  = (cap_MW[j] * 1000.0) * (fpu_cost_y if not pd.isna(fpu_cost_y) else 0.0)

                df_t = discount_factor(r_j, t)
                pv_cost_sum += (cost_fuel + cost_nfu + cost_fpu) * df_t

                # Discounted generation (exclude battery generation from denominator)
                gen_y = (gen_MWh[j] if repeat_ops_each_year else 0.0)
                if is_not_battery[j]:
                    pv_gen_sum += gen_y * df_t

        lcoe = np.nan if pv_gen_sum == 0 else pv_cost_sum / pv_gen_sum

        # Carrier summaries (for plotting panels 2-4) using the single-year base data
        base_df = sdf.copy()
        # In case of odd CF%, compute from base data
        base_df["CF_calc"] = (base_df["Total_Generation_MWh"] / (base_df["Scenario_Capacity_MW"] * hours_per_year)).replace([np.inf, -np.inf], np.nan)
        base_df["CF_use"] = np.where(base_df["CF_calc"].notna(), base_df["CF_calc"], base_df.get("Capacity_Factor_pct", 0)/100.0)
        base_df["CF_use"] = pd.Series(base_df["CF_use"]).clip(lower=0)

        cap_by_carrier = base_df.groupby("Carrier", dropna=False)["Scenario_Capacity_MW"].sum().to_dict()
        cf_by_carrier  = base_df.groupby("Carrier", dropna=False).apply(generation_weighted_cf).to_dict()
        curt_by_carrier = base_df.groupby("Carrier", dropna=False)["Curtailed_Energy_MWh"].sum().to_dict()
        gen_by_carrier = base_df.groupby("Carrier", dropna=False)["Total_Generation_MWh"].sum().to_dict()
        
        # Get parameter/filter values for this scenario (from first row since they're the same for all rows in a scenario)
        param_values = {}
        if not sdf.empty:
            first_row = sdf.iloc[0]
            for col in sdf.columns:
                if col.startswith('param_') or col == 'Bus':
                    param_values[col] = first_row[col]

        scenario_results.append({
            "Scenario": scen,
            "LCOE_$perMWh": lcoe,
            "cap_by_carrier": cap_by_carrier,
            "cf_by_carrier": cf_by_carrier,
            "curt_by_carrier": curt_by_carrier,
            "gen_by_carrier": gen_by_carrier,
            "params": param_values
        })

    # Clean up progress indicators
    if len(scenarios) > 10:
        progress_bar.empty()
        status_text.empty()

    res_df = pd.DataFrame(scenario_results)
    if res_df.empty:
        st.warning("No results after filtering.")
    else:
        # Order simulations by LCOE
        res_df = res_df.sort_values("LCOE_$perMWh", ascending=True).reset_index(drop=True)

        # Build carrier lists across all scenarios for stack consistency
        all_carriers = sorted(set().union(*[set(d.keys()) for d in res_df["cap_by_carrier"]]))
        if not all_carriers:
            all_carriers = ["unknown"]

        # @st.cache_data  # Disabled due to dictionary columns causing hashing issues
        def expand_dict_column(df, colname, value_suffix):
            """Expand dictionary column into wide format with caching."""
            # Get all unique carriers across all dictionaries
            all_keys = sorted(set().union(*[set(d.keys()) for d in df[colname]]))
            if not all_keys:
                all_keys = ["unknown"]
            
            rows = []
            for i, row in df.iterrows():
                base = {"Scenario": row["Scenario"]}
                d = row[colname]
                for k in all_keys:
                    base[f"{k}{value_suffix}"] = float(d.get(k, 0.0))
                rows.append(base)
            return pd.DataFrame(rows), all_keys

        cap_tbl, all_carriers_cap = expand_dict_column(res_df, "cap_by_carrier", "_MW")
        cf_tbl, all_carriers_cf = expand_dict_column(res_df, "cf_by_carrier", "_CF") 
        curt_tbl, all_carriers_curt = expand_dict_column(res_df, "curt_by_carrier", "_MWh")
        gen_tbl, all_carriers_gen = expand_dict_column(res_df, "gen_by_carrier", "_GWh")

        # Convert generation from MWh to GWh for better readability
        for col in gen_tbl.columns:
            if col.endswith('_GWh') and col != 'Scenario':
                gen_tbl[col] = gen_tbl[col] / 1000.0

        # Use the union of all carriers for consistency
        all_carriers = sorted(set(all_carriers_cap + all_carriers_cf + all_carriers_curt + all_carriers_gen))

        plot_df = res_df[["Scenario","LCOE_$perMWh"]].merge(cap_tbl, on="Scenario").merge(cf_tbl, on="Scenario").merge(curt_tbl, on="Scenario").merge(gen_tbl, on="Scenario")
        
        # Calculate curtailment percentage for each carrier
        # Curtailment % = curtailed energy / (generation + curtailed energy) * 100
        curt_pct_data = {"Scenario": plot_df["Scenario"].values}
        for carrier in all_carriers:
            gen_mwh = plot_df[f"{carrier}_GWh"] * 1000  # Convert GWh back to MWh
            curt_mwh = plot_df[f"{carrier}_MWh"]
            total_potential = gen_mwh + curt_mwh
            curt_pct_data[f"{carrier}_Pct"] = np.where(total_potential > 0, (curt_mwh / total_potential) * 100, 0)
        
        curt_pct_tbl = pd.DataFrame(curt_pct_data)
        plot_df = plot_df.merge(curt_pct_tbl, on="Scenario")
        
        scenarios_ordered = plot_df["Scenario"].tolist()

        # Create numeric x-axis (scenario index)
        x_vals = list(range(len(scenarios_ordered)))

        # -----------------------------
        # Plotting (5 panels in one figure)
        # -----------------------------
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=(
                "Simulation LCOE ($/MWh)",
                "Total Installed Capacity by Carrier (MW)",
                "Total Generation by Carrier (GWh)",
                "Average Capacity Factor by Carrier (%)",
                "Total Curtailment by Carrier (%)",
                ""  # Empty sixth subplot
            )
        )

        # 1) LCOE line
        fig.add_trace(
            go.Scatter(x=x_vals, y=plot_df["LCOE_$perMWh"], mode="lines+markers", name="LCOE", line=dict(width=3), legendgroup="LCOE",
                      customdata=scenarios_ordered,
                      hovertemplate="<b>%{customdata}</b><br>LCOE: $%{y:.2f}/MWh<extra></extra>"),
            row=1, col=1
        )

        # Define which carriers should be visible by default
        default_visible_carriers = {"geo", "wind", "solar", "gas"}

        # Create a color mapping for consistent colors across all plots
        import plotly.colors as pc
        colors = pc.qualitative.Plotly + pc.qualitative.Dark24 + pc.qualitative.Light24
        color_map = {carrier: colors[i % len(colors)] for i, carrier in enumerate(all_carriers)}

        # 2) Capacity lines
        for k in all_carriers:
            visibility = True if k.lower() in default_visible_carriers else 'legendonly'
            fig.add_trace(
                go.Scatter(x=x_vals, y=plot_df[f"{k}_MW"], mode="lines+markers", name=f"{k}", 
                          showlegend=True, legendgroup=k, visible=visibility, 
                          line=dict(color=color_map[k]), marker=dict(color=color_map[k]),
                          customdata=scenarios_ordered,
                          hovertemplate="<b>%{customdata}</b><br>" + f"{k}: " + "%{y:.1f} MW<extra></extra>"),
                row=1, col=2
            )

        # 3) Generation lines
        for k in all_carriers:
            visibility = True if k.lower() in default_visible_carriers else 'legendonly'
            fig.add_trace(
                go.Scatter(x=x_vals, y=plot_df[f"{k}_GWh"], mode="lines+markers", name=f"{k} Gen (GWh)", 
                          showlegend=False, legendgroup=k, visible=visibility,
                          line=dict(color=color_map[k]), marker=dict(color=color_map[k]),
                          customdata=scenarios_ordered,
                          hovertemplate="<b>%{customdata}</b><br>" + f"{k} Gen: " + "%{y:.1f} GWh<extra></extra>"),
                row=2, col=1
            )

        # 4) CF lines (use percentage)
        for k in all_carriers:
            visibility = True if k.lower() in default_visible_carriers else 'legendonly'
            fig.add_trace(
                go.Scatter(x=x_vals, y=(100.0*plot_df[f"{k}_CF"]), mode="lines+markers", name=f"{k} CF (%)", 
                          showlegend=False, legendgroup=k, visible=visibility,
                          line=dict(color=color_map[k]), marker=dict(color=color_map[k]),
                          customdata=scenarios_ordered,
                          hovertemplate="<b>%{customdata}</b><br>" + f"{k} CF: " + "%{y:.1f}%<extra></extra>"),
                row=2, col=2
            )

        # 5) Curtailment lines (convert to percentage)
        # Calculate curtailment percentage = curtailed energy / (generation + curtailed energy) * 100
        for k in all_carriers:
            visibility = True if k.lower() in default_visible_carriers else 'legendonly'
            # Calculate curtailment percentage 
            total_potential = plot_df[f"{k}_GWh"] * 1000 + plot_df[f"{k}_MWh"]  # Convert GWh back to MWh and add curtailed
            curtailment_pct = np.where(total_potential > 0, (plot_df[f"{k}_MWh"] / total_potential) * 100, 0)
            
            fig.add_trace(
                go.Scatter(x=x_vals, y=curtailment_pct, mode="lines+markers", name=f"{k} curtailment %", 
                          showlegend=False, legendgroup=k, visible=visibility,
                          line=dict(color=color_map[k]), marker=dict(color=color_map[k]),
                          customdata=scenarios_ordered,
                          hovertemplate="<b>%{customdata}</b><br>" + f"{k} Curtailment: " + "%{y:.1f}%<extra></extra>"),
                row=3, col=1
            )

        fig.update_layout(height=800, legend_tracegroupgap=6, hovermode="x unified", margin=dict(l=40,r=20,t=60,b=80))
        fig.update_xaxes(title_text="Scenario Rank (by LCOE)", matches='x')

        st.markdown("### Scenario Results (ordered by LCOE)")
        st.plotly_chart(fig, use_container_width=True)

        # -----------------------------
        # Triangle Plot - Technology Mix Analysis
        # -----------------------------
        st.markdown("### Technology Mix Analysis")
        st.markdown("**Triangle plot showing the capacity relationship between geothermal, gas, and variable renewable (wind+solar) technologies across scenarios**")
        
        # Prepare data for triangle plot
        triangle_data = []
        
        # First pass: collect all capacity data to find minimums
        all_scenario_data = []
        for idx, row in plot_df.iterrows():
            scenario = row["Scenario"]
            lcoe = row["LCOE_$perMWh"]
            
            # Calculate capacity by technology group
            geothermal_cap = 0
            gas_cap = 0
            renewables_cap = 0
            
            for carrier in all_carriers:
                cap_col = f"{carrier}_MW"
                if cap_col in row:
                    capacity = row[cap_col]
                    carrier_lower = carrier.lower()
                    
                    # More comprehensive geothermal detection
                    if any(geo_term in carrier_lower for geo_term in ["geothermal", "geo", "thermal"]):
                        geothermal_cap += capacity
                    # More comprehensive gas detection
                    elif any(fuel in carrier_lower for fuel in ["gas", "natural_gas", "lng", "diesel", "oil", "petroleum", "fossil"]):
                        gas_cap += capacity
                    # More comprehensive renewables detection  
                    elif any(tech in carrier_lower for tech in ["wind", "solar", "pv", "photovoltaic"]):
                        renewables_cap += capacity
            
            all_scenario_data.append({
                'Scenario': scenario,
                'LCOE': lcoe,
                'Geothermal_MW': geothermal_cap,
                'Gas_MW': gas_cap,
                'Renewables_MW': renewables_cap
            })
        
        if all_scenario_data:
            # Calculate minimum capacity for each technology across all scenarios
            temp_df = pd.DataFrame(all_scenario_data)
            min_geothermal = temp_df['Geothermal_MW'].min()
            min_gas = temp_df['Gas_MW'].min()
            min_renewables = temp_df['Renewables_MW'].min()
            
            # Second pass: calculate new capacity above minimum
            for scenario_data in all_scenario_data:
                # Calculate new capacity (above minimum)
                new_geothermal = scenario_data['Geothermal_MW'] - min_geothermal
                new_gas = scenario_data['Gas_MW'] - min_gas
                new_renewables = scenario_data['Renewables_MW'] - min_renewables
                
                total_new_cap = new_geothermal + new_gas + new_renewables
                total_cap = scenario_data['Geothermal_MW'] + scenario_data['Gas_MW'] + scenario_data['Renewables_MW']
                
                if total_new_cap > 0:  # Only include scenarios with new capacity above minimum
                    triangle_data.append({
                        'Scenario': scenario_data['Scenario'],
                        'LCOE': scenario_data['LCOE'],
                        'Geothermal_MW': scenario_data['Geothermal_MW'],
                        'Gas_MW': scenario_data['Gas_MW'],
                        'Renewables_MW': scenario_data['Renewables_MW'],
                        'New_Geothermal_MW': new_geothermal,
                        'New_Gas_MW': new_gas,
                        'New_Renewables_MW': new_renewables,
                        'Total_MW': total_cap,
                        'Total_New_MW': total_new_cap
                    })
        
        if triangle_data:
            tri_df = pd.DataFrame(triangle_data)
            
            # For ternary plots, we need to normalize to fractions that sum to 1
            # Convert new capacity MW to fractions of each scenario's total new capacity
            tri_df['New_Geothermal_frac'] = tri_df['New_Geothermal_MW'] / tri_df['Total_New_MW']
            tri_df['New_Gas_frac'] = tri_df['New_Gas_MW'] / tri_df['Total_New_MW']
            tri_df['New_Renewables_frac'] = tri_df['New_Renewables_MW'] / tri_df['Total_New_MW']
            
            # Create ternary plot
            fig_tri = go.Figure()
            
            # Calculate marker sizes based on total new capacity
            # Scale marker sizes to a wider range (5-35 pixels) for better differentiation
            min_new_cap = tri_df['Total_New_MW'].min()
            max_new_cap = tri_df['Total_New_MW'].max()
            
            # Avoid division by zero
            if max_new_cap > min_new_cap:
                # Scale from 5 to 35 pixels based on new capacity (wider range for better distinction)
                marker_sizes = 5 + (tri_df['Total_New_MW'] - min_new_cap) / (max_new_cap - min_new_cap) * 30
            else:
                marker_sizes = [20] * len(tri_df)  # Default size if all equal
            
            # Add scatter trace
            fig_tri.add_trace(go.Scatterternary(
                a=tri_df['New_Geothermal_frac'],
                b=tri_df['New_Gas_frac'], 
                c=tri_df['New_Renewables_frac'],
                mode='markers',
                marker=dict(
                    size=marker_sizes,
                    color=tri_df['LCOE'],
                    colorscale='RdYlBu_r',  # Red (high LCOE) to Blue (low LCOE)
                    colorbar=dict(title="LCOE ($/MWh)"),
                    line=dict(width=1.5, color='white'),  # Thicker white border for better edge visibility
                    sizemode='diameter',
                    opacity=0.7  # Reduced opacity for better overlapping visibility
                ),
                text=[f"Scenario: {row['Scenario']}<br>"
                      f"LCOE: ${row['LCOE']:.1f}/MWh<br>"
                      f"Total Capacity: {row['Total_MW']:.0f} MW<br>"
                      f"Total New Capacity: {row['Total_New_MW']:.0f} MW<br>"
                      f"Geothermal: {row['Geothermal_MW']:.0f} MW (New: {row['New_Geothermal_MW']:.0f} MW, {row['New_Geothermal_frac']*100:.1f}%)<br>"
                      f"Gas: {row['Gas_MW']:.0f} MW (New: {row['New_Gas_MW']:.0f} MW, {row['New_Gas_frac']*100:.1f}%)<br>"
                      f"Renewables: {row['Renewables_MW']:.0f} MW (New: {row['New_Renewables_MW']:.0f} MW, {row['New_Renewables_frac']*100:.1f}%)"
                      for _, row in tri_df.iterrows()],
                hovertemplate='%{text}<extra></extra>',
                name='Scenarios'
            ))
            
            fig_tri.update_layout(
                ternary=dict(
                    sum=1,  # Fractions sum to 1
                    aaxis=dict(
                        title='New Geothermal Fraction', 
                        min=0,  # Must be 0 or positive for ternary plots
                        linewidth=1,  # Same thickness as grid lines
                        ticks="outside",
                        tickfont=dict(size=10),
                        gridcolor='rgba(255,255,255,0.3)',  # White grid lines for dark background
                        gridwidth=1,  # Explicit grid line width
                        showgrid=True,
                        showline=True,  # Show axis lines again
                        tick0=0,  # Start ticks at 0
                        dtick=0.2  # Tick every 0.2 (20%)
                    ),
                    baxis=dict(
                        title='New Gas Fraction', 
                        min=0,  # Must be 0 or positive for ternary plots
                        linewidth=1,  # Same thickness as grid lines
                        ticks="outside",
                        tickfont=dict(size=10),
                        gridcolor='rgba(255,255,255,0.3)',  # White grid lines for dark background
                        gridwidth=1,  # Explicit grid line width
                        showgrid=True,
                        showline=True,  # Show axis lines again
                        tick0=0,  # Start ticks at 0
                        dtick=0.2  # Tick every 0.2 (20%)
                    ),
                    caxis=dict(
                        title='New Wind+Solar Fraction', 
                        min=0,  # Must be 0 or positive for ternary plots
                        linewidth=1,  # Same thickness as grid lines
                        ticks="outside",
                        tickfont=dict(size=10),
                        gridcolor='rgba(255,255,255,0.3)',  # White grid lines for dark background
                        gridwidth=1,  # Explicit grid line width
                        showgrid=True,
                        showline=True,  # Show axis lines again
                        tick0=0,  # Start ticks at 0
                        dtick=0.2  # Tick every 0.2 (20%)
                    )
                ),
                font=dict(size=12),
                height=600
            )
            
            # Create side-by-side layout for ternary plot and marker legend
            col_plot, col_legend = st.columns([3, 1], gap="small")
            
            with col_plot:
                st.plotly_chart(fig_tri, use_container_width=True)
            
            with col_legend:
                
                # Create a simple plot showing marker size examples
                import numpy as np
                
                # Generate size examples (small, medium, large)
                legend_capacities = [min_new_cap, (min_new_cap + max_new_cap) / 2, max_new_cap]
                if max_new_cap > min_new_cap:
                    legend_sizes = [5 + (cap - min_new_cap) / (max_new_cap - min_new_cap) * 30 for cap in legend_capacities]
                else:
                    legend_sizes = [20, 20, 20]
                
                # Create legend plot
                fig_legend = go.Figure()
                
                # Add markers at different y positions
                y_positions = [3, 2, 1]
                for i, (cap, size) in enumerate(zip(legend_capacities, legend_sizes)):
                    fig_legend.add_trace(go.Scatter(
                        x=[0.5], y=[y_positions[i]], 
                        mode='markers',
                        marker=dict(
                            size=size,
                            color='steelblue',
                            opacity=0.7,
                            line=dict(width=1.5, color='white')
                        ),
                        name=f'{cap:.0f} MW',
                        showlegend=False,
                        hoverinfo='none'
                    ))
                    
                    # Add capacity label
                    fig_legend.add_annotation(
                        x=0.7, y=y_positions[i],
                        text=f'{cap:.0f} MW new capacity',
                        showarrow=False,
                        xanchor='left',
                        font=dict(size=12)
                    )
                
                fig_legend.update_layout(
                    xaxis=dict(showgrid=False, showticklabels=False, range=[0, 1]),
                    yaxis=dict(showgrid=False, showticklabels=False, range=[0.5, 3.5]),
                    height=600,  # Match the ternary plot height
                    margin=dict(l=20, r=20, t=40, b=20),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)'
                )
                
                st.plotly_chart(fig_legend, use_container_width=True)
            
            # Add explanation of the plot dimensions
            st.info(f"""
            **📊 Plot Interpretation Guide:**
            - **Position**: Technology mix fractions (where in triangle = what % of each technology type)
            - **Color**: LCOE (blue = lower cost, red = higher cost)
            - **Size**: Total new capacity above baseline (larger markers = more total expansion)
            - **Range**: New capacity ranges from {min_new_cap:.0f} MW to {max_new_cap:.0f} MW across scenarios
            """)
        else:
            st.warning("No capacity data available for triangle plot.")

        # -----------------------------
        # Downloadable results
        # -----------------------------
        with st.container():
            st.markdown("### Download data")
            @st.cache_data
            def build_export_table(plot_df, res_df):
                # Create combined table with all data merged together
                combined = plot_df[["Scenario", "LCOE_$perMWh"]].copy()
                
                # Add carrier metrics with descriptive column names
                for carrier in all_carriers:
                    combined[f"{carrier}_Capacity_MW"] = plot_df[f"{carrier}_MW"]
                    combined[f"{carrier}_Generation_GWh"] = plot_df[f"{carrier}_GWh"]
                    combined[f"{carrier}_CF"] = plot_df[f"{carrier}_CF"]
                    combined[f"{carrier}_Curtailment_MWh"] = plot_df[f"{carrier}_MWh"]
                    combined[f"{carrier}_Curtailment_Pct"] = plot_df[f"{carrier}_Pct"]
                
                # Add parameter/filter columns for each scenario
                # Extract params from res_df and merge into combined
                param_data = []
                for _, row in res_df.iterrows():
                    scenario = row["Scenario"]
                    params = row.get("params", {})
                    param_row = {"Scenario": scenario}
                    param_row.update(params)
                    param_data.append(param_row)
                
                if param_data:
                    params_df = pd.DataFrame(param_data)
                    combined = combined.merge(params_df, on="Scenario", how="left")
                
                return combined

            combined_tab = build_export_table(plot_df, res_df)

            with io.BytesIO() as buffer:
                with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                    combined_tab.to_excel(writer, index=False, sheet_name="All_Data")
                st.download_button("Download results (Excel)", data=buffer.getvalue(), file_name="simulation_lcoe_dashboard_export.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            st.caption("Notes: LCOE uses PV(costs)/PV(generation) over the selected horizon. Fuel, non-fuel variable, and fixed production costs escalate annually from 2024 values using their per-generator escalation rates. CAPEX treatment is selectable (upfront or annualized with CRF). Generation and costs are discounted using the chosen scheme. Carrier panels use the base single-year operational data.")

elif page == "🔍 Sensitivity Analysis":
    # -----------------------------
    # Sensitivity Analysis Section
    # -----------------------------
    st.markdown("### Cost Sensitivity Analysis")
    st.markdown("Analyze how the optimal capacity mix changes as specific cost parameters vary.")

    # Create sensitivity analysis controls
    sens_col1, sens_col2 = st.columns(2)

    with sens_col1:
        st.markdown("**Select Parameters to Vary**")
        st.markdown("💡 *Select multiple parameters to vary them simultaneously*")
        
        # Allow multiple parameter selection
        enable_multi_param = st.checkbox("Enable multi-parameter sensitivity", help="Vary multiple parameters simultaneously")
        selected_params = []  # Initialize for both cases
        
        if enable_multi_param:
            st.markdown("**Parameter Selection**")
            
            # Generator Cost Parameters
            st.markdown("*Generator Cost Parameters:*")
            gen_cost_cols = [col for col in cost_df.columns if col not in ["Generator", "Carrier"]]
            for param in gen_cost_cols:
                available_gens = cost_df[cost_df[param].notna()]["Generator"].unique()
                if len(available_gens) > 0:
                    if st.checkbox(f"Generator Cost - {param}"):
                        selected_gen = st.selectbox(f"Generator for {param}", available_gens, key=f"gen_{param}")
                        current_val = cost_df[cost_df["Generator"] == selected_gen][param].iloc[0]
                        if isinstance(current_val, str) and "%" in str(current_val):
                            current_val = to_float(current_val) * 100
                        else:
                            current_val = to_float(current_val)
                        selected_params.append({
                            "type": "Generator Cost",
                            "param": param,
                            "generator": selected_gen,
                            "current_val": current_val,
                            "label": f"{param} ({selected_gen})"
                        })
            
            # Fuel Cost Parameters
            st.markdown("*Fuel Cost Parameters:*")
            available_fuels = fuel_df["Fuel"].unique()
            fuel_cost_cols = [col for col in fuel_df.columns if col not in ["Fuel"]]
            for fuel in available_fuels:
                for param in fuel_cost_cols:
                    if st.checkbox(f"Fuel Cost - {fuel} {param}"):
                        current_val = fuel_df[fuel_df["Fuel"] == fuel][param].iloc[0]
                        current_val = to_float(current_val)
                        selected_params.append({
                            "type": "Fuel Cost",
                            "param": param,
                            "fuel": fuel,
                            "current_val": current_val,
                            "label": f"{param} ({fuel})"
                        })
            
            # Wind Technology Parameters
            st.markdown("*Wind Technology Parameters:*")
            wind_params = [
                "Capital Cost ($/kW)",
                "Fixed Production Cost ($/kW-yr)", 
                "Non-fuel Variable Cost ($/MWh)",
                "Discount Rate (%)",
                "Capital Cost Escalation (%/yr)",
                "Fixed Production Escalation (%/yr)",
                "Variable Cost Escalation (%/yr)"
            ]
            for param in wind_params:
                if st.checkbox(f"Wind - {param}"):
                    if 'wind_override_enabled' in st.session_state and st.session_state.wind_override_enabled:
                        wind_current_values = {
                            "Capital Cost ($/kW)": st.session_state.get('wind_capex', 1500.0),
                            "Fixed Production Cost ($/kW-yr)": st.session_state.get('wind_fixed_cost', 30.0),
                            "Non-fuel Variable Cost ($/MWh)": st.session_state.get('wind_var_cost', 0.0),
                            "Discount Rate (%)": st.session_state.get('wind_discount', 0.05) * 100.0,
                            "Capital Cost Escalation (%/yr)": 2.0,
                            "Fixed Production Escalation (%/yr)": st.session_state.get('wind_fixed_esc', 0.025) * 100.0,
                            "Variable Cost Escalation (%/yr)": st.session_state.get('wind_var_esc', 0.025) * 100.0
                        }
                    else:
                        wind_current_values = {
                            "Capital Cost ($/kW)": 1500.0,
                            "Fixed Production Cost ($/kW-yr)": 30.0,
                            "Non-fuel Variable Cost ($/MWh)": 0.0,
                            "Discount Rate (%)": 5.0,
                            "Capital Cost Escalation (%/yr)": 2.0,
                            "Fixed Production Escalation (%/yr)": 2.5,
                            "Variable Cost Escalation (%/yr)": 2.5
                        }
                    current_val = wind_current_values[param]
                    selected_params.append({
                        "type": "Wind Technology Override",
                        "param": param,
                        "current_val": current_val,
                        "label": f"Wind {param}"
                    })
            
            # Solar Technology Parameters
            st.markdown("*Solar Technology Parameters:*")
            solar_params = [
                "Capital Cost ($/kW)",
                "Fixed Production Cost ($/kW-yr)", 
                "Non-fuel Variable Cost ($/MWh)",
                "Discount Rate (%)",
                "Capital Cost Escalation (%/yr)",
                "Fixed Production Escalation (%/yr)",
                "Variable Cost Escalation (%/yr)"
            ]
            for param in solar_params:
                if st.checkbox(f"Solar - {param}"):
                    if 'solar_override_enabled' in st.session_state and st.session_state.solar_override_enabled:
                        solar_current_values = {
                            "Capital Cost ($/kW)": st.session_state.get('solar_capex', 1200.0),
                            "Fixed Production Cost ($/kW-yr)": st.session_state.get('solar_fixed_cost', 20.0),
                            "Non-fuel Variable Cost ($/MWh)": st.session_state.get('solar_var_cost', 0.0),
                            "Discount Rate (%)": st.session_state.get('solar_discount', 0.05) * 100.0,
                            "Capital Cost Escalation (%/yr)": 1.5,
                            "Fixed Production Escalation (%/yr)": st.session_state.get('solar_fixed_esc', 0.025) * 100.0,
                            "Variable Cost Escalation (%/yr)": st.session_state.get('solar_var_esc', 0.025) * 100.0
                        }
                    else:
                        solar_current_values = {
                            "Capital Cost ($/kW)": 1200.0,
                            "Fixed Production Cost ($/kW-yr)": 20.0,
                            "Non-fuel Variable Cost ($/MWh)": 0.0,
                            "Discount Rate (%)": 4.0,
                            "Capital Cost Escalation (%/yr)": 1.5,
                            "Fixed Production Escalation (%/yr)": 2.0,
                            "Variable Cost Escalation (%/yr)": 2.0
                        }
                    current_val = solar_current_values[param]
                    selected_params.append({
                        "type": "Solar Technology Override",
                        "param": param,
                        "current_val": current_val,
                        "label": f"Solar {param}"
                    })
            
            if len(selected_params) == 0:
                st.warning("Please select at least one parameter to vary.")
                
        else:
            # Single parameter mode (original logic)
            param_type = st.selectbox("Parameter Type", ["Generator Cost", "Fuel Cost", "Wind Technology Override", "Solar Technology Override"])
            
            if param_type == "Generator Cost":
                # Get available generator cost columns
                gen_cost_cols = [col for col in cost_df.columns if col not in ["Generator", "Carrier"]]
                selected_param = st.selectbox("Generator Cost Parameter", gen_cost_cols)
                
                # Get generators that have this parameter
                available_gens = cost_df[cost_df[selected_param].notna()]["Generator"].unique()
                selected_generator = st.selectbox("Generator", available_gens)
                
                # Get current value for reference
                current_val = cost_df[cost_df["Generator"] == selected_generator][selected_param].iloc[0]
                if isinstance(current_val, str) and "%" in str(current_val):
                    current_val = to_float(current_val) * 100  # Convert to percentage for display
                else:
                    current_val = to_float(current_val)
                
                selected_params = [{
                    "type": "Generator Cost",
                    "param": selected_param,
                    "generator": selected_generator,
                    "current_val": current_val,
                    "label": f"{selected_param} ({selected_generator})"
                }]
                
            elif param_type == "Fuel Cost":
                available_fuels = fuel_df["Fuel"].unique()
                selected_fuel = st.selectbox("Fuel", available_fuels)
                
                # Get available fuel cost columns
                fuel_cost_cols = [col for col in fuel_df.columns if col not in ["Fuel"]]
                selected_param = st.selectbox("Fuel Cost Parameter", fuel_cost_cols)
                
                # Get current value
                current_val = fuel_df[fuel_df["Fuel"] == selected_fuel][selected_param].iloc[0]
                current_val = to_float(current_val)
                
                selected_params = [{
                    "type": "Fuel Cost",
                    "param": selected_param,
                    "fuel": selected_fuel,
                    "current_val": current_val,
                    "label": f"{selected_param} ({selected_fuel})"
                }]
                
            elif param_type == "Wind Technology Override":
                wind_params = [
                    "Capital Cost ($/kW)",
                    "Fixed Production Cost ($/kW-yr)", 
                    "Non-fuel Variable Cost ($/MWh)",
                    "Discount Rate (%)",
                    "Capital Cost Escalation (%/yr)",
                    "Fixed Production Escalation (%/yr)",
                    "Variable Cost Escalation (%/yr)"
                ]
                selected_param = st.selectbox("Wind Parameter", wind_params)
                
                # Get current values from user inputs if wind override is enabled, otherwise use defaults
                if 'wind_override_enabled' in st.session_state and st.session_state.wind_override_enabled:
                    wind_current_values = {
                        "Capital Cost ($/kW)": st.session_state.get('wind_capex', 1500.0),
                        "Fixed Production Cost ($/kW-yr)": st.session_state.get('wind_fixed_cost', 30.0),
                        "Non-fuel Variable Cost ($/MWh)": st.session_state.get('wind_var_cost', 0.0),
                        "Discount Rate (%)": st.session_state.get('wind_discount', 0.05) * 100.0,  # Convert back to percentage
                        "Capital Cost Escalation (%/yr)": 2.0,  # Not currently in override controls
                        "Fixed Production Escalation (%/yr)": st.session_state.get('wind_fixed_esc', 0.025) * 100.0,  # Convert back to percentage
                        "Variable Cost Escalation (%/yr)": st.session_state.get('wind_var_esc', 0.025) * 100.0  # Convert back to percentage
                    }
                else:
                    # Use default values if override is not enabled
                    wind_current_values = {
                        "Capital Cost ($/kW)": 1500.0,
                        "Fixed Production Cost ($/kW-yr)": 30.0,
                        "Non-fuel Variable Cost ($/MWh)": 0.0,
                        "Discount Rate (%)": 5.0,
                        "Capital Cost Escalation (%/yr)": 2.0,
                        "Fixed Production Escalation (%/yr)": 2.5,
                        "Variable Cost Escalation (%/yr)": 2.5
                    }
                current_val = wind_current_values[selected_param]
                
                selected_params = [{
                    "type": "Wind Technology Override",
                    "param": selected_param,
                    "current_val": current_val,
                    "label": f"Wind {selected_param}"
                }]
                
            else:  # Solar Technology Override
                solar_params = [
                    "Capital Cost ($/kW)",
                    "Fixed Production Cost ($/kW-yr)", 
                    "Non-fuel Variable Cost ($/MWh)",
                    "Discount Rate (%)",
                    "Capital Cost Escalation (%/yr)",
                    "Fixed Production Escalation (%/yr)",
                    "Variable Cost Escalation (%/yr)"
                ]
                selected_param = st.selectbox("Solar Parameter", solar_params)
                
                # Get current values from user inputs if solar override is enabled, otherwise use defaults
                if 'solar_override_enabled' in st.session_state and st.session_state.solar_override_enabled:
                    solar_current_values = {
                        "Capital Cost ($/kW)": st.session_state.get('solar_capex', 1200.0),
                        "Fixed Production Cost ($/kW-yr)": st.session_state.get('solar_fixed_cost', 20.0),
                        "Non-fuel Variable Cost ($/MWh)": st.session_state.get('solar_var_cost', 0.0),
                        "Discount Rate (%)": st.session_state.get('solar_discount', 0.05) * 100.0,  # Convert back to percentage
                        "Capital Cost Escalation (%/yr)": 1.5,  # Not currently in override controls
                        "Fixed Production Escalation (%/yr)": st.session_state.get('solar_fixed_esc', 0.025) * 100.0,  # Convert back to percentage
                        "Variable Cost Escalation (%/yr)": st.session_state.get('solar_var_esc', 0.025) * 100.0  # Convert back to percentage
                    }
                else:
                    # Use default values if override is not enabled
                    solar_current_values = {
                        "Capital Cost ($/kW)": 1200.0,
                        "Fixed Production Cost ($/kW-yr)": 20.0,
                        "Non-fuel Variable Cost ($/MWh)": 0.0,
                        "Discount Rate (%)": 4.0,
                        "Capital Cost Escalation (%/yr)": 1.5,
                        "Fixed Production Escalation (%/yr)": 2.0,
                        "Variable Cost Escalation (%/yr)": 2.0
                    }
                current_val = solar_current_values[selected_param]
                
                selected_params = [{
                    "type": "Solar Technology Override",
                    "param": selected_param,
                    "current_val": current_val,
                    "label": f"Solar {selected_param}"
                }]

    with sens_col2:
        st.markdown("**Define Value Range**")
        
        if enable_multi_param and len(selected_params) > 0:
            st.markdown("*Parameters to be varied:*")
            for param_info in selected_params:
                st.write(f"• {param_info['label']}: {param_info['current_val']:.2f}")
            st.markdown("---")
            st.markdown("*The same multiplier range will be applied to all selected parameters*")
            
        elif not enable_multi_param and len(selected_params) > 0:
            st.write(f"Current value: {selected_params[0]['current_val']:.2f}")
        
        # Create range inputs
        min_mult = st.number_input("Minimum multiplier", min_value=0.1, max_value=5.0, value=0.5, step=0.1)
        max_mult = st.number_input("Maximum multiplier", min_value=0.1, max_value=5.0, value=2.0, step=0.1)
        num_points = st.number_input("Number of points", min_value=3, max_value=20, value=5, step=1)
        
        # Add tolerance for lowest cost scenarios
        st.markdown("**Lowest Cost Scenarios**")
        lcoe_tolerance = st.number_input("LCOE tolerance ($/MWh)", 
                                       min_value=1.0, max_value=100.0, value=10.0, step=1.0,
                                       help="Include scenarios with LCOE ≤ (minimum LCOE + tolerance)")
        
        # Generate test values
        test_multipliers = np.linspace(min_mult, max_mult, num_points)

    # Run sensitivity analysis when button is pressed
    if st.button("Run Sensitivity Analysis"):
        if not selected_params:
            st.error("Please select at least one parameter to vary.")
        else:
            sensitivity_results = []
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, mult in enumerate(test_multipliers):
                status_text.text(f"Running analysis {i+1}/{len(test_multipliers)}...")
                progress_bar.progress((i + 1) / len(test_multipliers))
                
                # Create modified cost dataframes by applying multiplier to all selected parameters
                mod_cost_df = cost_df.copy()
                mod_fuel_df = fuel_df.copy()
                
                # Apply changes for all selected parameters
                for param_info in selected_params:
                    test_val = mult * param_info['current_val']
                    param_type = param_info['type']
                    
                    if param_type == "Generator Cost":
                        selected_param = param_info['param']
                        selected_generator = param_info['generator']
                        if "%" in str(cost_df[cost_df["Generator"] == selected_generator][selected_param].iloc[0]):
                            # Handle percentage values
                            mod_cost_df.loc[mod_cost_df["Generator"] == selected_generator, selected_param] = f"{test_val:.2f}%"
                        else:
                            mod_cost_df.loc[mod_cost_df["Generator"] == selected_generator, selected_param] = test_val
                            
                    elif param_type == "Fuel Cost":
                        selected_param = param_info['param']
                        selected_fuel = param_info['fuel']
                        mod_fuel_df.loc[mod_fuel_df["Fuel"] == selected_fuel, selected_param] = test_val
                        
                    elif param_type == "Wind Technology Override":
                        selected_param = param_info['param']
                        # Apply wind technology override to all wind generators
                        wind_mask = mod_cost_df["Carrier"].str.contains("wind", case=False, na=False)
                        
                        # Map parameter names to column names
                        param_col_map = {
                            "Capital Cost ($/kW)": "Capital cost ($/kW)",
                            "Fixed Production Cost ($/kW-yr)": "2024 Fixed Production cost ($/kW-yr)",
                            "Non-fuel Variable Cost ($/MWh)": "2024 Non-fuel var cost ($/MWh)",
                            "Discount Rate (%)": "Discount rate (%)",
                            "Capital Cost Escalation (%/yr)": "Capital cost escalation (%/yr)",
                            "Fixed Production Escalation (%/yr)": "Fixed Production escalation rate (%/yr)",
                            "Variable Cost Escalation (%/yr)": "Non-fuel var cost escalation rate (%/yr)"
                        }
                        
                        if selected_param in param_col_map:
                            col_name = param_col_map[selected_param]
                            if col_name in mod_cost_df.columns:
                                if "%" in selected_param:
                                    mod_cost_df.loc[wind_mask, col_name] = f"{test_val:.2f}%"
                                else:
                                    mod_cost_df.loc[wind_mask, col_name] = test_val
                                    
                    elif param_type == "Solar Technology Override":
                        selected_param = param_info['param']
                        # Apply solar technology override to all solar generators
                        solar_mask = mod_cost_df["Carrier"].str.contains("solar", case=False, na=False)
                        
                        # Map parameter names to column names
                        param_col_map = {
                            "Capital Cost ($/kW)": "Capital cost ($/kW)",
                            "Fixed Production Cost ($/kW-yr)": "2024 Fixed Production cost ($/kW-yr)",
                            "Non-fuel Variable Cost ($/MWh)": "2024 Non-fuel var cost ($/MWh)",
                            "Discount Rate (%)": "Discount rate (%)",
                            "Capital Cost Escalation (%/yr)": "Capital cost escalation (%/yr)",
                            "Fixed Production Escalation (%/yr)": "Fixed Production escalation rate (%/yr)",
                            "Variable Cost Escalation (%/yr)": "Non-fuel var cost escalation rate (%/yr)"
                        }
                        
                        if selected_param in param_col_map:
                            col_name = param_col_map[selected_param]
                            if col_name in mod_cost_df.columns:
                                if "%" in selected_param:
                                    mod_cost_df.loc[solar_mask, col_name] = f"{test_val:.2f}%"
                                else:
                                    mod_cost_df.loc[solar_mask, col_name] = test_val
                
                # Parse numeric columns for modified cost df
                for col in ["Non-fuel var cost escalation rate (%/yr)",
                            "Fixed Production escalation rate (%/yr)",
                            "Discount rate (%)",
                            "2024 Non-fuel var cost ($/MWh)",
                            "2024 Fixed Production cost ($/kW-yr)",
                            "Capital cost ($/kW)"]:
                    if col in mod_cost_df.columns:
                        mod_cost_df[col] = mod_cost_df[col].apply(to_float)
                
                if "2024 Fuel cost ($/MMBtu)" in mod_fuel_df.columns:
                    mod_fuel_df["2024 Fuel cost ($/MMBtu)"] = mod_fuel_df["2024 Fuel cost ($/MMBtu)"].apply(to_float)
                
                if "Fuel escalation rate (%/yr)" in mod_fuel_df.columns:
                    mod_fuel_df["Fuel escalation rate (%/yr)"] = mod_fuel_df["Fuel escalation rate (%/yr)"].apply(to_float)
                
                # Recalculate LCOE for all scenarios with modified costs
                gen_cost_mod = mod_cost_df.rename(columns={
                    "Non-fuel var cost escalation rate (%/yr)":"nfu_esc",
                    "Fixed Production escalation rate (%/yr)":"fpu_esc",
                    "Capital cost ($/kW)":"capex_per_kw",
                    "Discount rate (%)":"disc_rate_gen",
                    "2024 Non-fuel var cost ($/MWh)":"nfu_2024",
                    "2024 Fixed Production cost ($/kW-yr)":"fpu_2024",
                })
                
                # Avoid double-merge if ops_f already contains cost columns: drop overlapping cost columns
                base_ops = ops_f.copy()
                for c in gen_cost_mod.columns:
                    if c in ["Generator", "Carrier"]:
                        continue
                    if c in base_ops.columns:
                        base_ops = base_ops.drop(columns=[c])

                ops_mod = base_ops.merge(gen_cost_mod, on=["Generator","Carrier"], how="left", validate="m:1")
                fuel_map_mod = dict(zip(mod_fuel_df["Fuel"].astype(str), mod_fuel_df["2024 Fuel cost ($/MMBtu)"]))
                
                # Create fuel escalation mapping for sensitivity analysis
                if "Fuel escalation rate (%/yr)" in mod_fuel_df.columns:
                    fuel_esc_map_mod = dict(zip(mod_fuel_df["Fuel"].astype(str), mod_fuel_df["Fuel escalation rate (%/yr)"]))
                else:
                    fuel_esc_map_mod = {}
                
                # Map fuel escalation rates to operations data by Carrier
                ops_mod["fuel_esc"] = ops_mod["Carrier"].astype(str).map(fuel_esc_map_mod).fillna(0.0)

                # Clean numerics
                for col in ["fuel_esc","nfu_esc","fpu_esc","nfu_2024","fpu_2024","capex_per_kw","disc_rate_gen"]:
                    if col in ops_mod.columns:
                        ops_mod[col] = ops_mod[col].apply(to_float)

                scenario_lcoes = []
                years = list(range(int(start_year), int(end_year)+1))

                # Calculate LCOE for each scenario with modified costs using full multi-year PV logic
                for scen, sdf in ops_mod.groupby("Scenario", sort=False):
                    gen_MWh = sdf["Total_Generation_MWh"].fillna(0.0).values
                    fuel_MMBtu = sdf["Fuel_Consumption_MMBtu"].fillna(0.0).values
                    cap_MW = sdf["Scenario_Capacity_MW"].fillna(0.0).values
                    carriers = sdf["Carrier"].astype(str).values

                    # Cost parameters (per generator)
                    fuel_esc = sdf["fuel_esc"].fillna(0.0).values if "fuel_esc" in sdf.columns else np.zeros(len(sdf))
                    nfu_esc = sdf["nfu_esc"].fillna(0.0).values if "nfu_esc" in sdf.columns else np.zeros(len(sdf))
                    fpu_esc = sdf["fpu_esc"].fillna(0.0).values if "fpu_esc" in sdf.columns else np.zeros(len(sdf))
                    nfu_2024 = sdf["nfu_2024"].fillna(0.0).values if "nfu_2024" in sdf.columns else np.zeros(len(sdf))
                    fpu_2024 = sdf["fpu_2024"].fillna(0.0).values if "fpu_2024" in sdf.columns else np.zeros(len(sdf))
                    capex_kw = sdf["capex_per_kw"].fillna(0.0).values if "capex_per_kw" in sdf.columns else np.zeros(len(sdf))
                    cap_cost_year = sdf["Capital cost year"].fillna(np.nan).values if "Capital cost year" in sdf.columns else np.full(len(sdf), np.nan)
                    first_year = sdf["First year"].fillna(np.nan).values if "First year" in sdf.columns else np.full(len(sdf), np.nan)
                    gen_disc_rate = sdf["disc_rate_gen"].fillna(global_discount_rate if use_global_discount else 0.05).values if "disc_rate_gen" in sdf.columns else np.full(len(sdf), global_discount_rate if use_global_discount else 0.05)
                    base_fuel_price = np.array([fuel_map_mod.get(f, np.nan) for f in carriers], dtype=float)

                    pv_cost_sum = 0.0
                    pv_gen_sum = 0.0

                    # CAPEX handling (once per generator)
                    for j in range(len(sdf)):
                        kw = cap_MW[j] * 1000.0
                        capex_total = kw * capex_kw[j]
                        if capex_total > 0:
                            start_incl_year = int(max(start_year, int(first_year[j]) if (not pd.isna(first_year[j])) else start_year))
                            if start_incl_year <= end_year:
                                y0_offset = start_incl_year - start_year
                                r_for_capex = (global_discount_rate if use_global_discount else gen_disc_rate[j])
                                if capex_treatment.startswith("Upfront"):
                                    df_y0 = discount_factor(r_for_capex, y0_offset)
                                    pv_cost_sum += capex_total * df_y0
                                else:
                                    crf = capital_recovery_factor(r_for_capex, asset_life_years)
                                    annual_payment = capex_total * crf
                                    for yr in years:
                                        if yr >= start_incl_year and yr < start_incl_year + asset_life_years:
                                            t = yr - start_year
                                            pv_cost_sum += annual_payment * discount_factor(r_for_capex, t)

                    # Yearly O&M + Fuel + (repeat ops & costs each year)
                    for t, yr in enumerate(years):
                        for j in range(len(sdf)):
                            r_j = (global_discount_rate if use_global_discount else gen_disc_rate[j])

                            years_from_2024 = yr - 2024
                            fuel_price_y = escalate(base_fuel_price[j], fuel_esc[j], years_from_2024)
                            nfu_cost_y = escalate(nfu_2024[j], nfu_esc[j], years_from_2024)
                            fpu_cost_y = escalate(fpu_2024[j], fpu_esc[j], years_from_2024)

                            cost_fuel = (fuel_MMBtu[j] if repeat_ops_each_year else 0.0) * (fuel_price_y if not pd.isna(fuel_price_y) else 0.0)
                            cost_nfu = (gen_MWh[j] if repeat_ops_each_year else 0.0) * (nfu_cost_y if not pd.isna(nfu_cost_y) else 0.0)
                            cost_fpu = (cap_MW[j] * 1000.0) * (fpu_cost_y if not pd.isna(fpu_cost_y) else 0.0)

                            df_t = discount_factor(r_j, t)
                            pv_cost_sum += (cost_fuel + cost_nfu + cost_fpu) * df_t
                            pv_gen_sum += (gen_MWh[j] if repeat_ops_each_year else 0.0) * df_t

                    lcoe = np.nan if pv_gen_sum == 0 else pv_cost_sum / pv_gen_sum
                    scenario_lcoes.append({"Scenario": scen, "LCOE": lcoe})
                
                # Find lowest LCOE scenarios within tolerance
                if scenario_lcoes:
                    scenario_lcoes_df = pd.DataFrame(scenario_lcoes)
                    best_lcoe = scenario_lcoes_df["LCOE"].min()
                    
                    # Find all scenarios within tolerance
                    lcoe_threshold = best_lcoe + lcoe_tolerance  # Both are in $/MWh
                    low_cost_scenarios = scenario_lcoes_df[scenario_lcoes_df["LCOE"] <= lcoe_threshold]["Scenario"].tolist()
                    
                    # Get capacity mix for all low-cost scenarios and calculate ranges
                    low_cost_data = ops_f[ops_f["Scenario"].isin(low_cost_scenarios)]
                    
                    # Calculate capacity by carrier for each low-cost scenario
                    scenario_capacity_mixes = []
                    for scenario in low_cost_scenarios:
                        scenario_data = low_cost_data[low_cost_data["Scenario"] == scenario]
                        cap_mix = scenario_data.groupby("Carrier")["Scenario_Capacity_MW"].sum().to_dict()
                        scenario_capacity_mixes.append(cap_mix)
                    
                    # Calculate capacity ranges for each carrier
                    carriers_to_use = sorted(set(low_cost_data["Carrier"].unique()))
                        
                    capacity_ranges = {}
                    for carrier in carriers_to_use:
                        carrier_capacities = [mix.get(carrier, 0) for mix in scenario_capacity_mixes]
                        if carrier_capacities:
                            capacity_ranges[carrier] = {
                                'min': min(carrier_capacities),
                                'max': max(carrier_capacities),
                                'avg': sum(carrier_capacities) / len(carrier_capacities)
                            }
                        else:
                            capacity_ranges[carrier] = {'min': 0, 'max': 0, 'avg': 0}
                    
                    # Get best single scenario for backward compatibility
                    best_scenario = scenario_lcoes_df.loc[scenario_lcoes_df["LCOE"].idxmin(), "Scenario"]
                    best_scenario_data = ops_f[ops_f["Scenario"] == best_scenario]
                    cap_mix = best_scenario_data.groupby("Carrier")["Scenario_Capacity_MW"].sum().to_dict()
                    
                    sensitivity_results.append({
                        "Parameter_Value": mult if len(selected_params) > 1 else (mult * selected_params[0]['current_val']),
                        "Multiplier": mult,
                        "Best_Scenario": best_scenario,
                        "Best_LCOE": best_lcoe,
                        "Capacity_Mix": cap_mix,
                        "Capacity_Ranges": capacity_ranges,
                        "Low_Cost_Scenarios_Count": len(low_cost_scenarios),
                        "Low_Cost_Scenarios": low_cost_scenarios,
                        "LCOE_Threshold": lcoe_threshold,
                        "Parameters_Varied": [p['label'] for p in selected_params]
                    })
        
        progress_bar.empty()
        status_text.empty()
        
        # Create a dedicated container for sensitivity results
        if sensitivity_results:
            st.markdown("---")
            st.markdown("### Sensitivity Analysis Results")
            
            # Use a container to ensure proper layout expansion
            with st.container():
                # Create sensitivity plot
                sens_df = pd.DataFrame(sensitivity_results)
                
                # Create capacity range plot
                fig_sens = go.Figure()
                
                param_values = sens_df["Parameter_Value"].values
                
                # Define which carriers should be visible by default
                default_visible_carriers = {"geo", "wind", "solar", "gas"}
                
                # Create a color mapping for consistent colors across all plots
                import plotly.colors as pc
                colors = pc.qualitative.Plotly + pc.qualitative.Dark24 + pc.qualitative.Light24
                color_map = {carrier: colors[i % len(colors)] for i, carrier in enumerate(carriers_to_use)}
            
                for carrier in carriers_to_use:
                    # Get capacity ranges for this carrier
                    carrier_mins = [result["Capacity_Ranges"].get(carrier, {}).get('min', 0) for result in sensitivity_results]
                    carrier_maxs = [result["Capacity_Ranges"].get(carrier, {}).get('max', 0) for result in sensitivity_results]
                    carrier_avgs = [result["Capacity_Ranges"].get(carrier, {}).get('avg', 0) for result in sensitivity_results]
                    
                    # Add shaded area for min-max range
                    if carrier_mins != carrier_maxs:  # Only show range if there's variation
                        # Convert color to rgba with transparency
                        base_color = color_map.get(carrier, 'gray')
                        if base_color.startswith('#'):
                            # Convert hex to rgba
                            r, g, b = int(base_color[1:3], 16), int(base_color[3:5], 16), int(base_color[5:7], 16)
                            fill_color = f"rgba({r},{g},{b},0.2)"
                        else:
                            fill_color = f"rgba(128,128,128,0.2)"  # Fallback gray
                        
                        fig_sens.add_trace(go.Scatter(
                            x=list(param_values) + list(reversed(param_values)),
                            y=carrier_maxs + list(reversed(carrier_mins)),
                            fill='toself',
                            fillcolor=fill_color,
                            line=dict(width=0),
                            mode='none',
                            name=f"{carrier} Range",
                            legendgroup=carrier,
                            showlegend=False,
                            hoverinfo='skip'
                        ))
                    
                    # Add average line
                    visibility = True if carrier.lower() in default_visible_carriers else 'legendonly'
                    fig_sens.add_trace(go.Scatter(
                        x=param_values,
                        y=carrier_avgs,
                        mode='lines+markers',
                        name=f"{carrier} (avg)",
                        line=dict(color=color_map.get(carrier, 'gray'), width=3),
                        legendgroup=carrier,
                        showlegend=True,
                        visible=visibility
                    ))
                
                # Create plot title and axis labels based on parameter selection
                if len(selected_params) == 1:
                    param_info = selected_params[0]
                    param_label = param_info['label']
                    x_axis_title = param_label
                    title_suffix = f"vs {param_label}"
                else:
                    param_labels = [p['label'] for p in selected_params]
                    param_label = f"Multiple Parameters ({len(selected_params)} varied)"
                    x_axis_title = "Multiplier"
                    title_suffix = f"vs {param_label}"
                    
                    # Show which parameters are varied in the subtitle
                    params_list = ", ".join(param_labels[:3])  # Show first 3 parameters
                    if len(param_labels) > 3:
                        params_list += f" and {len(param_labels)-3} more"
                
                fig_sens.update_layout(
                    title=f"Capacity Ranges in Lowest-Cost Scenarios {title_suffix}<br><sub>Parameters: {params_list if len(selected_params) > 1 else param_label} | Tolerance: {lcoe_tolerance}$/MWh</sub>",
                    xaxis_title=x_axis_title,
                    yaxis_title="Installed Capacity (MW)",
                    height=400,
                    hovermode='x unified'
                )
                
                # Plot in the container
                st.plotly_chart(fig_sens, use_container_width=True)
                
                # Show summary tables in the same container
                st.markdown("**Summary Table**")
                
                if len(selected_params) == 1:
                    # Single parameter - show actual parameter values
                    summary_table = sens_df[["Parameter_Value", "Multiplier", "Best_LCOE", "Low_Cost_Scenarios_Count", "Low_Cost_Scenarios"]].copy()
                    summary_table["Best_LCOE"] = summary_table["Best_LCOE"].round(2)
                    summary_table["LCOE_Threshold"] = (summary_table["Best_LCOE"] + lcoe_tolerance).round(2)
                    # Format scenario names as comma-separated string
                    summary_table["Scenarios_List"] = summary_table["Low_Cost_Scenarios"].apply(lambda x: ", ".join(x))
                    summary_table = summary_table.rename(columns={
                        "Parameter_Value": f"{selected_params[0]['label']}",
                        "Best_LCOE": "Best LCOE ($/MWh)", 
                        "Low_Cost_Scenarios_Count": "# Low-Cost Scenarios",
                        "LCOE_Threshold": "LCOE Threshold ($/MWh)",
                        "Scenarios_List": "Scenarios Included"
                    })
                    # Drop the original scenarios column after formatting
                    summary_table = summary_table.drop(columns=["Low_Cost_Scenarios"])
                else:
                    # Multiple parameters - show multipliers and list of parameters
                    summary_table = sens_df[["Multiplier", "Best_LCOE", "Low_Cost_Scenarios_Count", "Low_Cost_Scenarios"]].copy()
                    summary_table["Best_LCOE"] = summary_table["Best_LCOE"].round(2)
                    summary_table["LCOE_Threshold"] = (summary_table["Best_LCOE"] + lcoe_tolerance).round(2)
                    # Format scenario names as comma-separated string
                    summary_table["Scenarios_List"] = summary_table["Low_Cost_Scenarios"].apply(lambda x: ", ".join(x))
                    summary_table = summary_table.rename(columns={
                        "Best_LCOE": "Best LCOE ($/MWh)", 
                        "Low_Cost_Scenarios_Count": "# Low-Cost Scenarios",
                        "LCOE_Threshold": "LCOE Threshold ($/MWh)",
                        "Scenarios_List": "Scenarios Included"
                    })
                    # Drop the original scenarios column after formatting
                    summary_table = summary_table.drop(columns=["Low_Cost_Scenarios"])
                
                st.dataframe(summary_table, use_container_width=True)
                
                # Show parameters being varied for multi-parameter case
                if len(selected_params) > 1:
                    st.markdown("**Parameters Varied Simultaneously**")
                    params_info = []
                    for param_info in selected_params:
                        params_info.append({
                            "Parameter": param_info['label'],
                            "Baseline Value": f"{param_info['current_val']:.2f}",
                            "Min Value": f"{min_mult * param_info['current_val']:.2f}",
                            "Max Value": f"{max_mult * param_info['current_val']:.2f}"
                        })
                    params_df = pd.DataFrame(params_info)
                    st.dataframe(params_df, use_container_width=True)
                
                # Show detailed capacity ranges table
                st.markdown("**Capacity Ranges by Technology (MW)**")
                capacity_ranges_data = []
                for i, result in enumerate(sensitivity_results):
                    if len(selected_params) == 1:
                        param_val = result["Parameter_Value"]
                        param_col_name = selected_params[0]['label']
                    else:
                        param_val = result["Multiplier"]
                        param_col_name = "Multiplier"
                    
                    for carrier in carriers_to_use:
                        ranges = result["Capacity_Ranges"].get(carrier, {'min': 0, 'max': 0, 'avg': 0})
                        if ranges['max'] > 0:  # Only show carriers with non-zero capacity
                            capacity_ranges_data.append({
                                param_col_name: param_val,
                                "Technology": carrier,
                                "Min (MW)": round(ranges['min'], 1),
                                "Max (MW)": round(ranges['max'], 1), 
                                "Avg (MW)": round(ranges['avg'], 1),
                                "Range (MW)": round(ranges['max'] - ranges['min'], 1)
                            })
                
                if capacity_ranges_data:
                    capacity_df = pd.DataFrame(capacity_ranges_data)
                    st.dataframe(capacity_df, use_container_width=True)
                
                # Add spacing within container to ensure proper layout
                st.markdown("")
                st.markdown("")
            
        else:
            if 'sensitivity_results' in locals():
                st.error("No results generated. Please check your inputs.")

elif page == "⚡ Generator Breakdown":
    st.markdown("## Generator Cost Breakdown Analysis")
    
    # Calculate scenario LCOE for scenario selection using consistent PV methodology
    scenario_results = []
    years = list(range(int(start_year), int(end_year)+1))
    
    for scen, sdf in ops_f.groupby("Scenario", sort=False):
        # Per generator static values (repeat ops each year)
        gen_MWh = sdf["Total_Generation_MWh"].fillna(0.0).values
        fuel_MMBtu = sdf["Fuel_Consumption_MMBtu"].fillna(0.0).values
        cap_MW = sdf["Scenario_Capacity_MW"].fillna(0.0).values
        carriers = sdf["Carrier"].astype(str).values

        # Cost parameters (per generator)
        fuel_esc = sdf["fuel_esc"].fillna(0.0).values
        nfu_esc = sdf["nfu_esc"].fillna(0.0).values
        fpu_esc = sdf["fpu_esc"].fillna(0.0).values
        nfu_2024 = sdf["nfu_2024"].fillna(0.0).values
        fpu_2024 = sdf["fpu_2024"].fillna(0.0).values
        capex_kw = sdf["capex_per_kw"].fillna(0.0).values
        cap_cost_year = sdf["Capital cost year"].fillna(np.nan).values if "Capital cost year" in sdf.columns else np.full(len(sdf), np.nan)
        first_year = sdf["First year"].fillna(np.nan).values if "First year" in sdf.columns else np.full(len(sdf), np.nan)
        gen_disc_rate = sdf["disc_rate_gen"].fillna(global_discount_rate if use_global_discount else 0.05).values
        # Fuel base prices (2024)
        base_fuel_price = np.array([fuel_map.get(f, np.nan) for f in carriers], dtype=float)

        # Aggregate across years using present value methodology (same as main page)
        pv_cost_sum = 0.0
        pv_gen_sum = 0.0

        # CAPEX handling (once per generator)
        for j in range(len(sdf)):
            kw = cap_MW[j] * 1000.0
            capex_total = kw * capex_kw[j]
            if capex_total > 0:
                start_incl_year = int(max(start_year, first_year[j] if not math.isnan(first_year[j]) else start_year))
                if start_incl_year > end_year:
                    pass  # outside horizon; ignore
                else:
                    y0_offset = start_incl_year - start_year
                    r_for_capex = (global_discount_rate if use_global_discount else gen_disc_rate[j])
                    if capex_treatment.startswith("Upfront"):
                        df_y0 = discount_factor(r_for_capex, y0_offset)
                        pv_cost_sum += capex_total * df_y0
                    else:
                        crf = capital_recovery_factor(r_for_capex, asset_life_years)
                        annual_payment = capex_total * crf
                        for yr in years:
                            if yr >= start_incl_year and yr < start_incl_year + asset_life_years:
                                t = yr - start_year
                                pv_cost_sum += annual_payment * discount_factor(r_for_capex, t)

        # Yearly O&M + Fuel + (repeat ops & costs each year)
        for t, yr in enumerate(years):
            # Choose discount rate for PV of costs and gen (system-level: use global or per-generator)
            for j in range(len(sdf)):
                r_j = (global_discount_rate if use_global_discount else gen_disc_rate[j])

                # Fuel price escalation anchored to 2024
                years_from_2024 = yr - 2024
                fuel_price_y = escalate(base_fuel_price[j], fuel_esc[j], years_from_2024)

                # Non-fuel variable and Fixed production escalation anchored to 2024
                nfu_cost_y = escalate(nfu_2024[j], nfu_esc[j], years_from_2024)  # $/MWh
                fpu_cost_y = escalate(fpu_2024[j], fpu_esc[j], years_from_2024)  # $/kW-yr

                # Costs for that generator that year
                cost_fuel = (fuel_MMBtu[j] if repeat_ops_each_year else 0.0) * (fuel_price_y if not pd.isna(fuel_price_y) else 0.0)
                cost_nfu  = (gen_MWh[j] if repeat_ops_each_year else 0.0) * (nfu_cost_y if not pd.isna(nfu_cost_y) else 0.0)
                cost_fpu  = (cap_MW[j] * 1000.0) * (fpu_cost_y if not pd.isna(fpu_cost_y) else 0.0)

                df_t = discount_factor(r_j, t)
                pv_cost_sum += (cost_fuel + cost_nfu + cost_fpu) * df_t

                # Discounted generation
                gen_y = (gen_MWh[j] if repeat_ops_each_year else 0.0)
                pv_gen_sum += gen_y * df_t

        lcoe = np.nan if pv_gen_sum == 0 else pv_cost_sum / pv_gen_sum
        scenario_results.append({
            'Scenario': scen,
            'LCOE_$perMWh': lcoe
        })
    
    # Sort scenarios by LCOE
    scenario_df = pd.DataFrame(scenario_results).sort_values('LCOE_$perMWh')
    
    # Create scenario selection dropdown
    scenario_options = []
    for _, row in scenario_df.iterrows():
        option_text = f"{row['Scenario']} (${row['LCOE_$perMWh']:.1f}/MWh)"
        scenario_options.append(option_text)
    
    # Default to lowest LCOE scenario
    selected_scenario_text = st.selectbox(
        "Select Scenario for Generator Breakdown:",
        options=scenario_options,
        index=0,
        help="Scenarios are listed in order from lowest to highest system LCOE"
    )
    
    # Extract scenario name from selection
    selected_scenario = selected_scenario_text.split(' (')[0]
    
    # Get data for selected scenario
    scenario_data = ops_f[ops_f["Scenario"] == selected_scenario].copy()
    
    if len(scenario_data) > 0:
        # Calculate generator-level LCOE breakdown using consistent present value methodology
        gen_breakdown_data = []
        
        years = list(range(int(start_year), int(end_year)+1))
        
        for _, gen_row in scenario_data.iterrows():
            gen_name = gen_row["Generator"]
            gen_MWh = gen_row["Total_Generation_MWh"]
            
            if gen_MWh > 0:  # Only include generators with generation
                fuel_MMBtu = gen_row["Fuel_Consumption_MMBtu"]
                cap_MW = gen_row["Scenario_Capacity_MW"]
                carrier = str(gen_row["Carrier"])
                
                # Cost parameters (with proper handling of percentage values)
                capex_per_kw = gen_row.get("capex_per_kw", 0)
                disc_rate_gen = gen_row.get("disc_rate_gen", global_discount_rate)
                nfu_2024 = gen_row.get("nfu_2024", 0)
                fpu_2024 = gen_row.get("fpu_2024", 0)
                nfu_esc = gen_row.get("nfu_esc", 0)
                fpu_esc = gen_row.get("fpu_esc", 0)
                fuel_esc = gen_row.get("fuel_esc", 0)
                
                # Get base fuel price and other parameters
                base_fuel_price = fuel_map.get(carrier, 0)
                cap_cost_year = gen_row.get("Capital cost year", start_year)
                first_year_gen = gen_row.get("First year", start_year)
                
                # Calculate present value components for this generator
                pv_capital_cost = 0.0
                pv_fuel_cost = 0.0
                pv_nonfuel_var_cost = 0.0
                pv_fixed_cost = 0.0
                pv_generation = 0.0
                
                # Discount rate selection
                r_gen = global_discount_rate if use_global_discount else disc_rate_gen
                
                # CAPEX handling (same methodology as main page)
                kw = cap_MW * 1000.0
                capex_total = kw * capex_per_kw
                if capex_total > 0:
                    start_incl_year = int(max(start_year, first_year_gen if not pd.isna(first_year_gen) else start_year))
                    if start_incl_year <= end_year:
                        y0_offset = start_incl_year - start_year
                        if capex_treatment.startswith("Upfront"):
                            df_y0 = discount_factor(r_gen, y0_offset)
                            pv_capital_cost = capex_total * df_y0
                        else:
                            crf = capital_recovery_factor(r_gen, asset_life_years)
                            annual_payment = capex_total * crf
                            for yr in years:
                                if yr >= start_incl_year and yr < start_incl_year + asset_life_years:
                                    t = yr - start_year
                                    pv_capital_cost += annual_payment * discount_factor(r_gen, t)
                
                # Yearly O&M + Fuel costs (same methodology as main page)
                for t, yr in enumerate(years):
                    # Fuel price escalation anchored to 2024
                    years_from_2024 = yr - 2024
                    fuel_price_y = escalate(base_fuel_price, fuel_esc, years_from_2024)
                    
                    # Non-fuel variable and Fixed production escalation anchored to 2024
                    nfu_cost_y = escalate(nfu_2024, nfu_esc, years_from_2024)  # $/MWh
                    fpu_cost_y = escalate(fpu_2024, fpu_esc, years_from_2024)  # $/kW-yr
                    
                    # Costs for that generator that year
                    cost_fuel = (fuel_MMBtu if repeat_ops_each_year else 0.0) * (fuel_price_y if not pd.isna(fuel_price_y) else 0.0)
                    cost_nfu = (gen_MWh if repeat_ops_each_year else 0.0) * (nfu_cost_y if not pd.isna(nfu_cost_y) else 0.0)
                    cost_fpu = (cap_MW * 1000.0) * (fpu_cost_y if not pd.isna(fpu_cost_y) else 0.0)
                    
                    # Apply discount factor
                    df_t = discount_factor(r_gen, t)
                    pv_fuel_cost += cost_fuel * df_t
                    pv_nonfuel_var_cost += cost_nfu * df_t
                    pv_fixed_cost += cost_fpu * df_t
                    
                    # Discounted generation
                    gen_y = (gen_MWh if repeat_ops_each_year else 0.0)
                    pv_generation += gen_y * df_t
                
                # Calculate levelized costs ($/MWh) = PV(cost_component) / PV(generation)
                capital_lcoe = pv_capital_cost / pv_generation if pv_generation > 0 else 0
                fuel_lcoe = pv_fuel_cost / pv_generation if pv_generation > 0 else 0
                nonfuel_var_lcoe = pv_nonfuel_var_cost / pv_generation if pv_generation > 0 else 0
                fixed_lcoe = pv_fixed_cost / pv_generation if pv_generation > 0 else 0
                total_lcoe = capital_lcoe + fuel_lcoe + nonfuel_var_lcoe + fixed_lcoe
                
                # Calculate capacity factor (Generation / (Capacity * 8760 hours))
                capacity_factor_pct = (gen_MWh / (cap_MW * 8760)) * 100 if cap_MW > 0 else 0
                
                # Store breakdown data
                gen_breakdown_data.append({
                    'Generator': gen_name,
                    'Generation_MWh': gen_MWh,
                    'Capacity_MW': cap_MW,
                    'Capacity_Factor_pct': capacity_factor_pct,
                    'Capital_Cost': capital_lcoe,
                    'Fuel_Cost': fuel_lcoe,
                    'Non_Fuel_Variable': nonfuel_var_lcoe,
                    'Fixed_Cost': fixed_lcoe,
                    'Total_LCOE': total_lcoe
                })
        
        if gen_breakdown_data:
            # Create breakdown dataframe
            breakdown_df = pd.DataFrame(gen_breakdown_data)
            breakdown_df = breakdown_df.sort_values('Total_LCOE', ascending=False)
            
            # Create stacked bar chart
            fig = go.Figure()
            
            # Add each cost component as a bar
            fig.add_trace(go.Bar(
                name='Capital Cost',
                x=breakdown_df['Generator'],
                y=breakdown_df['Capital_Cost'],
                marker_color='#1f77b4'
            ))
            
            fig.add_trace(go.Bar(
                name='Fuel Cost',
                x=breakdown_df['Generator'],
                y=breakdown_df['Fuel_Cost'],
                marker_color='#ff7f0e'
            ))
            
            fig.add_trace(go.Bar(
                name='Non-Fuel Variable',
                x=breakdown_df['Generator'],
                y=breakdown_df['Non_Fuel_Variable'],
                marker_color='#2ca02c'
            ))
            
            fig.add_trace(go.Bar(
                name='Fixed Cost',
                x=breakdown_df['Generator'],
                y=breakdown_df['Fixed_Cost'],
                marker_color='#d62728'
            ))
            
            # Update layout for stacked bar chart
            fig.update_layout(
                title=f'Generator LCOE Breakdown - {selected_scenario}',
                xaxis_title='Generator',
                yaxis_title='Levelized Cost ($/MWh)',
                barmode='stack',
                height=600,
                xaxis={'tickangle': 45},
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Create second plot showing annual generation
            fig_gen = go.Figure()
            
            # Convert MWh to GWh for better readability
            generation_gwh = breakdown_df['Generation_MWh'] / 1000
            
            # Use same ordering as first plot (by Total LCOE, highest to lowest)
            generation_df = breakdown_df.copy()
            generation_df['Generation_GWh'] = generation_gwh
            
            fig_gen.add_trace(go.Bar(
                x=generation_df['Generator'],
                y=generation_df['Generation_GWh'],
                marker_color='steelblue',
                name='Annual Generation'
            ))
            
            # Update layout for generation chart
            fig_gen.update_layout(
                title=f'Annual Generation by Generator - {selected_scenario}',
                xaxis_title='Generator',
                yaxis_title='Annual Generation (GWh)',
                height=500,
                xaxis={'tickangle': 45},
                showlegend=False
            )
            
            st.plotly_chart(fig_gen, use_container_width=True)
            
            # Create third plot showing annual capacity factor
            fig_cf = go.Figure()
            
            # Use same ordering as first plot (by Total LCOE, highest to lowest)
            capacity_factor_df = breakdown_df.copy()
            
            fig_cf.add_trace(go.Bar(
                x=capacity_factor_df['Generator'],
                y=capacity_factor_df['Capacity_Factor_pct'],
                marker_color='orange',
                name='Capacity Factor'
            ))
            
            # Update layout for capacity factor chart
            fig_cf.update_layout(
                title=f'Annual Capacity Factor by Generator - {selected_scenario}',
                xaxis_title='Generator',
                yaxis_title='Capacity Factor (%)',
                height=500,
                xaxis={'tickangle': 45},
                showlegend=False
            )
            
            st.plotly_chart(fig_cf, use_container_width=True)
            
            # Show detailed breakdown table
            with st.expander("📊 Detailed Generator Cost Breakdown"):
                # Format the dataframe for display
                display_df = breakdown_df.copy()
                display_df['Generation_MWh'] = display_df['Generation_MWh'].round(0).astype(int)
                display_df['Capacity_MW'] = display_df['Capacity_MW'].round(1)
                display_df['Capacity_Factor_pct'] = display_df['Capacity_Factor_pct'].round(1)
                for col in ['Capital_Cost', 'Fuel_Cost', 'Non_Fuel_Variable', 'Fixed_Cost', 'Total_LCOE']:
                    display_df[col] = display_df[col].round(2)
                
                # Rename columns for display
                display_df = display_df.rename(columns={
                    'Generation_MWh': 'Generation (MWh)',
                    'Capacity_MW': 'Capacity (MW)',
                    'Capacity_Factor_pct': 'Capacity Factor (%)',
                    'Capital_Cost': 'Capital ($/MWh)',
                    'Fuel_Cost': 'Fuel ($/MWh)',
                    'Non_Fuel_Variable': 'Non-Fuel Var ($/MWh)',
                    'Fixed_Cost': 'Fixed ($/MWh)',
                    'Total_LCOE': 'Total LCOE ($/MWh)'
                })
                
                st.dataframe(display_df, use_container_width=True)
        else:
            st.warning("No generators with positive generation found for this scenario.")
    else:
        st.error("Selected scenario not found in data.")

# Add final spacing to ensure content is accessible
st.markdown("")
st.markdown("")
st.markdown("")