// API Configuration
const API_URL = 'http://localhost:8000/api/v1/query';

// DOM Elements
const queryInput = document.getElementById('queryInput');
const submitBtn = document.getElementById('submitBtn');
const methodBtns = document.querySelectorAll('.method-btn');
const voiceArea = document.getElementById('voiceArea');
const recordBtn = document.getElementById('recordBtn');
const voiceWave = document.getElementById('voiceWave');
const voiceStatus = document.getElementById('voiceStatus');
const responseArea = document.getElementById('responseArea');
const weatherDisplay = document.getElementById('weatherDisplay');
const loading = document.getElementById('loading');
const errorMsg = document.getElementById('errorMsg');
const historyList = document.getElementById('historyList');
const clearHistoryBtn = document.getElementById('clearHistoryBtn');
const downloadBtn = document.getElementById('downloadBtn');

// State
let currentMethod = 'text';
let recentSearches = [];
let currentWeatherData = null;
let currentAIResponse = '';
let currentQuery = '';

// ==================== HISTORY MANAGEMENT ====================

function loadHistory() {
    const saved = localStorage.getItem('farmwise_history');
    if (saved) {
        recentSearches = JSON.parse(saved);
        const twoHoursAgo = Date.now() - (2 * 60 * 60 * 1000);
        recentSearches = recentSearches.filter(item => item.timestamp > twoHoursAgo);
        saveHistory();
    }
    renderHistory();
}

function saveHistory() {
    localStorage.setItem('farmwise_history', JSON.stringify(recentSearches));
}

function addToHistory(query, response, weatherData = null) {
    recentSearches = recentSearches.filter(item => item.query !== query);
    recentSearches.unshift({
        query: query,
        response: response,
        weatherData: weatherData,
        timestamp: Date.now()
    });
    if (recentSearches.length > 10) {
        recentSearches = recentSearches.slice(0, 10);
    }
    saveHistory();
    renderHistory();
}

function clearHistory() {
    recentSearches = [];
    saveHistory();
    renderHistory();
}

function formatTimeAgo(timestamp) {
    const seconds = Math.floor((Date.now() - timestamp) / 1000);
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
}

