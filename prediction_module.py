import torch
import torch.nn as nn
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class GRUModel(nn.Module):
    def __init__(self, input_dim, feature_dim=32, hidden_dim=64, output_len=1):
        super().__init__()
        self.features = nn.Sequential(
            nn.Linear(input_dim, feature_dim),
            nn.Dropout(0.2),
            nn.ReLU(),
            nn.Linear(feature_dim, feature_dim),
            nn.Dropout(0.2),
            nn.ReLU()
        )
        self.gru = nn.GRU(feature_dim, hidden_dim, batch_first=True, dropout=0.2)
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim, output_len),
            nn.Sigmoid()
        )

    def forward(self, x):
        output, _ = self.gru(self.features(x))
        last = output[:, -1, :]
        return self.fc(last)


def load_model(model_path='gru_bike_prediction_model.pt', device='cpu'):
    """Load the trained GRU model."""
    # The model expects 7 features: ratio, lon, lat, hour_sin, hour_cos, weekday_num, is_weekend
    model = GRUModel(input_dim=7, feature_dim=256, hidden_dim=256, output_len=144)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.to(device)
    model.eval()
    return model


def prepare_features(df_row, future_time):
    """Prepare features for prediction at a given future time."""
    # Extract time features
    hour = future_time.hour
    hour_sin = np.sin(2 * np.pi * hour / 24)
    hour_cos = np.cos(2 * np.pi * hour / 24)
    
    weekday_num = future_time.weekday()
    is_weekend = 1.0 if weekday_num >= 5 else 0.0
    
    # Return feature vector
    return np.array([
        df_row['available_to_total_ratio'],
        df_row['geo_point_2d.lon'],
        df_row['geo_point_2d.lat'],
        hour_sin,
        hour_cos,
        weekday_num,
        is_weekend
    ], dtype=np.float32)


def predict_station(model, df_station, prediction_hours=24, seq_len=24, device='cpu'):
    """
    Predict bike availability for a station at future time points.
    
    Args:
        model: Trained GRU model
        df_station: DataFrame with historical data for one station (sorted by time)
        prediction_hours: Number of hours into the future to predict
        seq_len: Sequence length used during training
        device: Device to run predictions on
        
    Returns:
        Dictionary with predictions for each hour
    """
    # Get the last seq_len records as context
    if len(df_station) < seq_len:
        # Pad with the first row if we don't have enough data
        needed = seq_len - len(df_station)
        padding = pd.DataFrame([df_station.iloc[0].to_dict()] * needed)
        df_station = pd.concat([padding, df_station], ignore_index=True)
    
    df_hist = df_station.tail(seq_len).copy()
    
    # Get the last timestamp
    last_time = pd.to_datetime(df_hist.iloc[-1]['updated_at'])
    
    # Prepare input sequence
    features = ["ratio", "geo_point_2d.lon", "geo_point_2d.lat", "hour_sin", "hour_cos", "weekday_num", "is_weekend"]
    
    # Calculate time features for historical data
    for idx in df_hist.index:
        time = pd.to_datetime(df_hist.loc[idx, 'updated_at'])
        hour = time.hour
        df_hist.loc[idx, 'hour_sin'] = np.sin(2 * np.pi * hour / 24)
        df_hist.loc[idx, 'hour_cos'] = np.cos(2 * np.pi * hour / 24)
        df_hist.loc[idx, 'weekday_num'] = float(time.weekday())
        df_hist.loc[idx, 'is_weekend'] = 1.0 if time.weekday() >= 5 else 0.0
    
    # Rename ratio column if needed
    if 'available_to_total_ratio' in df_hist.columns:
        df_hist['ratio'] = df_hist['available_to_total_ratio']
    
    # Ensure all columns are numeric and handle any remaining object types
    for col in features:
        df_hist[col] = pd.to_numeric(df_hist[col], errors='coerce')
    
    # Fill any NaN values with 0
    df_hist[features] = df_hist[features].fillna(0)
    
    # Get feature values and convert to float32
    X_window = df_hist[features].values.astype(np.float32)
    X_window = torch.tensor(X_window, dtype=torch.float32).unsqueeze(0)
    X_window = X_window.to(device)
    
    # Get total bikes (convert to numeric safely)
    last_row = df_hist.iloc[-1]
    total_bikes = pd.to_numeric(last_row.get('total', 0), errors='coerce')
    if pd.isna(total_bikes):
        total_bikes = 0
    
    predictions = []
    
    model.eval()
    with torch.no_grad():
        # Model outputs 144 predictions (one every 10 minutes for 24 hours)
        pred_ratios = model(X_window).cpu().numpy().flatten()
        
        # Extract hourly predictions (every 6th prediction since 6*10min = 1 hour)
        # Predictions at indices: 5, 11, 17, 23, ... (0-indexed, so +1h is at index 5)
        max_hours = min(int(prediction_hours), 24)
        for hour in range(1, max_hours + 1):
            # Index for this hour: (hour * 6) - 1 (since we want the prediction AT that hour)
            idx = (hour * 6) - 1
            if idx >= len(pred_ratios):
                break
                
            future_time = last_time + timedelta(hours=hour)
            pred_ratio = float(pred_ratios[idx])
            
            predictions.append({
                'hour': hour,
                'time': future_time.strftime('%Y-%m-%d %H:%M'),
                'time_label': future_time.strftime('%H:%M'),
                'predicted_ratio': pred_ratio,
                'predicted_bikes': int(pred_ratio * total_bikes) if total_bikes > 0 else None
            })
    
    return predictions


def get_predictions_for_all_stations(agg_csv_path='agg.csv', model_path='gru_bike_prediction_model.pt', 
                                     prediction_hours=24, seq_len=24):
    """
    Load data and make predictions for all stations.
    
    Returns:
        Dictionary mapping station number to predictions
    """
    device = torch.device('cpu')  # Use CPU for simplicity
    
    # Load model
    try:
        model = load_model(model_path, device)
    except Exception as e:
        print(f"Error loading model: {e}")
        return {}
    
    # Load aggregated data
    try:
        df = pd.read_csv(agg_csv_path)
        df['updated_at'] = pd.to_datetime(df['updated_at'])
        df = df.sort_values(['number', 'updated_at'])
    except Exception as e:
        print(f"Error loading data: {e}")
        return {}
    
    # Get predictions for each station
    all_predictions = {}
    
    for station_num in df['number'].unique():
        df_station = df[df['number'] == station_num].copy()
        
        try:
            predictions = predict_station(model, df_station, prediction_hours, seq_len, device)
            all_predictions[int(station_num)] = predictions
        except Exception as e:
            print(f"Error predicting station {station_num}: {e}")
            all_predictions[int(station_num)] = []
    
    return all_predictions
