import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os

# Configuration & Theming
st.set_page_config(page_title="TPRM Risk Dashboard", page_icon="🛡️", layout="wide")

st.title("🛡️ Third-Party Risk Management (TPRM) Dashboard")
st.markdown("Upload assessment data to automatically generate dynamic real-time risk classification and insights.")

REQUIRED_COLUMNS = [
    "Legal Name",
    "Formal InfoSec Policy",
    "Security Breach Last 2 Years",
    "Regulatory Compliance",
    "Business Continuity Plan",
    "Incident Response Plan",
    "Cyber Insurance"
]

CONFIG_FILE = "custom_dashboard_config.json"

def load_custom_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_custom_config(graphs):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(graphs, f)

@st.cache_data
def load_and_process_data(file):
    try:
        df = pd.read_excel(file)
    except Exception as e:
        return None, f"Failed to read file: {e}"
        
    # Validate Columns
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        return None, f"Missing required columns: {', '.join(missing_cols)}"
        
    df = apply_risk_classification(df)
    return df, None

def apply_risk_classification(df):
    def calculate_risk(row):
        # Normalize text to lower case to make matching robust
        breach = str(row.get('Security Breach Last 2 Years', '')).lower()
        infosec = str(row.get('Formal InfoSec Policy', '')).lower()
        ir_plan = str(row.get('Incident Response Plan', '')).lower()
        bcp = str(row.get('Business Continuity Plan', '')).lower()
        insurance = str(row.get('Cyber Insurance', '')).lower()

        # HIGH RISK RULES:
        # Security breach exists (not none/no) OR No InfoSec Policy OR No Incident Response Plan
        has_breach = breach not in ['none', 'no', 'nan', '']
        if has_breach or infosec == 'no' or ir_plan == 'no':
            return "High"
            
        # MEDIUM RISK RULES:
        # Missing BCP OR No Cyber Insurance
        if bcp == 'no' or insurance == 'no':
            return "Medium"
            
        # OTHERWISE
        return "Low"
        
    df['Risk Level'] = df.apply(calculate_risk, axis=1)
    
    # Custom sort order for Risk Level
    risk_order = ['High', 'Medium', 'Low']
    df['Risk Level'] = pd.Categorical(df['Risk Level'], categories=risk_order, ordered=True)
    return df

def generate_csv_download(df):
    return df.to_csv(index=False).encode('utf-8')

@st.dialog("🔍 Data Drill-Down", width="large")
def show_drilldown(title, subset_df):
    st.markdown(f"**{title}**")
    st.dataframe(subset_df, use_container_width=True)
    st.download_button(
        label="📥 Download This Selection",
        data=generate_csv_download(subset_df),
        file_name="drilldown_export.csv",
        mime="text/csv"
    )

if 'chart_key_versions' not in st.session_state:
    st.session_state.chart_key_versions = {}

def get_chart_key(base_key):
    version = st.session_state.chart_key_versions.get(base_key, 0)
    return f"{base_key}_v{version}"

def handle_chart_click(base_key, df, title_func, filter_func):
    actual_key = get_chart_key(base_key)
    current_sel = st.session_state.get(actual_key)
    
    if current_sel and current_sel.get("selection", {}).get("points"):
        point = current_sel["selection"]["points"][0]
        cat_val = point.get("x") or point.get("label") or point.get("y")
        if cat_val is not None:
            # Force chart to remount with a new key so it visually loses selection
            st.session_state.chart_key_versions[base_key] = st.session_state.chart_key_versions.get(base_key, 0) + 1
            
            # Save the drill-down payload into session state and rerun
            subset = filter_func(df, cat_val)
            st.session_state.drilldown_pending = {
                "title": title_func(cat_val),
                "subset": subset
            }
            
            # Clean up the exact old key selection from Streamlit internal dictionary
            if actual_key in st.session_state:
                del st.session_state[actual_key]
                
            # Trigger a full top-to-bottom script execution
            st.rerun()

