import streamlit as st
import pandas as pd
import re
from azure.identity import InteractiveBrowserCredential
import requests
def metrics(df, phone_column):
    total_numbers = df[phone_column].count()
    unique_numbers = df[phone_column].nunique()
    return total_numbers, unique_numbers

def validate_phone_number(phone):
    if pd.isna(phone):
        return {"Status": "Null", "Phone Number": None}
    
    phone = str(phone)
    
    cleaned_phone = re.sub(r'[\s\-\(\)]', '', phone)
    
    if not cleaned_phone.startswith('+'):
        if len(cleaned_phone) == 10:
            return {"Status": "Valid", "Phone Number": '+91' + cleaned_phone}
        elif len(cleaned_phone) == 12:
            return {"Status": "Valid", "Phone Number": '+' + cleaned_phone}
        else:
            return {"Status": "Corrupted", "Phone Number": cleaned_phone}
    else:
        if len(cleaned_phone) == 13:
            return {"Status": "Valid", "Phone Number": cleaned_phone}
        else:
            return {"Status": "Corrupted", "Phone Number": cleaned_phone}

def show_status_message(df, phone_column):
    data = df[[phone_column]]
    data[phone_column] = data.applymap(validate_phone_number)
    valid = data[phone_column].apply(pd.Series)
    return valid

def valid_metrics(valid_df):
    val = valid_df[valid_df["Status"] == "Valid"].shape[0]
    cor = valid_df[valid_df["Status"] == "Corrupted"].shape[0]
    return val, cor


def sign_in(scope):
  app = InteractiveBrowserCredential()
  result = app.get_token(scope)

  if not result.token:
      print('Error:', "Could not get access token")

  headers = {
  'Authorization': f'Bearer {result.token}',
  'Content-Type': 'application/json'
  }
  return headers

def split_into_chunks(phone_numbers, chunk_size=100):
    """Split a list of phone numbers into chunks of specified size."""
    for i in range(0, len(phone_numbers), chunk_size):
        yield phone_numbers[i:i + chunk_size]


def build_gql_query(phone_chunk):
    """Build a GraphQL query for a chunk of phone numbers"""
    or_clauses = ",".join([
        f'{{ phone_number: {{ eq: "{num}" }} }}' 
        for num in phone_chunk
    ])
    return f"""
    query {{
      user_datas(filter: {{ or: [{or_clauses}] }}) {{
        items {{
          platform_id
          brand
          sub_brand
          phone_number
          registration_date
          ftd_date
          ftd_amount
          total_calls
          answered_call
          first_call_date
          last_call_date
          first_answered_call_date
          last_answered_call_date

        }}
      }}
    }}
    """

def execute_graphql_query(endpoint, query, headers=None):
    try:
      response = requests.post(endpoint, json={'query': query}, headers=headers)
      response.raise_for_status()
      data = response.json()
      df = pd.DataFrame(data['data']['user_datas']['items'])
      return df
    except Exception as error:
      print(f"Query failed with error: {error}")


def fetched_data(df):
    phone_count = df['phone_number'].count()
    unique_count = df['phone_number'].nunique()
    duplicated_count = phone_count - unique_count
    registered_count = df['platform_id'].count()
    ftd_count = df['ftd_date'].count()
    
    return phone_count, unique_count, registered_count, ftd_count

def charts(df):
    brand_counts = df.groupby(['Brand', 'Sub Brand']).agg(
        {
            'Platform ID': 'count',
            'FTD Date': 'count'
        }
    ).reset_index().rename(columns={'Platform ID': 'Registered Players', 'FTD Date':'FTD Players'})
    return brand_counts

