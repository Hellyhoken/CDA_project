# -*- coding: utf-8 -*-
import pandas as pd
import json
import folium
import os
from prediction_module import get_predictions_for_all_stations


def load_data(file_path):
    """Load data from either CSV or JSON file."""
    if file_path.endswith('.csv'):
        # Load CSV file
        df = pd.read_csv(file_path)
        # Rename columns to standardized format
        data = []
        for _, row in df.iterrows():
            data.append({
                'address': row['address'],
                'number': row['number'],
                'lon': row['geo_point_2d.lon'],
                'lat': row['geo_point_2d.lat']
            })
        return data
    
    elif file_path.endswith('.json'):
        # Load JSON file
        with open(file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        # Extract data from results
        data = []
        for item in json_data.get('results', []):
            data.append({
                'address': item['address'],
                'number': item['number'],
                'lon': item['geo_point_2d']['lon'],
                'lat': item['geo_point_2d']['lat']
            })
        return data
    
    else:
        raise ValueError("File must be either .csv or .json")


def load_station_totals(agg_csv_path='agg.csv'):
    """Load total bike capacity for each station from aggregated data."""
    try:
        df = pd.read_csv(agg_csv_path)
        station_totals = df.groupby('number')['total'].last().to_dict()
        return station_totals
    except Exception as e:
        print(f"Error loading station totals: {e}")
        return {}


def load_current_ratios(agg_csv_path='agg.csv'):
    """Load latest availability ratio for each station."""
    try:
        df = pd.read_csv(agg_csv_path)
        if 'updated_at' in df.columns:
            df['updated_at'] = pd.to_datetime(df['updated_at'], errors='coerce')
            df = df.sort_values(['number', 'updated_at'])
        ratios = df.groupby('number')['available_to_total_ratio'].last().to_dict()
        # Coerce to float and clamp between 0 and 1
        cleaned = {}
        for k, v in ratios.items():
            try:
                f = float(v)
            except Exception:
                f = 0.0
            if f < 0: f = 0.0
            if f > 1: f = 1.0
            cleaned[int(k)] = f
        return cleaned
    except Exception as e:
        print(f"Error loading current ratios: {e}")
        return {}


def create_map(data, predictions=None, station_totals=None, station_current_ratios=None, output_file='map.html'):
    """Create a folium map with all the points."""
    if not data:
        print("No data to display")
        return
    
    if predictions is None:
        predictions = {}
    
    if station_totals is None:
        station_totals = {}
    if station_current_ratios is None:
        station_current_ratios = {}
    
    # Calculate the center of the map (average of all coordinates)
    avg_lat = sum(point['lat'] for point in data) / len(data)
    avg_lon = sum(point['lon'] for point in data) / len(data)
    
    # Create the map centered on the average coordinates
    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=13)
    
    # Prepare JSON data
    all_stations_json = json.dumps(data)
    predictions_json = json.dumps(predictions)
    station_totals_json = json.dumps(station_totals)
    station_current_ratios_json = json.dumps(station_current_ratios)
    
    # Add custom CSS and JavaScript for the side panel and pin controls
    custom_html = """
    <style>
        #side-panel {
            position: fixed;
            top: 0;
            right: -400px;
            width: 400px;
            height: 100%;
            background-color: white;
            box-shadow: -2px 0 5px rgba(0,0,0,0.3);
            transition: right 0.3s ease;
            z-index: 9999;
            overflow-y: auto;
            font-family: Arial, sans-serif;
        }
        #side-panel.open {
            right: 0;
        }
        #panel-header {
            background-color: #007bff;
            color: white;
            padding: 15px;
            position: sticky;
            top: 0;
            z-index: 10000;
        }
        #close-btn {
            float: right;
            background: none;
            border: none;
            color: white;
            font-size: 24px;
            cursor: pointer;
            padding: 0;
            margin: -5px 0;
        }
        #panel-content {
            padding: 20px;
        }
        .info-section {
            margin-bottom: 20px;
            padding-bottom: 20px;
            border-bottom: 1px solid #e0e0e0;
        }
        .info-section:last-child {
            border-bottom: none;
        }
        .info-label {
            font-weight: bold;
            color: #555;
            margin-bottom: 5px;
        }
        .info-value {
            color: #333;
            margin-bottom: 15px;
        }
        .prediction-placeholder {
            background-color: #f8f9fa;
            border: 2px dashed #dee2e6;
            border-radius: 5px;
            padding: 30px;
            text-align: center;
            color: #6c757d;
            margin-top: 10px;
        }
        
        /* Prediction histogram styles */
        .prediction-chart {
            margin-top: 10px;
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 5px;
        }
        .chart-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .chart-title {
            margin: 0;
            color: #333;
            font-size: 15px;
        }
        .chart-total {
            background-color: #007bff;
            color: white;
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 13px;
            font-weight: bold;
        }
        .chart-svg {
            width: 100%;
            height: 200px;
            background-color: white;
            border-radius: 5px;
            border: 1px solid #dee2e6;
        }
        .bar-container {
            margin-bottom: 15px;
        }
        .bar-label {
            display: flex;
            justify-content: space-between;
            margin-bottom: 5px;
            font-size: 13px;
            color: #333;
        }
        .bar-label-time {
            font-weight: bold;
            color: #007bff;
        }
        .bar-label-value {
            color: #666;
        }
        .bar-background {
            width: 100%;
            height: 30px;
            background-color: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
            position: relative;
        }
        .bar-fill {
            height: 100%;
            background: linear-gradient(90deg, #28a745 0%, #ffc107 50%, #dc3545 100%);
            border-radius: 4px;
            transition: width 0.5s ease;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            padding-right: 8px;
            color: white;
            font-weight: bold;
            font-size: 12px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        .bar-bikes {
            margin-top: 3px;
            font-size: 12px;
            color: #666;
        }
        
        /* Pin Control Panel */
        #pin-control {
            position: fixed;
            top: 10px;
            left: 10px;
            background-color: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
            z-index: 9998;
            font-family: Arial, sans-serif;
            min-width: 200px;
        }
        #pin-control h4 {
            margin: 0 0 10px 0;
            color: #333;
            font-size: 16px;
        }
        .pin-btn {
            width: 100%;
            padding: 8px;
            margin-bottom: 8px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
            transition: all 0.3s;
        }
        .pin-btn.active {
            box-shadow: 0 0 0 3px rgba(40, 167, 69, 0.5);
        }
        #start-pin-btn {
            background-color: #28a745;
            color: white;
        }
        #start-pin-btn:hover {
            background-color: #218838;
        }
        #end-pin-btn {
            background-color: #dc3545;
            color: white;
        }
        #end-pin-btn:hover {
            background-color: #c82333;
        }
        #clear-pins-btn {
            background-color: #6c757d;
            color: white;
        }
        #clear-pins-btn:hover {
            background-color: #5a6268;
        }
        #plan-route-btn {
            background-color: #007bff;
            color: white;
            margin-top: 10px;
        }
        #plan-route-btn:hover {
            background-color: #0056b3;
        }
        #plan-route-btn:disabled {
            background-color: #ccc;
            cursor: not-allowed;
        }
        .pin-status {
            font-size: 12px;
            color: #666;
            margin-top: -5px;
            margin-bottom: 10px;
        }
    </style>
    <div id="pin-control">
        <h4>📍 Place Pins</h4>
        <button id="start-pin-btn" class="pin-btn" onclick="togglePinMode('start')">
            Place Start Pin
        </button>
        <div class="pin-status" id="start-status">Click to activate</div>
        
        <button id="end-pin-btn" class="pin-btn" onclick="togglePinMode('end')">
            Place End Pin
        </button>
        <div class="pin-status" id="end-status">Click to activate</div>
        
        <button id="clear-pins-btn" class="pin-btn" onclick="clearAllPins()">
            Clear All Pins
        </button>
        
        <button id="plan-route-btn" class="pin-btn" onclick="goToRoutePlanner()" disabled>
            🚴 Plan Route
        </button>
    </div>
    
    <div id="side-panel">
        <div id="panel-header">
            <button id="close-btn" onclick="closePanel()">&times;</button>
            <h3 id="panel-title" style="margin: 0;">Station Information</h3>
        </div>
        <div id="panel-content">
            <div class="info-section">
                <div class="info-label">Station Number:</div>
                <div class="info-value" id="station-number">-</div>
                
                <div class="info-label">Address:</div>
                <div class="info-value" id="station-address">-</div>
                
                <div class="info-label">Coordinates:</div>
                <div class="info-value" id="station-coords">-</div>
            </div>
            
            <div class="info-section">
                <div class="info-label">Bike Availability Predictions:</div>
                <div id="predictions-content" class="prediction-placeholder">
                    <p><strong>Predictions Coming Soon</strong></p>
                    <p style="font-size: 14px; margin-top: 10px;">
                        Future predictions for bike availability will be displayed here.
                    </p>
                </div>
            </div>
        </div>
    </div>
    <script>
        var allStations = """ + all_stations_json + """;
        var stationPredictions = """ + predictions_json + """;
        var stationTotals = """ + station_totals_json + """;
        var stationCurrentRatios = """ + station_current_ratios_json + """;
        var mapInstance = null;
        var pinMode = null; // 'start' or 'end'
        var startMarker = null;
        var endMarker = null;
        var startCoords = null;
        var endCoords = null;
        var highlightedMarker = null;
        var stationMarkers = {};
        
        function setMap(map) {
            mapInstance = map;
            
            // Add click listener to map
            mapInstance.on('click', function(e) {
                if (pinMode === 'start') {
                    placeStartPin(e.latlng.lat, e.latlng.lng);
                } else if (pinMode === 'end') {
                    placeEndPin(e.latlng.lat, e.latlng.lng);
                }
            });
        }
        
        function togglePinMode(mode) {
            if (pinMode === mode) {
                // Deactivate
                pinMode = null;
                document.getElementById(mode + '-pin-btn').classList.remove('active');
                document.getElementById(mode + '-status').textContent = 'Click to activate';
            } else {
                // Deactivate other mode
                if (pinMode) {
                    document.getElementById(pinMode + '-pin-btn').classList.remove('active');
                    document.getElementById(pinMode + '-status').textContent = 'Click to activate';
                }
                // Activate this mode
                pinMode = mode;
                document.getElementById(mode + '-pin-btn').classList.add('active');
                document.getElementById(mode + '-status').textContent = 'Click on map to place';
            }
        }
        
        function placeStartPin(lat, lng) {
            if (!mapInstance) return;
            
            // Remove existing start marker
            if (startMarker) {
                mapInstance.removeLayer(startMarker);
            }
            
            // Create green marker
            var greenIcon = L.icon({
                iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
                shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                iconSize: [25, 41],
                iconAnchor: [12, 41],
                popupAnchor: [1, -34],
                shadowSize: [41, 41]
            });
            
            startMarker = L.marker([lat, lng], {icon: greenIcon}).addTo(mapInstance);
            startMarker.bindPopup('<b>Start Location</b>').openPopup();
            startCoords = {lat: lat, lng: lng};
            
            // Update status
            document.getElementById('start-status').textContent = '✓ Placed at ' + lat.toFixed(4) + ', ' + lng.toFixed(4);
            
            // Deactivate pin mode
            pinMode = null;
            document.getElementById('start-pin-btn').classList.remove('active');
            
            // Enable route planner if both pins are placed
            checkRoutePlannerButton();
        }
        
        function placeEndPin(lat, lng) {
            if (!mapInstance) return;
            
            // Remove existing end marker
            if (endMarker) {
                mapInstance.removeLayer(endMarker);
            }
            
            // Create red marker
            var redIcon = L.icon({
                iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
                shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                iconSize: [25, 41],
                iconAnchor: [12, 41],
                popupAnchor: [1, -34],
                shadowSize: [41, 41]
            });
            
            endMarker = L.marker([lat, lng], {icon: redIcon}).addTo(mapInstance);
            endMarker.bindPopup('<b>End Location</b>').openPopup();
            endCoords = {lat: lat, lng: lng};
            
            // Update status
            document.getElementById('end-status').textContent = '✓ Placed at ' + lat.toFixed(4) + ', ' + lng.toFixed(4);
            
            // Deactivate pin mode
            pinMode = null;
            document.getElementById('end-pin-btn').classList.remove('active');
            
            // Enable route planner if both pins are placed
            checkRoutePlannerButton();
        }
        
        function clearAllPins() {
            if (startMarker && mapInstance) {
                mapInstance.removeLayer(startMarker);
                startMarker = null;
                startCoords = null;
                document.getElementById('start-status').textContent = 'Click to activate';
            }
            if (endMarker && mapInstance) {
                mapInstance.removeLayer(endMarker);
                endMarker = null;
                endCoords = null;
                document.getElementById('end-status').textContent = 'Click to activate';
            }
            pinMode = null;
            document.getElementById('start-pin-btn').classList.remove('active');
            document.getElementById('end-pin-btn').classList.remove('active');
            checkRoutePlannerButton();
        }
        
        function openPanel(stationNumber, address, lat, lon) {
            // Remove previous highlight
            if (highlightedMarker) {
                mapInstance.removeLayer(highlightedMarker);
                highlightedMarker = null;
            }
            
            // Add highlight circle around clicked station
            highlightedMarker = L.circle([lat, lon], {
                color: '#007bff',
                fillColor: '#007bff',
                fillOpacity: 0.2,
                radius: 50,
                weight: 3
            }).addTo(mapInstance);
            
            document.getElementById('station-number').textContent = stationNumber;
            document.getElementById('station-address').textContent = address;
            document.getElementById('station-coords').textContent = lat.toFixed(6) + ', ' + lon.toFixed(6);
            
            // Display predictions if available
            var predictionsDiv = document.getElementById('predictions-content');
            if (stationPredictions[stationNumber] && stationPredictions[stationNumber].length > 0) {
                var preds = stationPredictions[stationNumber];
                
                // Get total bikes from station data
                var totalBikes = stationTotals[stationNumber] || 'N/A';
                
                var html = '<div class="prediction-chart">';
                html += '<div class="chart-header">';
                html += '<h4 class="chart-title">24-Hour Availability Forecast</h4>';
                html += '<div class="chart-total">🚲 Total: ' + totalBikes + '</div>';
                html += '</div>';
                
                // Create SVG chart
                var svgWidth = 350;
                var svgHeight = 200;
                var padding = 30;
                var chartWidth = svgWidth - 2 * padding;
                var chartHeight = svgHeight - 2 * padding;
                
                html += '<svg class="chart-svg" viewBox="0 0 ' + svgWidth + ' ' + svgHeight + '">';
                
                // Draw axes
                html += '<line x1="' + padding + '" y1="' + (svgHeight - padding) + '" x2="' + (svgWidth - padding) + '" y2="' + (svgHeight - padding) + '" stroke="#999" stroke-width="1"/>';
                html += '<line x1="' + padding + '" y1="' + padding + '" x2="' + padding + '" y2="' + (svgHeight - padding) + '" stroke="#999" stroke-width="1"/>';
                
                // Calculate Y-axis bike counts (0, 50%, 100% of total)
                var bikesAtZero = 0;
                var bikesAtMid = Math.round(totalBikes / 2);
                var bikesAtTop = totalBikes;
                
                // Draw horizontal grid lines and Y-axis labels
                html += '<line x1="' + padding + '" y1="' + (svgHeight - padding) + '" x2="' + (svgWidth - padding) + '" y2="' + (svgHeight - padding) + '" stroke="#e0e0e0" stroke-width="1"/>';
                html += '<text x="' + (padding - 5) + '" y="' + (svgHeight - padding + 5) + '" text-anchor="end" font-size="10" fill="#666">' + bikesAtZero + '</text>';
                
                html += '<line x1="' + padding + '" y1="' + (padding + chartHeight/2) + '" x2="' + (svgWidth - padding) + '" y2="' + (padding + chartHeight/2) + '" stroke="#e0e0e0" stroke-width="1" stroke-dasharray="2,2"/>';
                html += '<text x="' + (padding - 5) + '" y="' + (padding + chartHeight/2 + 5) + '" text-anchor="end" font-size="10" fill="#666">' + bikesAtMid + '</text>';
                
                html += '<line x1="' + padding + '" y1="' + padding + '" x2="' + (svgWidth - padding) + '" y2="' + padding + '" stroke="#e0e0e0" stroke-width="1" stroke-dasharray="2,2"/>';
                html += '<text x="' + (padding - 5) + '" y="' + (padding + 5) + '" text-anchor="end" font-size="10" fill="#666">' + bikesAtTop + '</text>';
                
                // Build path for area chart
                // Build combined series with current ratio baseline if available
                var combined = [];
                var currentRatio = stationCurrentRatios[stationNumber];
                if (currentRatio !== undefined) {
                    var currentBikes = (totalBikes && !isNaN(totalBikes)) ? Math.round(currentRatio * totalBikes) : null;
                    combined.push({hour: 0, predicted_ratio: currentRatio, predicted_bikes: currentBikes});
                }
                preds.forEach(function(p) { combined.push(p); });

                var points = [];
                combined.forEach(function(pred, idx) {
                    var x = padding + (idx / (combined.length - 1)) * chartWidth;
                    var ratio = pred.predicted_ratio;
                    var y = (svgHeight - padding) - (ratio * chartHeight);
                    points.push({x: x, y: y, ratio: ratio, hour: pred.hour, bikes: pred.predicted_bikes});
                });
                
                // Create area path (filled)
                var areaPath = 'M ' + padding + ' ' + (svgHeight - padding);
                points.forEach(function(p) {
                    areaPath += ' L ' + p.x + ' ' + p.y;
                });
                areaPath += ' L ' + (svgWidth - padding) + ' ' + (svgHeight - padding) + ' Z';
                html += '<path d="' + areaPath + '" fill="rgba(0, 123, 255, 0.2)" stroke="none"/>';
                
                // Create line path
                var linePath = 'M';
                points.forEach(function(p, idx) {
                    linePath += (idx > 0 ? ' L ' : ' ') + p.x + ' ' + p.y;
                });
                html += '<path d="' + linePath + '" fill="none" stroke="#007bff" stroke-width="2"/>';
                
                // Add points with hover info
                points.forEach(function(p) {
                    var color = p.ratio < 0.3 ? '#dc3545' : (p.ratio < 0.7 ? '#ffc107' : '#28a745');
                    html += '<circle cx="' + p.x + '" cy="' + p.y + '" r="3" fill="' + color + '" stroke="white" stroke-width="1">';
                    html += '<title>+' + p.hour + 'h: ' + (p.ratio * 100).toFixed(1) + '% (' + p.bikes + ' bikes)</title>';
                    html += '</circle>';
                });
                
                // X-axis labels (every 4 hours, include 0h if present)
                for (var i = 0; i < combined.length; i += 4) {
                    var x = padding + (i / (combined.length - 1)) * chartWidth;
                    html += '<text x="' + x + '" y="' + (svgHeight - padding + 15) + '" text-anchor="middle" font-size="9" fill="#666">+' + combined[i].hour + 'h</text>';
                }
                
                html += '</svg>';
                html += '</div>';
                predictionsDiv.innerHTML = html;
                predictionsDiv.style.backgroundColor = 'transparent';
                predictionsDiv.style.border = 'none';
                predictionsDiv.style.padding = '0';
            } else {
                predictionsDiv.innerHTML = '<p><strong>No predictions available</strong></p><p style="font-size: 14px; margin-top: 10px;">Predictions could not be generated for this station.</p>';
            }
            
            document.getElementById('side-panel').classList.add('open');
        }
        
        function closePanel() {
            // Remove highlight when closing panel
            if (highlightedMarker) {
                mapInstance.removeLayer(highlightedMarker);
                highlightedMarker = null;
            }
            document.getElementById('side-panel').classList.remove('open');
        }
        
        function checkRoutePlannerButton() {
            var btn = document.getElementById('plan-route-btn');
            if (startCoords && endCoords) {
                btn.disabled = false;
            } else {
                btn.disabled = true;
            }
        }
        
        function calculateDistance(lat1, lon1, lat2, lon2) {
            var R = 6371; // Earth's radius in km
            var dLat = (lat2 - lat1) * Math.PI / 180;
            var dLon = (lon2 - lon1) * Math.PI / 180;
            var a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                    Math.sin(dLon/2) * Math.sin(dLon/2);
            var c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
            return R * c;
        }
        
        function goToRoutePlanner() {
            if (!startCoords || !endCoords) return;
            
            // Find 3 closest stations to start
            var startStations = allStations.map(function(station) {
                return {
                    station: station,
                    distance: calculateDistance(startCoords.lat, startCoords.lng, station.lat, station.lon)
                };
            }).sort(function(a, b) {
                return a.distance - b.distance;
            }).slice(0, 3);
            
            // Find 3 closest stations to end
            var endStations = allStations.map(function(station) {
                return {
                    station: station,
                    distance: calculateDistance(endCoords.lat, endCoords.lng, station.lat, station.lon)
                };
            }).sort(function(a, b) {
                return a.distance - b.distance;
            }).slice(0, 3);

            try {
                console.log('[RoutePlanner] Nearest start stations:', startStations.map(s => ({n: s.station.number, dKm: s.distance})));
                console.log('[RoutePlanner] Nearest end stations:', endStations.map(s => ({n: s.station.number, dKm: s.distance})));
            } catch (e) { console.warn('[RoutePlanner] logging nearest stations failed', e); }

            // Build payload with predictions and totals for selected stations
            function enrich(list) {
                return list.map(function(item) {
                    var s = item.station;
                    var preds = stationPredictions[s.number] || [];
                    var curRatio = stationCurrentRatios[s.number];
                    return {
                        number: s.number,
                        address: s.address,
                        lat: s.lat,
                        lon: s.lon,
                        distanceKm: item.distance, // already in km
                        total: stationTotals[s.number] || 0,
                        currentRatio: (curRatio !== undefined ? curRatio : null),
                        predictions: preds.map(function(p) {
                            return {
                                hour: p.hour,
                                ratio: p.predicted_ratio,
                                bikes: p.predicted_bikes
                            };
                        })
                    };
                });
            }

            var payload = {
                start: {
                    coords: startCoords,
                    stations: enrich(startStations)
                },
                end: {
                    coords: endCoords,
                    stations: enrich(endStations)
                }
            };

            try {
                console.log('[RoutePlanner] Payload stations (start):', payload.start.stations.map(s => ({n: s.number, total: s.total, preds: s.predictions.length})));
                console.log('[RoutePlanner] Payload stations (end):', payload.end.stations.map(s => ({n: s.number, total: s.total, preds: s.predictions.length})));
                sessionStorage.setItem('route_planner_payload', JSON.stringify(payload));
                console.log('[RoutePlanner] Stored payload in sessionStorage (bytes):', JSON.stringify(payload).length);
            } catch (e) {
                console.warn('[RoutePlanner] Could not store payload in sessionStorage', e);
            }

            // Fallback: store in window.name to survive navigation even across file:// quirks
            try {
                window.name = 'ROUTE_PAYLOAD:' + JSON.stringify(payload);
                console.log('[RoutePlanner] Stored payload in window.name (length):', window.name.length);
            } catch (e) {
                console.warn('[RoutePlanner] Could not write window.name payload', e);
            }
            
            // Build URL with parameters
            var params = new URLSearchParams();
            params.set('start_lat', startCoords.lat);
            params.set('start_lng', startCoords.lng);
            params.set('end_lat', endCoords.lat);
            params.set('end_lng', endCoords.lng);
            // Keep lightweight station metadata in URL for fallback only
            try {
                params.set('start_stations', JSON.stringify(startStations));
                params.set('end_stations', JSON.stringify(endStations));
            } catch (e) {
                // If URL length becomes an issue, these can be omitted
            }
            params.set('use_session', '1');
            
            // Navigate to route planner page
            console.log('[RoutePlanner] Navigating to route_planner.html with params size:', params.toString().length);
            window.location.href = 'route_planner.html?' + params.toString();
        }
        
        // Initialize map reference when ready
        (function initMap() {
            var attempts = 0;
            var maxAttempts = 50;
            
            function findMap() {
                attempts++;
                for (var key in window) {
                    if (window[key] && typeof window[key] === 'object' && window[key].hasOwnProperty('_layers')) {
                        setMap(window[key]);
                        console.log('Map initialized successfully');
                        return;
                    }
                }
                if (attempts < maxAttempts) {
                    setTimeout(findMap, 100);
                }
            }
            
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', findMap);
            } else {
                findMap();
            }
        })();
    </script>
    """
    
    m.get_root().html.add_child(folium.Element(custom_html))
    
    # Add JavaScript to create markers after map initialization
    markers_js = "<script>\n"
    markers_js += "setTimeout(function() {\n"
    markers_js += "    var map = window[Object.keys(window).find(key => window[key] && window[key]._layers)];\n"
    markers_js += "    if (!map) return;\n"
    
    # Add markers for each point
    for point in data:
        # Escape address for JavaScript
        address_escaped = point['address'].replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"').replace("\n", " ")
        num = point['number']
        lat = point['lat']
        lon = point['lon']
        
        markers_js += f"""
    var marker_{num} = L.marker([{lat}, {lon}], {{
        icon: L.icon({{
            iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-blue.png',
            shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
            iconSize: [25, 41],
            iconAnchor: [12, 41],
            popupAnchor: [1, -34],
            shadowSize: [41, 41]
        }})
    }}).addTo(map);
    marker_{num}.bindTooltip('{address_escaped}');
    marker_{num}.on('click', function() {{
        openPanel({num}, '{address_escaped}', {lat}, {lon});
    }});
"""
    
    markers_js += "}, 500);\n</script>"
    
    m.get_root().html.add_child(folium.Element(markers_js))
    
    # Save the map
    m.save(output_file)
    print(f"Map saved to {output_file}")
    print(f"Total points displayed: {len(data)}")
    
    return m