def generate_custom_chart_figure(df, config):
    x_col = config.get("x_col")
    y_col = config.get("y_col") 
    aggr = config.get("aggregation", "count")
    graph_type = config.get("graph_type", "bar")
    
    # If the LLM generates a literal None/null for aggregation, fallback to count
    if not aggr or str(aggr).lower() == 'none':
        aggr = 'count'
    
    if not x_col or x_col not in df.columns:
        raise ValueError(f"Valid 'x_col' required (got {x_col}).")
        
    if aggr == 'count':
        grouped = df.groupby(x_col).size().reset_index(name='count')
        y_col_out = 'count'
    else:
        if not y_col or y_col not in df.columns:
            raise ValueError(f"Valid 'y_col' required for aggregation '{aggr}'")
        # Ensure y_col is numeric if we're aggregating
        grouped = df.groupby(x_col)[y_col].agg(aggr).reset_index()
        y_col_out = y_col
        
    if graph_type == "line":
        return px.line(grouped, x=x_col, y=y_col_out, title=f"{y_col_out} by {x_col}")
    elif graph_type == "pie":
        return px.pie(grouped, names=x_col, values=y_col_out, title=f"{y_col_out} by {x_col}")
    else:
        return px.bar(grouped, x=x_col, y=y_col_out, title=f"{y_col_out} by {x_col}")

with st.sidebar:
    st.header("📂 Data Upload")
    uploaded_file = st.file_uploader("Upload TPRM Excel Data", type=["xls", "xlsx"])
    
    st.markdown("---")
    with st.expander("⚙️ Settings", expanded=False):
        gemini_key = st.text_input(
            "Gemini API Key",
            value=st.session_state.get("gemini_api_key", ""),
            type="password",
            placeholder="Enter your Gemini API key",
            help="Stored in memory only. Resets when you refresh the page."
        )
        if gemini_key != st.session_state.get("gemini_api_key", ""):
            st.session_state.gemini_api_key = gemini_key
            st.success("API key saved for this session!")
    
if uploaded_file is None:
    st.info("👈 Please upload the TPRM Assessment Excel file in the sidebar to view the dashboard.")
    st.image("https://images.unsplash.com/photo-1551288049-bebda4e38f71?fm=jpg&q=80&w=2000&blend=000000&blend-mode=overlay&blend-alpha=30", use_column_width=True)
