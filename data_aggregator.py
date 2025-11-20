import json
import pandas as pd
import argparse
import os

def aggregate_data(input_files, output_file):
    # Aggregate JSON data into pandas dataframe
    aggregated_data = []

    for file_path in input_files:
        with open(file_path, 'r') as file:
            data = json.load(file)
            # Extract updated_at from filename
            file_name = os.path.basename(file_path)
            # Assuming filename format contains timestamp (e.g., data_2024-01-15.json)
            # Adjust the extraction logic based on your actual filename format
            updated_at = make_date_string(file_name.replace('.json', '').split('_')[-2:])
            
            for record in data['results']:
                record['updated_at'] = updated_at
            
            aggregated_data.extend(data['results'])
    
    print(f"Total records aggregated: {len(aggregated_data)}")
    print(f"Sample record: {aggregated_data[1] if aggregated_data else 'No data found'}")
    df = pd.json_normalize(aggregated_data)
    df.to_csv(output_file, index=False)

    return df

def make_date_string(strings):
    if len(strings) != 2:
        return ""
    return f'{strings[0][:4]}-{strings[0][4:6]}-{strings[0][6:]} {strings[1][0:2]}:{strings[1][2:4]}'

def get_json_files(input_dir):
    import os
    json_files = []
    for file_name in os.listdir(input_dir):
        if file_name.endswith('.json'):
            json_files.append(os.path.join(input_dir, file_name))
    return json_files

def check_missing_values(df):
    missing_values = df.isnull().sum()
    print("Missing values in each column:")
    print(missing_values)

def add_weekday_column(df):
    if 'updated_at' in df.columns:
        df['updated_at'] = pd.to_datetime(df['updated_at'], errors='coerce')
        df['weekday'] = df['updated_at'].dt.day_name()
    else:
        print("No 'updated_at' column found to add 'weekday'.")
    return df

def add_weekend_column(df):
    if 'updated_at' in df.columns:
        df['is_weekend'] = df['updated_at'].dt.dayofweek >= 5
    else:
        print("No 'updated_at' column found to add 'is_weekend'.")
    return df

def add_ratio_column(df):
    df['available_to_total_ratio'] = df.apply(
        lambda row: row['available'] / row['total'] if row['total'] > 0 else None, axis=1
    )
    return df

def add_time_column(df):
    if 'updated_at' in df.columns:
        df['time'] = df['updated_at'].dt.time
    else:
        print("No 'updated_at' column found to add 'time'.")
    return df

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aggregate JSON data files into a single CSV file.")
    parser.add_argument('--input-dir', help='Directory containing input JSON files to aggregate.')
    parser.add_argument('--output-file', default='aggregated_data.csv', help='Output CSV file path.')
    parser.add_argument('--address-df', required=False, help='Path to address dataframe CSV file.')
    parser.add_argument('--raw-only', action='store_true', help='If set, only generate raw aggregated data without additional processing.')
    args = parser.parse_args()

    input_files = get_json_files(args.input_dir)

    df = aggregate_data(input_files, f'raw_{args.output_file}')

    check_missing_values(df)
    if not args.raw_only:
        if args.address_df:
            address_df = pd.read_csv(args.address_df)
            df = df.merge(address_df, on='number', how='left', suffixes=('_old', ''))
            df = df.drop(columns=[col for col in df.columns if col.endswith('_old')])

        df = add_weekday_column(df)
        df = add_weekend_column(df)
        df = add_ratio_column(df)
        df = add_time_column(df)

        check_missing_values(df)

        df.to_csv(args.output_file, index=False)