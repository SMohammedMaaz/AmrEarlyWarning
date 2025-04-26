// Chart visualization functionality
document.addEventListener('DOMContentLoaded', function() {
    // Resistance Trend Chart
    const trendChartElement = document.getElementById('resistanceTrendChart');
    if (trendChartElement) {
        // Fetch data from API
        fetch('/api/resistance-trends')
            .then(response => response.json())
            .then(data => {
                const ctx = trendChartElement.getContext('2d');
                
                new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: data.map(item => item.month),
                        datasets: [{
                            label: 'Resistance %',
                            data: data.map(item => item.percentage),
                            fill: false,
                            borderColor: '#0dcaf0',
                            backgroundColor: 'rgba(13, 202, 240, 0.1)',
                            tension: 0.1,
                            pointBackgroundColor: '#0dcaf0'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const item = data[context.dataIndex];
                                        return [
                                            `Resistance: ${item.percentage}%`,
                                            `Total Samples: ${item.total}`,
                                            `Resistant: ${item.resistant}`
                                        ];
                                    }
                                }
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                max: 100,
                                title: {
                                    display: true,
                                    text: 'Resistance %'
                                }
                            }
                        }
                    }
                });
            })
            .catch(error => {
                console.error('Error loading resistance trends:', error);
                trendChartElement.parentNode.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        Error loading chart data
                    </div>
                `;
            });
    }
    
    // Top Pathogens Chart
    const pathogensChartElement = document.getElementById('topPathogensChart');
    if (pathogensChartElement) {
        // Fetch data from API
        fetch('/api/top-pathogens')
            .then(response => response.json())
            .then(data => {
                const ctx = pathogensChartElement.getContext('2d');
                
                new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: data.map(item => item.pathogen),
                        datasets: [{
                            label: 'Resistance %',
                            data: data.map(item => item.percentage),
                            backgroundColor: [
                                '#dc3545', '#fd7e14', '#ffc107', '#20c997', '#0dcaf0',
                                '#6610f2', '#d63384', '#198754', '#0d6efd', '#6c757d'
                            ]
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const item = data[context.dataIndex];
                                        return [
                                            `Resistance: ${item.percentage}%`,
                                            `Total Samples: ${item.total}`,
                                            `Resistant: ${item.resistant}`
                                        ];
                                    }
                                }
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                max: 100,
                                title: {
                                    display: true,
                                    text: 'Resistance %'
                                }
                            }
                        }
                    }
                });
            })
            .catch(error => {
                console.error('Error loading top pathogens:', error);
                pathogensChartElement.parentNode.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        Error loading chart data
                    </div>
                `;
            });
    }
    
    // Resistance by Antibiotic Chart
    const antibioticChartElement = document.getElementById('antibioticResistanceChart');
    if (antibioticChartElement) {
        // Get pathogen ID from data attribute
        const pathogenId = antibioticChartElement.getAttribute('data-pathogen-id');
        
        if (pathogenId) {
            // Fetch data from API
            fetch(`/api/pathogen/${pathogenId}/resistance`)
                .then(response => response.json())
                .then(data => {
                    const ctx = antibioticChartElement.getContext('2d');
                    
                    new Chart(ctx, {
                        type: 'horizontalBar',
                        data: {
                            labels: data.map(item => item.antibiotic),
                            datasets: [{
                                label: 'Resistance %',
                                data: data.map(item => item.percentage),
                                backgroundColor: data.map(item => {
                                    // Color based on resistance level
                                    if (item.percentage >= 75) return '#dc3545';
                                    if (item.percentage >= 50) return '#fd7e14';
                                    if (item.percentage >= 25) return '#ffc107';
                                    return '#198754';
                                })
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            indexAxis: 'y',
                            plugins: {
                                tooltip: {
                                    callbacks: {
                                        label: function(context) {
                                            const item = data[context.dataIndex];
                                            return [
                                                `Resistance: ${item.percentage}%`,
                                                `Total Samples: ${item.total}`,
                                                `Resistant: ${item.resistant}`
                                            ];
                                        }
                                    }
                                }
                            },
                            scales: {
                                x: {
                                    beginAtZero: true,
                                    max: 100,
                                    title: {
                                        display: true,
                                        text: 'Resistance %'
                                    }
                                }
                            }
                        }
                    });
                })
                .catch(error => {
                    console.error('Error loading antibiotic resistance:', error);
                    antibioticChartElement.parentNode.innerHTML = `
                        <div class="alert alert-danger">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            Error loading chart data
                        </div>
                    `;
                });
        }
    }
});
