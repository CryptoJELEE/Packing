// 어드민 대시보드 JavaScript

let adminToken = localStorage.getItem('admin_token');
let dailyChart, hourlyChart, palletChart;

// 초기화
document.addEventListener('DOMContentLoaded', function() {
    if (adminToken) {
        // 토큰이 있으면 대시보드 표시
        showDashboard();
        loadDashboardData();
    } else {
        // 토큰이 없으면 로그인 화면 표시
        showLogin();
    }
});

// 로그인 화면 표시
function showLogin() {
    document.getElementById('login-screen').classList.remove('hidden');
    document.getElementById('dashboard-screen').classList.add('hidden');
}

// 대시보드 화면 표시
function showDashboard() {
    document.getElementById('login-screen').classList.add('hidden');
    document.getElementById('dashboard-screen').classList.remove('hidden');
}

// 로그인 처리
async function handleLogin(event) {
    event.preventDefault();

    const password = document.getElementById('admin-password').value;
    const errorDiv = document.getElementById('login-error');

    try {
        const response = await fetch('/api/admin/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ password })
        });

        const data = await response.json();

        if (data.Success) {
            adminToken = data.token;
            localStorage.setItem('admin_token', adminToken);
            errorDiv.classList.add('hidden');
            showDashboard();
            loadDashboardData();
        } else {
            errorDiv.textContent = data.Reason || '로그인 실패';
            errorDiv.classList.remove('hidden');
        }
    } catch (error) {
        console.error('로그인 오류:', error);
        errorDiv.textContent = '로그인 중 오류가 발생했습니다';
        errorDiv.classList.remove('hidden');
    }
}

// 로그아웃
function handleLogout() {
    localStorage.removeItem('admin_token');
    adminToken = null;
    showLogin();
}

// 대시보드 데이터 로드
async function loadDashboardData() {
    const days = document.getElementById('days-filter').value;

    try {
        // 통계 데이터 로드
        const statsResponse = await fetch(`/api/admin/statistics?days=${days}`, {
            headers: {
                'X-Admin-Token': adminToken
            }
        });

        const statsData = await statsResponse.json();

        if (statsData.Success) {
            updateStatistics(statsData.data);
            updateCharts(statsData.data);
        } else {
            if (statsResponse.status === 401) {
                // 인증 실패 시 로그아웃
                handleLogout();
            }
        }

        // 시뮬레이션 목록 로드
        loadSimulations();

        // 에러 목록 로드
        loadErrors();

    } catch (error) {
        console.error('데이터 로드 오류:', error);
    }
}

// 통계 업데이트
function updateStatistics(stats) {
    document.getElementById('stat-total-sims').textContent = stats.total_simulations || 0;
    document.getElementById('stat-avg-efficiency').textContent =
        (stats.avg_efficiency || 0).toFixed(1) + '%';

    const totalRuns = (stats.successful_runs || 0) + (stats.failed_runs || 0);
    const successRate = totalRuns > 0 ? ((stats.successful_runs || 0) / totalRuns * 100) : 0;
    document.getElementById('stat-success-rate').textContent = successRate.toFixed(1) + '%';

    document.getElementById('stat-total-items').textContent =
        (stats.total_items_processed || 0).toLocaleString();
}

