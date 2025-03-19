import streamlit as st
import pandas as pd
import time
from process import metrics, show_status_message, valid_metrics, sign_in, split_into_chunks, build_gql_query, execute_graphql_query, fetched_data, charts
import os
from dotenv import load_dotenv

load_dotenv()
scope = os.getenv('SCOPE')
endpoint = os.getenv('ENDPOINT')



st.set_page_config(
    page_title="Phone Number Validation",
    page_icon="📞",
    layout="wide"
)

if "headers" not in st.session_state:
    st.session_state.headers = None

sign_in_button = st.button('Sign In')

if sign_in_button:
    st.session_state.headers = sign_in(scope)

if "file_uploaded" not in st.session_state:
    st.session_state.file_uploaded = False
# Sidebar
with st.sidebar:
    st.image("https://www.blueirissoft.com/images/Blueirissoft-logo-white.png")
    st.title('Leads Contact Filter')
    st.divider()
    info_placeholder = st.empty()  
    info_placeholder.info("Upload a CSV or Excel file containing phone numbers")

    file = st.file_uploader("Upload a CSV or Excel file", type=["csv", "xlsx", "xls"], label_visibility='collapsed')

    if file is not None:
        info_placeholder.empty()  
        
        if not st.session_state.file_uploaded:  
            try:
                # Load the file
                if file.name.endswith(".csv"):
                    df = pd.read_csv(file)
                else:
                    df = pd.read_excel(file)

                if df.shape[0] != 0:
                    st.toast("✅ File uploaded successfully!", icon="✅")  #
                    time.sleep(1)  
                    st.session_state.file_uploaded = True  

                else:
                    st.warning("No Data in the file!")
                    df = None  

            except Exception as e:
                st.error(f"Error: {e}")
                df = None
        else:
            # Load the file again for further interactions
            if file.name.endswith(".csv"):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)

        # Column selection dropdown in the sidebar
        if df is not None and not df.empty:
            st.divider()
            phone_col = st.selectbox("Select Phone Number Column", df.columns)



# Main section (outside the sidebar)
if file is not None and df is not None and not df.empty:
    # st.write("### Preview of Uploaded Data:")
    data = df[[phone_col]]

    col1, col2, col3, col4 = st.columns(4)
    total_numbers, unique_numbers = metrics(data, phone_col)
    valid = show_status_message(data, phone_col)
    phone_numbers = valid[["Phone Number"]]
    phone_numbers_list = phone_numbers['Phone Number'].drop_duplicates().tolist()
    phone_numbers = phone_numbers.rename(columns={"Phone Number": "phone_number"})
    val, cor = valid_metrics(valid.sample(frac=1, random_state=42))

    with st.expander("Show Data", expanded=True):
        st.write(f"Total Numbers {total_numbers:,}, Unique Numbers {unique_numbers:,}, Valid Numbers {val:,}, Corrupted Numbers {cor:,}")

        with st.container():
                
            tab1, tab2 = st.tabs(['Uploaded File', 'Cleaned Numbers'],)
            with tab1:        
                st.dataframe(df)
            with tab2:        
                st.dataframe(valid)
    
    fetch_data = st.button("Fetch Data")
    
    if fetch_data:
        if st.session_state['headers'] is None:
            st.error("Please Sign in")
        else:
            try:
                with st.spinner('Fetching data from API...'):
                    progress_bar = st.progress(0)
                    chunk_generator = split_into_chunks(phone_numbers_list, chunk_size=100)
                    dfs = []
                    total_chunks = (len(phone_numbers_list) + 99) // 100 
                    
                    for i, chunk in enumerate(chunk_generator):
                        query = build_gql_query(chunk)
                        df_chunk = execute_graphql_query(endpoint, query, st.session_state.headers)
                        dfs.append(df_chunk)
                        progress_bar.progress((i + 1) / total_chunks)
                        
                    progress_bar.progress(100)
                    time.sleep(0.5) 
                    progress_bar.empty() 
            
                    api_data = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
                    final_df = pd.merge(phone_numbers, api_data, on='phone_number', how='left')
                    phone_count, unique_count, registered_count, ftd_count = fetched_data(final_df)

                    final_df.rename(columns={
                        'phone_number': 'Phone Number',
                        'platform_id': 'Platform ID',
                        'brand': 'Brand',
                        'sub_brand': 'Sub Brand',
                        'registration_date': 'Registration Date',
                        'ftd_date': 'FTD Date',
                        'ftd_amount': 'FTD Amount',
                        'total_calls': 'Total Calls',
                        'answered_call': 'Answered Calls',
                        'first_call_date': 'First Call',                   
                        'last_call_date': 'Last Call',                   
                        'first_answered_call_date': 'First Answered',                   
                        'last_answered_call_date': 'Last Answered'                   
                        },inplace=True)
                    
                    brands_stat = charts(final_df)
                    st.session_state["final_df"] = final_df
                    
                with st.container(border=True):
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric('Total Numbers', phone_count, border=True)
                    with col2:
                        st.metric('Unique Numbers', unique_count, border=True)
                    with col3:
                        st.metric('Registered Players', registered_count, border=True)
                    with col4:
                        st.metric('FTD Players', ftd_count, border=True)
                    st.dataframe(final_df)

            except Exception as e:
                st.error(f"Error fetching data, {e}")