else:
    # 1. Automatic Load & Cache
    with st.spinner("Processing Risk Data..."):
        df, error = load_and_process_data(uploaded_file)
        
    if error:
        st.error(error)
    else:
        st.success("File processed successfully.")
        
        # 2. Sidebar Filtering
        st.sidebar.header("🔍 Filters")
        
        # Search Vendor
        search_vendor = st.sidebar.text_input("Search by Vendor Name")
        
        # Risk Levels
        risk_filter = st.sidebar.multiselect(
            "Filter by Risk Level", 
            options=["High", "Medium", "Low"], 
            default=["High", "Medium", "Low"]
        )
        
        # Compliance Framework
        # Explode comma-separated compliance values to get a unique list for the filter
        all_frameworks = []
        for x in df['Regulatory Compliance'].dropna():
            all_frameworks.extend([item.strip() for item in str(x).split(',')])
        unique_frameworks = sorted(list(set(all_frameworks)))
        
        compliance_filter = st.sidebar.multiselect(
            "Filter by Compliance Framework",
            options=unique_frameworks
        )
        
        # Apply Filters to Dataframe
        filtered_df = df.copy()
        if search_vendor:
            filtered_df = filtered_df[filtered_df['Legal Name'].str.contains(search_vendor, case=False, na=False)]
        if risk_filter:
            filtered_df = filtered_df[filtered_df['Risk Level'].isin(risk_filter)]
        if compliance_filter:
            # Vendor must have at least one of the selected frameworks
            pattern = '|'.join(compliance_filter)
            filtered_df = filtered_df[filtered_df['Regulatory Compliance'].str.contains(pattern, case=False, na=False)]

        # 3. KPI Metrics Section
        st.markdown("---")
        st.subheader("📊 Top-Level KPIs")
        
        total_vendors = len(filtered_df)
        
        breach_condition = ~filtered_df['Security Breach Last 2 Years'].astype(str).str.lower().isin(['none', 'nan', 'no', ''])
        vendors_w_breaches = filtered_df[breach_condition].shape[0]
        
        no_infosec = filtered_df[filtered_df['Formal InfoSec Policy'].astype(str).str.lower() == 'no'].shape[0]
        no_bcp = filtered_df[filtered_df['Business Continuity Plan'].astype(str).str.lower() == 'no'].shape[0]
        no_ir = filtered_df[filtered_df['Incident Response Plan'].astype(str).str.lower() == 'no'].shape[0]
        no_insurance = filtered_df[filtered_df['Cyber Insurance'].astype(str).str.lower() == 'no'].shape[0]

        m1, m2, m3 = st.columns(3)
        m1.metric("Total Vendors", total_vendors)
        m2.metric("Vendors with Security Breaches", vendors_w_breaches, delta_color="inverse", help="Breaches in last 2 years")
        m3.metric("Vendors Missing InfoSec Policy", no_infosec, delta_color="inverse")
        
        m4, m5, m6 = st.columns(3)
        m4.metric("Vendors Missing Incident Response", no_ir, delta_color="inverse")
        m5.metric("Vendors Missing BCP", no_bcp, delta_color="inverse")
        m6.metric("Vendors Missing Cyber Insurance", no_insurance, delta_color="inverse")

        # 4. Visualizations
        st.markdown("---")
        st.subheader("📈 Risk & Compliance Visualizations")
        
        if len(filtered_df) > 0:
            c1, c2 = st.columns(2)
            
            with c1:
                risk_counts = filtered_df['Risk Level'].value_counts().reset_index()
                risk_counts.columns = ['Risk Level', 'Count']
                fig_risk = px.bar(
                    risk_counts, 
                    x='Risk Level', 
                    y='Count', 
                    title="Risk Level Distribution",
                    color='Risk Level',
                    color_discrete_map={"High": "red", "Medium": "orange", "Low": "green"}
                )
                st.plotly_chart(fig_risk, use_container_width=True, on_select="rerun", selection_mode="points", key=get_chart_key("risk_chart"))
                handle_chart_click(
                    "risk_chart", filtered_df, 
                    lambda val: f"Vendors with Risk Level: {val}", 
                    lambda df, val: df[df['Risk Level'] == val]
                )
                
            with c2:
                comp_counts = pd.Series(all_frameworks).value_counts().reset_index()
                comp_counts.columns = ['Framework', 'Count']
                fig_comp = px.bar(
                    comp_counts.head(10), 
                    x='Count', 
                    y='Framework', 
                    title="Top Compliance Frameworks",
                    orientation='h',
                    color_discrete_sequence=['#1f77b4']
                )
                fig_comp.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_comp, use_container_width=True, on_select="rerun", selection_mode="points", key=get_chart_key("comp_chart"))
                handle_chart_click(
                    "comp_chart", filtered_df, 
                    lambda val: f"Vendors compliant with: {val}", 
                    lambda df, val: df[df['Regulatory Compliance'].str.contains(str(val), case=False, na=False)]
                )
            
            st.markdown("### Missing Critical Controls")
            missing_controls_data = {
                'Control': ['InfoSec Policy', 'BCP', 'Incident Response', 'Cyber Insurance'],
                'Vendors Missing': [no_infosec, no_bcp, no_ir, no_insurance]
            }
            fig_missing = px.bar(
                missing_controls_data,
                x='Control',
                y='Vendors Missing',
                title="Vendors Missing Key Controls",
                color='Control',
                text='Vendors Missing'
            )
            st.plotly_chart(fig_missing, use_container_width=True, on_select="rerun", selection_mode="points", key=get_chart_key("missing_chart"))
            
            def filter_missing(df, val):
                if val == "InfoSec Policy": return df[df['Formal InfoSec Policy'].astype(str).str.lower() == 'no']
                if val == "BCP": return df[df['Business Continuity Plan'].astype(str).str.lower() == 'no']
                if val == "Incident Response": return df[df['Incident Response Plan'].astype(str).str.lower() == 'no']
                if val == "Cyber Insurance": return df[df['Cyber Insurance'].astype(str).str.lower() == 'no']
                return df
                
            handle_chart_click(
                "missing_chart", filtered_df, 
                lambda val: f"Vendors Missing: {val}", 
                filter_missing
            )

            if 'Assessment Date' in filtered_df.columns:
                st.markdown("### Assessments Over Time (Trend)")
                trend_df = filtered_df.copy()
                trend_df['Assessment Date'] = pd.to_datetime(trend_df['Assessment Date'], errors='coerce')
                trend_df['Month'] = trend_df['Assessment Date'].dt.to_period('M').astype(str)
                trend_df = trend_df[trend_df['Month'] != 'NaT']
                
                monthly_counts = trend_df.groupby('Month').size().reset_index(name='Assessment Count')
                monthly_counts = monthly_counts.sort_values('Month')
                
                fig_trend = px.line(
                    monthly_counts,
                    x='Month',
                    y='Assessment Count',
                    title="Assessment Volume Trend Over Time",
                    markers=True
                )
                st.plotly_chart(fig_trend, use_container_width=True, on_select="rerun", selection_mode="points", key=get_chart_key("trend_chart"))
                handle_chart_click(
                    "trend_chart", trend_df, 
                    lambda val: f"Assessments in {str(val)[:7]}", 
                    lambda df, val: df[df['Month'].str.startswith(str(val)[:7])]
                )

            # 5. Dynamic AI Content Render
            st.markdown("---")
            
            if 'custom_graphs' not in st.session_state:
                st.session_state.custom_graphs = load_custom_config()
                
            if len(st.session_state.custom_graphs) > 0:
                st.subheader("📊 AI Generated Custom Charts")
                for i, graph_item in enumerate(st.session_state.custom_graphs):
                    st.markdown(f"**Query:** _{graph_item['query']}_")
                    col1, col2, col3, col4 = st.columns([0.5, 0.5, 0.5, 8.5])
                    with col1:
                        if st.button("⬆️", key=f"up_{i}", disabled=(i == 0)):
                            st.session_state.custom_graphs[i], st.session_state.custom_graphs[i-1] = st.session_state.custom_graphs[i-1], st.session_state.custom_graphs[i]
                            save_custom_config(st.session_state.custom_graphs)
                            st.rerun()
                    with col2:
                        if st.button("⬇️", key=f"down_{i}", disabled=(i == len(st.session_state.custom_graphs) - 1)):
                            st.session_state.custom_graphs[i], st.session_state.custom_graphs[i+1] = st.session_state.custom_graphs[i+1], st.session_state.custom_graphs[i]
                            save_custom_config(st.session_state.custom_graphs)
                            st.rerun()
                    with col3:
                        if st.button("❌", key=f"del_{i}"):
                            st.session_state.custom_graphs.pop(i)
                            save_custom_config(st.session_state.custom_graphs)
                            st.rerun()
                            
                    try:
                        fig_custom = generate_custom_chart_figure(filtered_df, graph_item['config'])
                        base_key = f"custom_chart_{i}"
                        st.plotly_chart(fig_custom, use_container_width=True, on_select="rerun", selection_mode="points", key=get_chart_key(base_key))
                        
                        x_col = graph_item['config'].get('x_col')
                        handle_chart_click(
                            base_key, filtered_df, 
                            lambda val, xc=x_col: f"Drill-down: {xc} = {val}", 
                            lambda df, val, xc=x_col: df[df[xc].astype(str) == str(val)]
                        )
                    except Exception as e:
                        st.error(f"Error rendering chart: {e}")
            
            # 6. Drill-Down Section
            st.markdown("---")
            st.subheader("🔍 High Risk Vendors Drill-Down")
            
            high_risk_df = filtered_df[filtered_df['Risk Level'] == 'High']
            if not high_risk_df.empty:
                st.dataframe(high_risk_df[['Legal Name', 'Primary Industry', 'Security Breach Last 2 Years', 'Formal InfoSec Policy', 'Incident Response Plan']], use_container_width=True)
            else:
                st.success("No High Risk vendors match the current filters! 🎉")
            
            st.markdown("### Raw Dataset Preview")
            with st.expander("Expand to view filtered dataset"):
                st.dataframe(filtered_df, use_container_width=True)
                
            csv_data = generate_csv_download(filtered_df)
            st.download_button(
                label="📥 Download Filtered Data as CSV",
                data=csv_data,
                file_name="tprm_dashboard_export.csv",
                mime="text/csv"
            )
            
            st.markdown("<br><br><br><br>", unsafe_allow_html=True) # padding for chat input
        else:
            st.warning("No vendors match the selected filters.")

