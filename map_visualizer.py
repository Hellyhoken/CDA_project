import pandas as pd
import json
import folium
import os


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


def create_map(data, output_file='map.html'):
    """Create a folium map with all the points."""
    if not data:
        print("No data to display")
        return
    
    # Calculate the center of the map (average of all coordinates)
    avg_lat = sum(point['lat'] for point in data) / len(data)
    avg_lon = sum(point['lon'] for point in data) / len(data)
    
    # Create the map centered on the average coordinates
    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=13)
    
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
                <div class="prediction-placeholder">
                    <p><strong>Predictions Coming Soon</strong></p>
                    <p style="font-size: 14px; margin-top: 10px;">
                        Future predictions for bike availability will be displayed here.
                    </p>
                </div>
            </div>
        </div>
    </div>
    <script>
        var allStations = """ + json.dumps(data) + """;
        var mapInstance = null;
        var pinMode = null; // 'start' or 'end'
        var startMarker = null;
        var endMarker = null;
        var startCoords = null;
        var endCoords = null;
        
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
            document.getElementById('station-number').textContent = stationNumber;
            document.getElementById('station-address').textContent = address;
            document.getElementById('station-coords').textContent = lat.toFixed(6) + ', ' + lon.toFixed(6);
            document.getElementById('side-panel').classList.add('open');
        }
        
        function closePanel() {
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
            
            // Build URL with parameters
            var params = new URLSearchParams();
            params.set('start_lat', startCoords.lat);
            params.set('start_lng', startCoords.lng);
            params.set('end_lat', endCoords.lat);
            params.set('end_lng', endCoords.lng);
            params.set('start_stations', JSON.stringify(startStations));
            params.set('end_stations', JSON.stringify(endStations));
            
            // Navigate to route planner page
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
    
    # Add markers for each point
    for point in data:
        # Create JavaScript function call for onclick
        onclick_js = f"openPanel({point['number']}, '{point['address'].replace("'", "\\'")}', {point['lat']}, {point['lon']})"
        
        # Create custom icon with onclick event
        icon_html = f'''
            <div onclick="{onclick_js}" style="cursor: pointer;">
                <i class="fa fa-map-marker fa-3x" style="color: blue;"></i>
            </div>
        '''
        
        folium.Marker(
            location=[point['lat'], point['lon']],
            tooltip=point['address'],
            icon=folium.DivIcon(html=icon_html)
        ).add_to(m)
    
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
    
    # Create and save the map
    create_map(data)


if __name__ == "__main__":
    main()