def main():
    # Try to load extra.csv first, if not found try extra.json
    file_options = ['extra.csv', 'extra.json']
    
    data = None
    loaded_file = None
    
    for file_name in file_options:
        if os.path.exists(file_name):
            try:
                print(f"Loading data from {file_name}...")
                data = load_data(file_name)
                loaded_file = file_name
                break
            except Exception as e:
                print(f"Error loading {file_name}: {e}")
                continue
    
    if data is None:
        print("Error: Could not load data from extra.csv or extra.json")
        return
    
    print(f"Successfully loaded {len(data)} points from {loaded_file}")
    
    # Load station totals
    print("Loading station totals...")
    station_totals = load_station_totals('agg.csv')
    print(f"Loaded totals for {len(station_totals)} stations")
    
    # Load predictions
    print("Loading predictions from model...")
    try:
        predictions = get_predictions_for_all_stations(
            agg_csv_path='agg.csv',
            model_path='gru_bike_prediction_model.pt',
            prediction_hours=24
        )
        print(f"Loaded predictions for {len(predictions)} stations")
    except Exception as e:
        print(f"Error loading predictions: {e}")
        predictions = {}
    
    # Load current ratios
    print("Loading current ratios...")
    current_ratios = load_current_ratios('agg.csv')
    print(f"Loaded current ratios for {len(current_ratios)} stations")

    # Create and save the map
    create_map(data, predictions, station_totals, current_ratios)


if __name__ == "__main__":
    main()