# Unified Sticky Bottom Copilot
if uploaded_file is not None and not error:
    if "copilot_history" not in st.session_state:
        st.session_state.copilot_history = []
    
    # Render persistent chat history
    if st.session_state.copilot_history:
        with st.expander("💬 **Copilot Chat History** (click to expand)", expanded=True):
            for msg in st.session_state.copilot_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
    
    prompt = st.chat_input("💬 Ask a question or type 'plot [graph type]...' to generate a chart")
    if prompt:
        st.session_state.copilot_history.append({"role": "user", "content": prompt})
        is_graph_req = any(w in prompt.lower() for w in ['plot', 'draw', 'graph', 'chart', 'visualize', 'pie', 'bar', 'trend', 'scatter'])
        
        with st.spinner("Copilot is analyzing..."):
            import sys
            root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            if root_path not in sys.path:
                sys.path.append(root_path)
            
            _api_key = st.session_state.get("gemini_api_key", "")
            
            if is_graph_req:
                from backend.services.llm_service import generate_graph_config
                config = generate_graph_config(prompt, list(filtered_df.columns), api_key=_api_key)
                if config and not config.get("error"):
                    st.session_state.custom_graphs.append({
                        "query": prompt,
                        "config": config
                    })
                    save_custom_config(st.session_state.custom_graphs)
                    st.session_state.copilot_history.append({"role": "assistant", "content": f"📊 Chart generated for: *{prompt}*"})
                    st.rerun()
                else:
                    reply = "❌ AI couldn't generate a valid chart configuration for this query."
                    st.session_state.copilot_history.append({"role": "assistant", "content": reply})
                    st.rerun()
            else:
                from backend.services.llm_service import generate_pandas_filter, call_generative
                    
                filter_query = generate_pandas_filter(prompt, list(filtered_df.columns), api_key=_api_key)
                use_generative = True
                ans_text = ""
                
                if filter_query and filter_query.lower() != "none":
                    try:
                        ans_df = filtered_df.query(filter_query)
                        count = len(ans_df)
                        ans_text = f"Found **{count}** records matching your query."
                        use_generative = False
                    except Exception:
                        use_generative = True
                
                if use_generative:
                    sample_csv = filtered_df.head(20).to_csv(index=False)
                    summary_stats = f"Total vendors: {len(filtered_df)}, High Risk: {len(filtered_df[filtered_df['Risk Level']=='High'])}, Medium Risk: {len(filtered_df[filtered_df['Risk Level']=='Medium'])}, Low Risk: {len(filtered_df[filtered_df['Risk Level']=='Low'])}"
                    gen_prompt = f"You are a data analyst. Here are some stats about the dataset:\n{summary_stats}\n\nHere is a sample of the data:\n{sample_csv}\n\nUser question: {prompt}\n\nProvide a clear, concise answer."
                    ans_text = call_generative(gen_prompt, api_key=_api_key, timeout=60)
                
                st.session_state.copilot_history.append({"role": "assistant", "content": ans_text})
                st.rerun()

if "drilldown_pending" in st.session_state:
    dd = st.session_state.pop("drilldown_pending")
    show_drilldown(dd["title"], dd["subset"])