// 차트 업데이트
function updateCharts(stats) {
    // 일별 사용량 차트
    if (dailyChart) {
        dailyChart.destroy();
    }

    const dailyData = stats.daily_usage || [];
    const dailyCtx = document.getElementById('daily-chart').getContext('2d');
    dailyChart = new Chart(dailyCtx, {
        type: 'line',
        data: {
            labels: dailyData.map(d => d.date).reverse(),
            datasets: [{
                label: '시뮬레이션 수',
                data: dailyData.map(d => d.count).reverse(),
                borderColor: '#000000',
                backgroundColor: 'rgba(0, 0, 0, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                }
            }
        }
    });

    // 시간대별 사용량 차트
    if (hourlyChart) {
        hourlyChart.destroy();
    }

    const hourlyData = stats.hourly_usage || [];
    const hourlyCtx = document.getElementById('hourly-chart').getContext('2d');
    hourlyChart = new Chart(hourlyCtx, {
        type: 'bar',
        data: {
            labels: hourlyData.map(d => d.hour + '시'),
            datasets: [{
                label: '시뮬레이션 수',
                data: hourlyData.map(d => d.count),
                backgroundColor: '#000000'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                }
            }
        }
    });

    // 파레트 타입별 차트
    if (palletChart) {
        palletChart.destroy();
    }

    const palletData = stats.pallet_type_stats || [];
    const palletCtx = document.getElementById('pallet-chart').getContext('2d');
    palletChart = new Chart(palletCtx, {
        type: 'doughnut',
        data: {
            labels: palletData.map(d => d.pallet_type || '미지정'),
            datasets: [{
                data: palletData.map(d => d.count),
                backgroundColor: [
                    '#000000',
                    '#333333',
                    '#666666',
                    '#999999',
                    '#cccccc'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

// 시뮬레이션 목록 로드
async function loadSimulations() {
    try {
        const response = await fetch('/api/admin/simulations?limit=50', {
            headers: {
                'X-Admin-Token': adminToken
            }
        });

        const data = await response.json();

        if (data.Success) {
            renderSimulationsTable(data.data);
        }
    } catch (error) {
        console.error('시뮬레이션 로드 오류:', error);
    }
}

// 시뮬레이션 테이블 렌더링
function renderSimulationsTable(simulations) {
    const container = document.getElementById('simulations-table');

    if (!simulations || simulations.length === 0) {
        container.innerHTML = '<p>데이터가 없습니다.</p>';
        return;
    }

    let html = '<table class="data-table"><thead><tr>';
    html += '<th>시간</th>';
    html += '<th>파레트 타입</th>';
    html += '<th>아이템 수</th>';
    html += '<th>적재 수</th>';
    html += '<th>효율</th>';
    html += '<th>처리시간</th>';
    html += '<th>상태</th>';
    html += '</tr></thead><tbody>';

    simulations.forEach(sim => {
        html += '<tr>';
        html += `<td>${new Date(sim.timestamp).toLocaleString('ko-KR')}</td>`;
        html += `<td>${sim.pallet_type || '-'}</td>`;
        html += `<td>${sim.total_items || 0}</td>`;
        html += `<td>${sim.fitted_items || 0}</td>`;
        html += `<td>${(sim.packing_efficiency || 0).toFixed(1)}%</td>`;
        html += `<td>${(sim.processing_time || 0).toFixed(2)}s</td>`;
        html += `<td class="${sim.success ? 'status-success' : 'status-error'}">`;
        html += sim.success ? '성공' : '실패';
        html += '</td>';
        html += '</tr>';
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

// 에러 목록 로드
async function loadErrors() {
    try {
        const response = await fetch('/api/admin/errors?limit=50', {
            headers: {
                'X-Admin-Token': adminToken
            }
        });

        const data = await response.json();

        if (data.Success) {
            renderErrorsTable(data.data);
        }
    } catch (error) {
        console.error('에러 로드 오류:', error);
    }
}

// 에러 테이블 렌더링
function renderErrorsTable(errors) {
    const container = document.getElementById('errors-table');

    if (!errors || errors.length === 0) {
        container.innerHTML = '<p>에러가 없습니다.</p>';
        return;
    }

    let html = '<table class="data-table"><thead><tr>';
    html += '<th>시간</th>';
    html += '<th>타입</th>';
    html += '<th>메시지</th>';
    html += '<th>엔드포인트</th>';
    html += '</tr></thead><tbody>';

    errors.forEach(err => {
        html += '<tr>';
        html += `<td>${new Date(err.timestamp).toLocaleString('ko-KR')}</td>`;
        html += `<td>${err.error_type || '-'}</td>`;
        html += `<td>${err.error_message || '-'}</td>`;
        html += `<td>${err.endpoint || '-'}</td>`;
        html += '</tr>';
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

// 필터 변경 처리
function handleFilterChange() {
    loadDashboardData();
}

// 탭 전환
function switchTab(tabName) {
    // 모든 탭 버튼 비활성화
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });

    // 모든 탭 콘텐츠 숨기기
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });

    // 선택된 탭 활성화
    event.target.classList.add('active');
    document.getElementById(`tab-${tabName}`).classList.add('active');
}

// 데이터 내보내기
async function exportData(type) {
    const days = document.getElementById('days-filter').value;

    try {
        const response = await fetch(`/api/admin/export?type=${type}&days=${days}`, {
            headers: {
                'X-Admin-Token': adminToken
            }
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${type}_${new Date().toISOString().split('T')[0]}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        } else {
            alert('데이터 내보내기 실패');
        }
    } catch (error) {
        console.error('내보내기 오류:', error);
        alert('데이터 내보내기 중 오류가 발생했습니다');
    }
}
