import os

filepath = 'frontend/dashboard.py'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

split_idx = -1
for i, line in enumerate(lines):
    if "main_col, chat_col = st.columns" in line:
        split_idx = i
        break

if split_idx != -1:
    top_half = lines[:split_idx]
else:
    top_half = lines

bottom_half = """        # 3. KPI Metrics Section
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
    # Use st.container(border=True) to float at bottom in streamlit? 
    # Actually st.chat_input is natively sticky at the bottom
    prompt = st.chat_input("💬 Ask a question or type 'plot [graph type]...' to generate a chart")
    if prompt:
        is_graph_req = any(w in prompt.lower() for w in ['plot', 'draw', 'graph', 'chart', 'visualize', 'pie', 'bar', 'trend', 'scatter'])
        
        with st.spinner("Copilot is analyzing..."):
            import sys
            import requests
            root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            if root_path not in sys.path:
                sys.path.append(root_path)
            
            if is_graph_req:
                from backend.services.llm_service import generate_graph_config
                config = generate_graph_config(prompt, list(filtered_df.columns))
                if config and not config.get("error"):
                    st.session_state.custom_graphs.append({
                        "query": prompt,
                        "config": config
                    })
                    save_custom_config(st.session_state.custom_graphs)
                    st.rerun()
                else:
                    st.toast("❌ AI couldn't generate a valid chart configuration for this query.", icon="🚨")
            else:
                from backend.services.llm_service import generate_pandas_filter, OLLAMA_API_URL, MODEL_NAME
                @st.dialog("🤖 AI Answer")
                def show_answer(answer_text):
                    st.markdown(answer_text)
                    
                filter_query = generate_pandas_filter(prompt, list(filtered_df.columns))
                if filter_query and filter_query.lower() != "none":
                    try:
                        ans_df = filtered_df.query(filter_query)
                        count = len(ans_df)
                        ans_text = f"**Question:** {prompt}\\n\\n**Result:** Found **{count}** records matching your query."
                        show_answer(ans_text)
                    except Exception as e:
                        st.toast(f"Failed to filter data: {e}")
                else:
                    summary_stats = f"Total vendors: {len(filtered_df)}, High Risk: {len(filtered_df[filtered_df['Risk Level']=='High'])}, Medium Risk: {len(filtered_df[filtered_df['Risk Level']=='Medium'])}"
                    gen_prompt = f"Given data stats: {summary_stats}. Answer user query concisely: {prompt}"
                    payload = {"model": MODEL_NAME, "prompt": gen_prompt, "stream": False}
                    try:
                        res = requests.post(OLLAMA_API_URL, json=payload, timeout=30)
                        ans_text = f"**Question:** {prompt}\\n\\n**Result:** {res.json().get('response', '')}"
                        show_answer(ans_text)
                    except Exception:
                        st.toast("Failed to connect to AI engine.")

if "drilldown_pending" in st.session_state:
    dd = st.session_state.pop("drilldown_pending")
    show_drilldown(dd["title"], dd["subset"])
"""

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(top_half)
    f.write(bottom_half)
print('Done!')
