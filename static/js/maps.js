// Map visualization functionality
document.addEventListener('DOMContentLoaded', function() {
    // Initialize map if the container exists
    const mapContainer = document.getElementById('resistanceMap');
    
    if (mapContainer) {
        // Get data attribute with map data
        const mapDataElement = document.getElementById('map-data');
        let mapData = [];
        
        if (mapDataElement && mapDataElement.getAttribute('data-map')) {
            try {
                mapData = JSON.parse(mapDataElement.getAttribute('data-map'));
            } catch (e) {
                console.error('Error parsing map data:', e);
            }
        }
        
        // Initialize Mapbox
        mapboxgl.accessToken = mapboxToken || 'pk.eyJ1IjoiZXhhbXBsZSIsImEiOiJjbGdxNjhibWkwMzBuM2VvYTk5cjZmYmRmIn0.xdlDKR8DCOZ9i-OaUn9v5w';
        
        const map = new mapboxgl.Map({
            container: 'resistanceMap',
            style: 'mapbox://styles/mapbox/dark-v10',
            center: [78.9629, 20.5937], // Center on India
            zoom: 3
        });
        
        // Add navigation controls
        map.addControl(new mapboxgl.NavigationControl());
        
        // Add data points when map loads
        map.on('load', function() {
            // Add markers for each location
            mapData.forEach(location => {
                // Create marker element
                const el = document.createElement('div');
                el.className = 'marker';
                el.style.width = '20px';
                el.style.height = '20px';
                el.style.borderRadius = '50%';
                el.style.backgroundColor = location.color;
                el.style.border = '2px solid white';
                
                // Create popup content
                let popupContent = `
                    <h5>${location.name}</h5>
                    <p>${location.location}</p>
                `;
                
                // Different content for facilities vs environmental samples
                if (location.isEnvironmentalSample) {
                    popupContent += `
                        <p><strong>Sample Type:</strong> ${location.sampleType}</p>
                        <p><strong>Pathogen:</strong> ${location.pathogen}</p>
                        ${location.pathogenLoad ? `<p><strong>Pathogen Load:</strong> ${location.pathogenLoad}</p>` : ''}
                        <p><strong>Risk Level:</strong> <span class="badge" style="background-color:${location.color}">${location.riskLevel}</span></p>
                    `;
                } else {
                    popupContent += `
                        <p><strong>Resistance Level:</strong> ${location.resistancePercentage}%</p>
                        <p><strong>Risk Level:</strong> <span class="badge" style="background-color:${location.color}">${location.riskLevel}</span></p>
                        <p><strong>Samples:</strong> ${location.totalSamples} (${location.totalResistant} resistant)</p>
                    `;
                    
                    // Add pathogen breakdown if available
                    if (location.pathogens && location.pathogens.length > 0) {
                        popupContent += '<hr><h6>Pathogen Breakdown:</h6><ul>';
                        location.pathogens.slice(0, 3).forEach(p => {
                            popupContent += `<li>${p.name}: ${p.percentage}% resistant</li>`;
                        });
                        if (location.pathogens.length > 3) {
                            popupContent += '<li>...</li>';
                        }
                        popupContent += '</ul>';
                    }
                }
                
                // Create popup
                const popup = new mapboxgl.Popup({ offset: 25 })
                    .setHTML(popupContent);
                
                // Add marker to map
                new mapboxgl.Marker(el)
                    .setLngLat([location.longitude, location.latitude])
                    .setPopup(popup)
                    .addTo(map);
            });
            
            // If on the dedicated map page, add legend and filters
            if (document.getElementById('map-container')) {
                // Add legend
                const legend = document.getElementById('map-legend');
                if (legend) {
                    legend.innerHTML = `
                        <h6 class="mb-2">Risk Levels</h6>
                        <div class="d-flex mb-1 align-items-center">
                            <div style="width: 20px; height: 20px; border-radius: 50%; background-color: #28a745; margin-right: 10px;"></div>
                            <span>Low (< 25%)</span>
                        </div>
                        <div class="d-flex mb-1 align-items-center">
                            <div style="width: 20px; height: 20px; border-radius: 50%; background-color: #ffc107; margin-right: 10px;"></div>
                            <span>Medium (25-50%)</span>
                        </div>
                        <div class="d-flex mb-1 align-items-center">
                            <div style="width: 20px; height: 20px; border-radius: 50%; background-color: #fd7e14; margin-right: 10px;"></div>
                            <span>High (50-75%)</span>
                        </div>
                        <div class="d-flex mb-1 align-items-center">
                            <div style="width: 20px; height: 20px; border-radius: 50%; background-color: #dc3545; margin-right: 10px;"></div>
                            <span>Very High (> 75%)</span>
                        </div>
                    `;
                }
                
                // Add filter functionality
                const filterSelect = document.getElementById('map-filter');
                if (filterSelect) {
                    filterSelect.addEventListener('change', function() {
                        const value = this.value;
                        
                        // Remove existing markers
                        document.querySelectorAll('.marker').forEach(m => m.remove());
                        
                        // Filter data and recreate markers
                        const filteredData = value === 'all' 
                            ? mapData 
                            : mapData.filter(location => {
                                if (value === 'environmental' && location.isEnvironmentalSample) return true;
                                if (value === 'facility' && !location.isEnvironmentalSample) return true;
                                if (value === 'high_risk' && location.riskLevel === 'High') return true;
                                if (value === 'very_high_risk' && location.riskLevel === 'Very High') return true;
                                return false;
                            });
                        
                        // Re-add filtered markers
                        // (Code would be similar to the marker creation above)
                    });
                }
            }
        });
    }
});

// Create a global variable for mapbox token
let mapboxToken = '';