function renderHistory() {
    if (recentSearches.length === 0) {
        historyList.innerHTML = `
            <div class="empty-history">
                <i class="fas fa-inbox"></i>
                <p>No recent searches</p>
            </div>
        `;
        return;
    }
    
    historyList.innerHTML = recentSearches.map(item => `
        <div class="history-item" data-query="${escapeHtml(item.query)}">
            <div class="history-query">${escapeHtml(item.query.substring(0, 50))}</div>
            <div class="history-time"><i class="far fa-clock"></i> ${formatTimeAgo(item.timestamp)}</div>
        </div>
    `).join('');
    
    document.querySelectorAll('.history-item').forEach(el => {
        el.addEventListener('click', () => {
            queryInput.value = el.dataset.query;
            submitQuery();
        });
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showLoading(show) {
    loading.classList.toggle('hidden', !show);
}

function showError(message) {
    errorMsg.textContent = message;
    errorMsg.classList.remove('hidden');
    setTimeout(() => errorMsg.classList.add('hidden'), 5000);
}

// ==================== AI RESPONSE FORMATTING ====================

function formatAIResponse(text) {
    if (!text) return '';
    
    let formatted = text;
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    formatted = formatted.replace(/^[•\-]\s+(.*?)$/gm, '<li>$1</li>');
    formatted = formatted.replace(/(<li>.*?<\/li>)/gs, '<ul>$1</ul>');
    formatted = formatted.replace(/CROP \d+:/g, '<strong class="crop-heading">$&</strong>');
    formatted = formatted.replace(/\n/g, '<br>');
    
    return formatted;
}

function displayAIResponse(response, locationData = null) {
    let html = '';
    
    if (locationData && locationData.location_name) {
        html += `
            <div class="location-card">
                <div class="location-icon"><i class="fas fa-map-marker-alt"></i></div>
                <div class="location-details">
                    <h4>${escapeHtml(locationData.location_name)}</h4>
                    ${locationData.latitude ? `<p>📍 ${locationData.latitude}, ${locationData.longitude}</p>` : ''}
                </div>
            </div>
        `;
    }
    
    const formattedResponse = formatAIResponse(response);
    html += `<div class="ai-response-text">${formattedResponse}</div>`;
    responseArea.innerHTML = html;
}

// ==================== WEATHER FUNCTIONS ====================

function getWeatherIcon(description) {
    const desc = description.toLowerCase();
    if (desc.includes('clear') || desc.includes('sunny')) return '☀️';
    if (desc.includes('cloud') || desc.includes('overcast')) return '☁️';
    if (desc.includes('rain') || desc.includes('shower')) return '🌧️';
    if (desc.includes('thunder') || desc.includes('storm')) return '⛈️';
    if (desc.includes('snow')) return '❄️';
    if (desc.includes('fog')) return '🌫️';
    if (desc.includes('wind')) return '💨';
    return '🌤️';
}

function getWeatherConditionLogo(description) {
    const desc = description.toLowerCase();
    if (desc.includes('clear') || desc.includes('sunny')) return '☀️ Sunny';
    if (desc.includes('cloud') || desc.includes('overcast')) return '☁️ Cloudy';
    if (desc.includes('rain') || desc.includes('shower')) return '🌧️ Rainy';
    if (desc.includes('thunder') || desc.includes('storm')) return '⛈️ Stormy';
    if (desc.includes('wind')) return '💨 Windy';
    if (desc.includes('fog')) return '🌫️ Foggy';
    return '🌤️ Partly Cloudy';
}

function formatDateRange(days) {
    if (!days || days.length === 0) return '';
    const start = new Date(days[0].date);
    const end = new Date(days[days.length - 1].date);
    return `${start.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${end.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`;
}

function displayWeatherTiles(weatherData, weekNumber) {
    const weekIndex = weekNumber - 1;
    if (!weatherData.forecast || !weatherData.forecast[weekIndex]) {
        return '<div class="no-data-message"><i class="fas fa-calendar-times"></i><p>No forecast data available</p></div>';
    }
    
    const week = weatherData.forecast[weekIndex];
    if (!week.days || week.days.length === 0) {
        return '<div class="no-data-message"><i class="fas fa-calendar-times"></i><p>No forecast data available</p></div>';
    }
    
    return `
        <div class="weather-tiles-grid">
            ${week.days.map(day => `
                <div class="weather-day-tile">
                    <div class="tile-date">${new Date(day.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}</div>
                    <div class="tile-icon">${getWeatherIcon(day.weather_description)}</div>
                    <div class="tile-temp">${Math.round(day.temperature_max)}° / ${Math.round(day.temperature_min)}°</div>
                    <div class="tile-details">
                        <span><i class="fas fa-tint"></i> ${day.precipitation}mm</span>
                        <span><i class="fas fa-wind"></i> ${Math.round(day.wind_speed)}km/h</span>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

function displayWeather(weatherData) {
    const location = weatherData.location_name;
    const lat = weatherData.latitude;
    const lon = weatherData.longitude;
    const current = weatherData.current;
    const conditionLogo = getWeatherConditionLogo(current.weather_description);
    
    let todayMinTemp = current.temperature;
    let todayMaxTemp = current.temperature;
    if (weatherData.forecast && weatherData.forecast[0] && weatherData.forecast[0].days && weatherData.forecast[0].days.length > 0) {
        const today = weatherData.forecast[0].days[0];
        todayMaxTemp = today.temperature_max;
        todayMinTemp = today.temperature_min;
    }
    
    const week1Dates = weatherData.forecast[0] ? formatDateRange(weatherData.forecast[0].days) : '';
    const week2Dates = weatherData.forecast[1] ? formatDateRange(weatherData.forecast[1].days) : '';
    const week3Dates = weatherData.forecast[2] ? formatDateRange(weatherData.forecast[2].days) : '';
    
    weatherDisplay.innerHTML = `
        <div class="weather-block">
            <div class="location-header">
                <h2><i class="fas fa-map-marker-alt"></i> ${escapeHtml(location)}</h2>
                <p class="coordinates">📍 Latitude: ${lat} | Longitude: ${lon}</p>
            </div>
            <div class="metrics-title">
                <h3><i class="fas fa-chart-line"></i> Today's Weather Metrics</h3>
            </div>
            <div class="weather-metrics-grid">
                <div class="metric-card">
                    <div class="metric-icon">🌡️</div>
                    <div class="metric-value">${Math.round(todayMaxTemp)}° / ${Math.round(todayMinTemp)}°</div>
                    <div class="metric-label">Temperature (Max/Min)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-icon">💧</div>
                    <div class="metric-value">${current.humidity}%</div>
                    <div class="metric-label">Humidity</div>
                </div>
                <div class="metric-card">
                    <div class="metric-icon">💨</div>
                    <div class="metric-value">${current.wind_speed} km/h</div>
                    <div class="metric-label">Wind Speed</div>
                </div>
                <div class="metric-card">
                    <div class="metric-icon">🌧️</div>
                    <div class="metric-value">${current.precipitation} mm</div>
                    <div class="metric-label">Precipitation</div>
                </div>
                <div class="metric-card condition-card">
                    <div class="metric-icon">${getWeatherIcon(current.weather_description)}</div>
                    <div class="metric-value">${conditionLogo}</div>
                    <div class="metric-label">Condition</div>
                </div>
            </div>
        </div>
        <div class="forecast-block">
            <div class="week-tabs-container">
                <div class="week-tabs" id="weekTabs">
                    <button class="week-tab active" data-week="1">
                        📅 Week 1<br><small>${week1Dates}</small>
                    </button>
                    <button class="week-tab" data-week="2">
                        📅 Week 2<br><small>${week2Dates}</small>
                    </button>
                    <button class="week-tab" data-week="3">
                        📅 Week 3<br><small>${week3Dates}</small>
                    </button>
                </div>
            </div>
            <div id="forecastContainer">
                ${displayWeatherTiles(weatherData, 1)}
            </div>
        </div>
    `;
    
    const weekBtns = document.querySelectorAll('.week-tab');
    weekBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            weekBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const week = parseInt(btn.dataset.week);
            const container = document.getElementById('forecastContainer');
            if (container) {
                container.innerHTML = displayWeatherTiles(weatherData, week);
            }
        });
    });
    
    weatherDisplay.classList.remove('hidden');
    weatherDisplay.style.display = 'block';
}

// ==================== EXCEL DOWNLOAD ====================

function downloadExcel() {
    if (!currentQuery) {
        showError('No data to download. Please ask a question first.');
        return;
    }
    
    const data = [];
    const currentDate = new Date();
    
    data.push(['FARM WISE REPORT']);
    data.push(['']);
    data.push(['Report Generated:', currentDate.toLocaleString()]);
    data.push(['']);
    data.push(['QUERY', currentQuery]);
    data.push(['']);
    
    if (currentAIResponse) {
        let cleanResponse = currentAIResponse
            .replace(/\*\*(.*?)\*\*/g, '$1')
            .replace(/[•·-]\s/g, '• ');
        
        let responseLines = [];
        const paragraphs = cleanResponse.split('\n');
        
        for (let para of paragraphs) {
            if (para.trim() === '') {
                responseLines.push('');
                continue;
            }
            const wrappedLines = wrapTextForExcel(para, 100, 120);
            responseLines.push(...wrappedLines);
        }
        
        if (responseLines.length > 0) {
            data.push(['RESPONSE', responseLines[0]]);
            for (let i = 1; i < responseLines.length; i++) {
                data.push(['', responseLines[i]]);
            }
        }
        data.push(['']);
    }
    
    if (currentWeatherData && currentWeatherData.forecast) {
        data.push(['LOCATION INFORMATION']);
        data.push(['Location:', currentWeatherData.location_name]);
        data.push(['Coordinates:', `${currentWeatherData.latitude}, ${currentWeatherData.longitude}`]);
        data.push(['']);
        
        data.push(['CURRENT WEATHER CONDITIONS']);
        data.push(['Temperature:', `${currentWeatherData.current.temperature}°C`]);
        data.push(['Humidity:', `${currentWeatherData.current.humidity}%`]);
        data.push(['Wind Speed:', `${currentWeatherData.current.wind_speed} km/h`]);
        data.push(['Precipitation:', `${currentWeatherData.current.precipitation} mm`]);
        data.push(['Condition:', currentWeatherData.current.weather_description]);
        data.push(['']);
        
        data.push(['FORECAST DATA']);
        data.push(['']);
        
        if (currentWeatherData.forecast[0] && currentWeatherData.forecast[0].days.length > 0) {
            const week1 = currentWeatherData.forecast[0];
            const startDate = new Date(week1.days[0].date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            const endDate = new Date(week1.days[week1.days.length - 1].date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            data.push([`WEEK 1 (${startDate} - ${endDate})`]);
            data.push(['Date', 'Max Temp (°C)', 'Min Temp (°C)', 'Precipitation (mm)', 'Wind Speed (km/h)', 'Condition']);
            
            week1.days.forEach(day => {
                data.push([
                    new Date(day.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
                    Math.round(day.temperature_max),
                    Math.round(day.temperature_min),
                    day.precipitation,
                    Math.round(day.wind_speed),
                    day.weather_description
                ]);
            });
            data.push(['']);
        }
        
        if (currentWeatherData.forecast[1] && currentWeatherData.forecast[1].days.length > 0) {
            const week2 = currentWeatherData.forecast[1];
            const startDate = new Date(week2.days[0].date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            const endDate = new Date(week2.days[week2.days.length - 1].date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            data.push([`WEEK 2 (${startDate} - ${endDate})`]);
            data.push(['Date', 'Max Temp (°C)', 'Min Temp (°C)', 'Precipitation (mm)', 'Wind Speed (km/h)', 'Condition']);
            
            week2.days.forEach(day => {
                data.push([
                    new Date(day.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
                    Math.round(day.temperature_max),
                    Math.round(day.temperature_min),
                    day.precipitation,
                    Math.round(day.wind_speed),
                    day.weather_description
                ]);
            });
            data.push(['']);
        }
        
        if (currentWeatherData.forecast[2] && currentWeatherData.forecast[2].days.length > 0) {
            const week3 = currentWeatherData.forecast[2];
            const startDate = new Date(week3.days[0].date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            const endDate = new Date(week3.days[week3.days.length - 1].date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            data.push([`WEEK 3 (${startDate} - ${endDate})`]);
            data.push(['Date', 'Max Temp (°C)', 'Min Temp (°C)', 'Precipitation (mm)', 'Wind Speed (km/h)', 'Condition']);
            
            week3.days.forEach(day => {
                data.push([
                    new Date(day.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
                    Math.round(day.temperature_max),
                    Math.round(day.temperature_min),
                    day.precipitation,
                    Math.round(day.wind_speed),
                    day.weather_description
                ]);
            });
            data.push(['']);
        }
    }
    
    data.push(['']);
    data.push(['Report generated by FarmWise AI']);
    data.push([`Generated on: ${currentDate.toLocaleString()}`]);
    
    const ws = XLSX.utils.aoa_to_sheet(data);
    ws['!cols'] = [{ wch: 25 }, { wch: 85 }];
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'FarmWise Report');
    
    const fileName = `FarmWise_Report_${currentDate.getFullYear()}${(currentDate.getMonth() + 1).toString().padStart(2, '0')}${currentDate.getDate().toString().padStart(2, '0')}_${currentDate.getHours().toString().padStart(2, '0')}${currentDate.getMinutes().toString().padStart(2, '0')}.xlsx`;
    XLSX.writeFile(wb, fileName);
}

function wrapTextForExcel(text, minChars = 100, maxChars = 120) {
    if (!text) return [];
    
    let cleanText = text
        .replace(/\*\*(.*?)\*\*/g, '$1')
        .replace(/[•·-]\s/g, '• ');
    
    const lines = [];
    let remaining = cleanText;
    
    while (remaining.length > maxChars) {
        let breakPoint = maxChars;
        for (let i = maxChars; i >= minChars; i--) {
            const char = remaining[i];
            if (char === ' ' || char === '.' || char === ',' || char === ';' || char === ':' || char === '?' || char === '!') {
                breakPoint = i + 1;
                break;
            }
        }
        if (breakPoint === maxChars && remaining[maxChars] !== ' ') {
            breakPoint = maxChars;
        }
        const line = remaining.substring(0, breakPoint).trim();
        if (line) lines.push(line);
        remaining = remaining.substring(breakPoint).trim();
    }
    if (remaining) lines.push(remaining);
    return lines;
}

// ==================== API CALL ====================

async function submitQuery() {
    const query = queryInput.value.trim();
    if (!query) {
        showError('Please enter a question');
        return;
    }
    
    currentQuery = query;
    currentWeatherData = null;
    
    responseArea.innerHTML = '<div class="greeting-message"><div class="greeting-icon">🌾</div><h3>Loading...</h3><p>Fetching your answer...</p></div>';
    weatherDisplay.classList.add('hidden');
    showLoading(true);
    
    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            currentAIResponse = data.response;
            
            if (data.data && data.data.forecast) {
                currentWeatherData = data.data;
                displayAIResponse(data.response);
                displayWeather(data.data);
            } else {
                let locationData = null;
                if (data.data && data.data.location) {
                    locationData = {
                        location_name: data.data.location,
                        latitude: data.data.latitude,
                        longitude: data.data.longitude
                    };
                }
                displayAIResponse(data.response, locationData);
                weatherDisplay.classList.add('hidden');
            }
            
            addToHistory(query, data.response, data.data);
            
        } else {
            showError(data.error || 'Something went wrong');
            responseArea.innerHTML = `<div class="greeting-message"><div class="greeting-icon">⚠️</div><h3>Error</h3><p>${escapeHtml(data.error || 'Failed to get response')}</p></div>`;
        }
        
    } catch (error) {
        showError('Unable to connect to server. Make sure backend is running at ' + API_URL);
        responseArea.innerHTML = `<div class="greeting-message"><div class="greeting-icon">🔌</div><h3>Connection Error</h3><p>Cannot connect to the server.</p></div>`;
    } finally {
        showLoading(false);
    }
}

// ==================== VOICE INPUT ====================

function startVoiceInput() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        showError('Voice recognition not supported in this browser');
        return;
    }
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    
    voiceStatus.textContent = 'Listening...';
    voiceWave.innerHTML = '';
    for (let i = 0; i < 20; i++) {
        const bar = document.createElement('div');
        bar.className = 'wave-bar';
        bar.style.animationDelay = `${i * 0.05}s`;
        voiceWave.appendChild(bar);
    }
    
    recognition.start();
    
    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        queryInput.value = transcript;
        voiceStatus.textContent = 'Recognized: ' + transcript;
        setTimeout(() => {
            voiceArea.classList.add('hidden');
            submitQuery();
        }, 1000);
    };
    
    recognition.onerror = () => {
        voiceStatus.textContent = 'Recognition failed. Please try again.';
        setTimeout(() => {
            voiceArea.classList.add('hidden');
        }, 2000);
    };
    
    recognition.onend = () => {
        voiceWave.innerHTML = '';
    };
}

// ==================== EVENT LISTENERS ====================

submitBtn.addEventListener('click', submitQuery);
queryInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') submitQuery();
});
downloadBtn.addEventListener('click', downloadExcel);
clearHistoryBtn.addEventListener('click', clearHistory);

methodBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        methodBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        
        if (btn.dataset.method === 'voice') {
            voiceArea.classList.remove('hidden');
            recordBtn.onclick = startVoiceInput;
        } else {
            voiceArea.classList.add('hidden');
        }
    });
});

// ==================== INITIALIZE ====================
loadHistory();