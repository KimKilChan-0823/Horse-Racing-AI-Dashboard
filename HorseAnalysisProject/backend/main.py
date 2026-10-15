<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>경마 데이터 분석 시스템 (Web Dashboard)</title>
    <!-- 부트스트랩 5 CDN -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <!-- Chart.js 라이브러리 -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        .sortable { cursor: pointer; }
        .sortable:hover { background-color: #f8f9fa; }
        .progress { border-radius: 12px; background-color: #e9ecef; }
        /* 로딩 오버레이 스타일 */
        #loadingOverlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(255, 255, 255, 0.75);
            backdrop-filter: blur(4px);
            z-index: 9999;
            display: none;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }
    </style>
</head>
<body class="bg-light">
    <!-- 🌟 로딩 오버레이 -->
    <div id="loadingOverlay">
        <div class="spinner-border text-primary mb-2" style="width: 3rem; height: 3rem;" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
        <small class="text-secondary fw-bold">데이터 분석 및 실시간 배당률 계산 중...</small>
    </div>

    <div class="container my-5">
        <!-- 헤더 영역 -->
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h2><i class="fa-solid fa-horse-head text-primary"></i> 경마 데이터 분석 시스템</h2>
            <span class="badge bg-success">DB Connected (PostgreSQL)</span>
        </div>
        
        <!-- 검색 필터 카드 -->
        <div class="card p-4 mb-4 shadow-sm border-0">
            <div class="row g-3 align-items-end mb-3">
                <div class="col-md-2">
                    <label class="form-label fw-bold">경마장</label>
                    <select id="meetLoc" class="form-select" onchange="resetToOneR()">
                        <option value="전체" selected>전체</option>
                        <option value="서울">서울</option>
                        <option value="부산경남">부경</option>
                        <option value="제주">제주</option>
                        <option value="영천">영천</option>
                    </select>
                </div>
                <div class="col-md-3">
                    <label class="form-label fw-bold">경주 날짜</label>
                    <input type="date" id="meetDate" class="form-control" onchange="handleDateChange()">
                </div>
                <div class="col-md-2">
                    <label class="form-label fw-bold text-info"><i class="fa-solid fa-cloud-sun"></i> 예상 날씨</label>
                    <select id="weather" class="form-select border-info" onchange="fetchAnalysisData()">
                        <option value="맑음">☀️ 맑음</option>
                        <option value="흐림">☁️ 흐림</option>
                        <option value="비">🌧️ 비</option>
                        <option value="눈">❄️ 눈</option>
                    </select>
                </div>
                <div class="col-md-2">
                    <label class="form-label fw-bold text-info"><i class="fa-solid fa-road"></i> 마장 상태</label>
                    <select id="trackCond" class="form-select border-info" onchange="fetchAnalysisData()">
                        <option value="건조">건조 (1~5%)</option>
                        <option value="다습">다습 (6~9%)</option>
                        <option value="포화">포화 (10~14%)</option>
                        <option value="불량">불량 (15%~)</option>
                    </select>
                </div>
                <div class="col-md-3">
                    <label class="form-label fw-bold">마명 검색</label>
                    <input type="text" id="horseFilter" class="form-control" placeholder="말 이름 검색..." oninput="filterTable()">
                </div>
            </div>
            
            <!-- 경주 버튼 및 정렬 토글 버튼 영역 -->
            <div class="row mt-2 align-items-end border-top pt-3">
                <div class="col-md-9">
                    <label class="form-label fw-bold text-secondary mb-2">해당 일자 경주 선택</label>
                    <div class="d-flex flex-wrap gap-2" id="raceButtons">
                        <!-- 자바스크립트로 1R ~ 15R 버튼 자동 생성 -->
                    </div>
                </div>
                <div class="col-md-3 text-end">
                    <button id="sortToggleBtn" class="btn btn-outline-primary fw-bold w-100" onclick="toggleSort()">
                        <i class="fa-solid fa-arrow-down-1-9"></i> 정렬: 마번순
                    </button>
                </div>
            </div>
        </div>

        <!-- 데이터 시각화 (레이더 차트) 영역 -->
        <div class="card p-3 mb-4 shadow-sm border-0 bg-white" id="chartContainer" style="display: none;">
            <h5 class="fw-bold text-center mb-3">🔥 TOP 3 마필 역량 분석 (LightGBM 확률 기준)</h5>
            <div style="height: 350px; display: flex; justify-content: center;">
                <canvas id="radarChart"></canvas>
            </div>
        </div>

        <!-- AI 승식 추천 영역 -->
        <div class="card p-3 mb-4 shadow-sm border-0" id="bettingContainer" style="display: none; background-color: #fffaf0; border-left: 5px solid #ffc107 !important;">
            <h5 class="fw-bold text-dark mb-3"><i class="fa-solid fa-coins text-warning"></i> 🤖 AI 맞춤 마권(승식) 추천</h5>
            <div class="row text-center align-items-center">
                <div class="col-md-4 border-end">
                    <p class="mb-1 text-secondary fw-bold">🏇 단승/연승식 (1등/입상마 1마리)</p>
                    <h4 class="text-primary mb-0 fw-bold" id="betSingle">-</h4>
                </div>
                <div class="col-md-4 border-end">
                    <p class="mb-1 text-secondary fw-bold">🏇 복승/쌍승식 (1, 2등 2마리)</p>
                    <h4 class="text-danger mb-0 fw-bold" id="betDouble">-</h4>
                </div>
                <div class="col-md-4">
                    <p class="mb-1 text-secondary fw-bold">🏇 삼복/삼쌍승식 (1, 2, 3등 3마리)</p>
                    <h4 class="text-success mb-0 fw-bold" id="betTrio">-</h4>
                </div>
            </div>
            <p class="text-end text-muted mt-2 mb-0" style="font-size: 0.8rem;">※ LightGBM 예측 확률 최상위 마필 조합입니다. (참고용)</p>
        </div>

        <!-- 데이터 그리드 카드 -->
        <div class="card shadow-sm border-0">
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-hover align-middle text-center">
                        <thead class="table-dark">
                            <tr>
                                <th class="sortable" onclick="sortTable('horse_no')">마번 <i class="fa-solid fa-sort"></i></th>
                                <th class="sortable" onclick="sortTable('horse_name')">마명 <i class="fa-solid fa-sort"></i></th>
                                <th class="sortable" onclick="sortTable('jk_top3_rate')">기수 (입상률) <i class="fa-solid fa-sort"></i></th>
                                <th class="sortable" onclick="sortTable('wg_budam')">부중 <i class="fa-solid fa-sort"></i></th>
                                <th class="sortable" onclick="sortTable('top3_rate')">마필 입상률 <i class="fa-solid fa-sort"></i></th>
                                <th class="sortable" onclick="sortTable('best_time')">최고기록 <i class="fa-solid fa-sort"></i></th>
                                <th class="sortable" onclick="sortTable('actual_rank')">🏁 결과 <i class="fa-solid fa-sort"></i></th>
                                <th class="sortable" onclick="sortTable('pred_score_lgbm')" style="width: 14%;">🚀 LightGBM 확률 <i class="fa-solid fa-sort"></i></th>
                                <th class="sortable" onclick="sortTable('pred_score_rf')" style="width: 14%;">🤖 RF 확률 <i class="fa-solid fa-sort"></i></th>
                                <th>단승 배당</th>
                                <th>💰 기댓값(EV)</th>
                            </tr>
                        </thead>
                        <tbody id="resultTable">
                            <tr><td colspan="11" class="text-muted py-4">데이터를 불러오는 중입니다...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <!-- 자바스크립트 로직 -->
    <script>
        // 🌟 [핵심] 로컬/배포 환경 자동 분기
        // 파일 직접 열기(file:) 또는 127.0.0.1:5500(Live Server) 등 로컬 환경일 때만 로컬 백엔드(8000)를 바라봄
        // Render 도메인(onrender.com)에서는 빈 문자열('')로 동작하여 자기 도메인의 API를 호출함
        const isLocalHost = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') && window.location.port !== '10000';
        const API_BASE_URL = (window.location.protocol === 'file:' || isLocalHost) ? 'http://127.0.0.1:8000' : '';

        let allData = []; 
        let currentOdds = {}; 
        let currentRaceNo = 1; 
        let sortMode = 'horse_no'; 
        let sortDirection = false;
        let radarChartInstance = null; 

        window.onload = async function() {
            document.getElementById('meetDate').value = '2026-10-11';
            
            renderRaceButtons();
            await autoSetWeather();
            fetchAnalysisData();
        };

        function renderRaceButtons() {
            const container = document.getElementById('raceButtons');
            container.innerHTML = ''; 
            for (let i = 1; i <= 15; i++) {
                const btn = document.createElement('button');
                btn.className = `btn ${i === currentRaceNo ? 'btn-primary' : 'btn-outline-secondary'} fw-bold px-3`;
                btn.innerText = `${i}R`;
                btn.onclick = () => {
                    currentRaceNo = i;
                    renderRaceButtons(); 
                    fetchAnalysisData(); 
                };
                container.appendChild(btn);
            }
        }

        async function resetToOneR() {
            currentRaceNo = 1;
            renderRaceButtons();
            await autoSetWeather(); 
            fetchAnalysisData();
        }

        function showLoading(isLoading) {
            const overlay = document.getElementById('loadingOverlay');
            if (overlay) {
                overlay.style.display = isLoading ? 'flex' : 'none';
            }
        }

        async function fetchAnalysisData() {
            showLoading(true);

            const loc = document.getElementById('meetLoc').value;
            const date = document.getElementById('meetDate').value;
            const weather = document.getElementById('weather').value;
            const trackCond = document.getElementById('trackCond').value;
            
            const analysisUrl = `${API_BASE_URL}/api/analysis?meet_date=${date}&meet_loc=${encodeURIComponent(loc)}&race_no=${currentRaceNo}&weather=${encodeURIComponent(weather)}&track_cond=${encodeURIComponent(trackCond)}`;
            const oddsUrl = `${API_BASE_URL}/api/odds?meet_loc=${encodeURIComponent(loc)}&race_no=${currentRaceNo}`;

            try {
                const [analysisRes, oddsRes] = await Promise.all([
                    fetch(analysisUrl),
                    fetch(oddsUrl).catch(() => ({ json: () => ({ odds: {} }) }))
                ]);

                if (!analysisRes.ok) {
                    throw new Error(`HTTP 상태 코드: ${analysisRes.status}`);
                }

                const analysisJson = await analysisRes.json();
                const oddsJson = await oddsRes.json();

                allData = analysisJson.data || []; 
                currentOdds = oddsJson.odds || {}; 

                applySortAndRender(); 
                drawRadarChart(); 
                renderBettingRecommendation();
            } catch (error) {
                console.error('API 호출 오류:', error);
                alert('서버 연결 실패: ' + error.message);
            } finally {
                showLoading(false);
            }
        }

        function toggleSort() {
            const btn = document.getElementById('sortToggleBtn');
            if (sortMode === 'horse_no') {
                sortMode = 'pred_score_lgbm';
                btn.innerHTML = '<i class="fa-solid fa-star"></i> 정렬: 예측 확률순';
                btn.className = 'btn btn-primary fw-bold w-100';
            } else {
                sortMode = 'horse_no';
                btn.innerHTML = '<i class="fa-solid fa-arrow-down-1-9"></i> 정렬: 마번순';
                btn.className = 'btn btn-outline-primary fw-bold w-100';
            }
            applySortAndRender(); 
        }

        function applySortAndRender() {
            if (sortMode === 'pred_score_lgbm') {
                allData.sort((a, b) => b.pred_score_lgbm - a.pred_score_lgbm);
            } else {
                allData.sort((a, b) => {
                    if (a.meet_loc !== b.meet_loc) {
                        return (a.meet_loc || '').localeCompare(b.meet_loc || '');
                    }
                    return parseInt(a.horse_no) - parseInt(b.horse_no);
                });
            }
            filterTable(); 
        }

        function renderTable(data) {
            const tbody = document.getElementById('resultTable');
            tbody.innerHTML = '';

            if (!data || data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="11" class="text-muted py-4">조회된 출전마 정보가 없습니다.</td></tr>';
                document.getElementById('chartContainer').style.display = 'none'; 
                document.getElementById('bettingContainer').style.display = 'none';
                return;
            }

            data.forEach(item => {
                let lgbmColor = item.pred_score_lgbm >= 50 ? 'bg-success' : (item.pred_score_lgbm >= 20 ? 'bg-warning' : 'bg-danger');
                let rfColor = item.pred_score_rf >= 50 ? 'bg-success' : (item.pred_score_rf >= 20 ? 'bg-warning' : 'bg-danger');
                
                let actualRankHtml = '<span class="text-muted">-</span>'; 
                if (item.actual_rank) {
                    const rank = parseInt(item.actual_rank);
                    if (rank === 1) actualRankHtml = '<span class="badge bg-warning text-dark fs-6" style="background-color: #ffd700 !important;">🥇 1착</span>';
                    else if (rank === 2) actualRankHtml = '<span class="badge bg-secondary fs-6" style="background-color: #c0c0c0 !important;">🥈 2착</span>';
                    else if (rank === 3) actualRankHtml = '<span class="badge bg-danger fs-6" style="background-color: #cd7f32 !important;">🥉 3착</span>';
                    else actualRankHtml = `<span class="badge bg-light text-dark border">${rank}착</span>`;
                }

                const horseNoStr = String(item.horse_no);
                const odds = currentOdds[horseNoStr] || 0;
                
                let oddsHtml = '<span class="text-muted">-</span>';
                let evHtml = '<span class="badge bg-light text-muted border">배당 없음</span>';
                let rowClass = '';

                if (odds > 0) {
                    oddsHtml = `<span class="fw-bold text-primary">${odds}배</span>`;
                    const ev = (item.pred_score_lgbm / 100) * odds;
                    const evPercent = (ev * 100).toFixed(0);

                    if (ev >= 1.2) {
                        evHtml = `<span class="badge bg-danger fs-6">🔥 ${evPercent}%</span>`;
                        rowClass = 'table-warning';
                    } else if (ev >= 1.0) {
                        evHtml = `<span class="badge bg-success fs-6">👍 ${evPercent}%</span>`;
                    } else {
                        evHtml = `<span class="badge bg-secondary">${evPercent}%</span>`;
                    }
                }

                const locName = item.meet_loc || '부산경남';
                let locBadgeClass = 'bg-primary text-white';
                if (locName.includes('부산') || locName.includes('부경')) {
                    locBadgeClass = 'bg-info text-dark';
                } else if (locName.includes('제주')) {
                    locBadgeClass = 'bg-warning text-dark';
                }

                const horseNoDisplay = `
                    <div class="d-inline-flex align-items-center justify-content-center gap-1">
                        <span class="badge ${locBadgeClass} shadow-sm" style="font-size: 0.72rem; padding: 4px 6px;">${locName}</span>
                        <span class="badge rounded-circle bg-dark text-white fw-bold d-inline-flex align-items-center justify-content-center shadow-sm" style="width: 26px; height: 26px; font-size: 0.85rem;">
                            ${item.horse_no}
                        </span>
                    </div>
                `;

                tbody.innerHTML += `
                    <tr class="${rowClass}">
                        <td class="align-middle">${horseNoDisplay}</td>
                        <td><strong>${item.horse_name}</strong> <span class="badge bg-secondary" style="font-size:0.7em;">${item.total_races}전</span></td>
                        <td>${item.jockey_name} <br><small class="text-muted">(${parseFloat(item.jk_top3_rate).toFixed(1)}%)</small></td>
                        <td>${item.wg_budam}</td>
                        <td><span class="badge bg-dark">${parseFloat(item.top3_rate).toFixed(1)}%</span></td>
                        <td class="text-success fw-bold">${formatTime(item.best_time)}</td>
                        <td class="align-middle">${actualRankHtml}</td>
                        
                        <td class="align-middle">
                            <div class="progress position-relative" style="height: 25px; box-shadow: inset 0 1px 2px rgba(0,0,0,.1);">
                                <div class="progress-bar ${lgbmColor}" role="progressbar" style="width: ${item.pred_score_lgbm}%;"></div>
                                <div class="position-absolute w-100 h-100 d-flex align-items-center justify-content-center fw-bold" style="color: #000; text-shadow: 1px 1px 2px rgba(255,255,255,0.9);">
                                    ${item.pred_score_lgbm}%
                                </div>
                            </div>
                        </td>
                        
                        <td class="align-middle">
                            <div class="progress position-relative" style="height: 25px; box-shadow: inset 0 1px 2px rgba(0,0,0,.1);">
                                <div class="progress-bar ${rfColor}" role="progressbar" style="width: ${item.pred_score_rf}%;"></div>
                                <div class="position-absolute w-100 h-100 d-flex align-items-center justify-content-center fw-bold" style="color: #000; text-shadow: 1px 1px 2px rgba(255,255,255,0.9);">
                                    ${item.pred_score_rf}%
                                </div>
                            </div>
                        </td>
                        
                        <td class="align-middle">${oddsHtml}</td>
                        <td class="align-middle">${evHtml}</td>
                    </tr>
                `;
            });
        }

        function filterTable() {
            const keyword = document.getElementById('horseFilter').value.trim();
            const filtered = allData.filter(item => item.horse_name.includes(keyword));
            renderTable(filtered);
        }

        function sortTable(key) {
            sortDirection = !sortDirection;
            allData.sort((a, b) => {
                let valA = a[key];
                let valB = b[key];
                if (typeof valA === 'string') {
                    return sortDirection ? valA.localeCompare(valB) : valB.localeCompare(valA);
                } else {
                    return sortDirection ? valA - valB : valB - valA;
                }
            });
            renderTable(allData);
        }

        function formatTime(totalSec) {
            if (!totalSec || totalSec === 0) return '-';
            const mins = Math.floor(totalSec / 60);
            const secs = (totalSec % 60).toFixed(1);
            return mins > 0 ? `${mins}분 ${secs}초` : `${secs}초`;
        }

        function drawRadarChart() {
            const chartBox = document.getElementById('chartContainer');
            const selectedLoc = document.getElementById('meetLoc').value;

            // '전체' 선택 시 또는 데이터가 3마리 미만일 때 숨김
            if (selectedLoc === '전체' || !allData || allData.length < 3) {
                chartBox.style.display = 'none';
                return;
            }
            
            chartBox.style.display = 'block';
            
            const top3 = [...allData].sort((a, b) => b.pred_score_lgbm - a.pred_score_lgbm).slice(0, 3);
            const ctx = document.getElementById('radarChart').getContext('2d');
            
            if (radarChartInstance) {
                radarChartInstance.destroy();
            }

            const colors = [
                { border: 'rgba(255, 99, 132, 1)', bg: 'rgba(255, 99, 132, 0.2)' },
                { border: 'rgba(54, 162, 235, 1)', bg: 'rgba(54, 162, 235, 0.2)' }, 
                { border: 'rgba(255, 206, 86, 1)', bg: 'rgba(255, 206, 86, 0.2)' } 
            ];

            const datasets = top3.map((horse, index) => {
                return {
                    label: `${horse.horse_no}번 ${horse.horse_name} (${horse.pred_score_lgbm}%)`,
                    data: [
                        horse.top3_rate, 
                        horse.jk_top3_rate, 
                        horse.tr_top3_rate, 
                        horse.jt_top3_rate, 
                        horse.hr_wet_top3_rate
                    ],
                    borderColor: colors[index].border,
                    backgroundColor: colors[index].bg,
                    borderWidth: 2,
                    pointRadius: 4
                };
            });

            radarChartInstance = new Chart(ctx, {
                type: 'radar',
                data: {
                    labels: ['마필 역량', '기수 역량', '조교사 역량', '기수+조교사 궁합', '수중전(진흙탕) 능력'],
                    datasets: datasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        r: {
                            angleLines: { display: true },
                            suggestedMin: 0,
                            suggestedMax: 100 
                        }
                    }
                }
            });
        }

        async function autoSetWeather() {
            const loc = document.getElementById('meetLoc').value;
            const date = document.getElementById('meetDate').value;

            const coords = {
                '전체': { lat: 37.429, lon: 127.016 },
                '서울': { lat: 37.429, lon: 127.016 },
                '부산경남': { lat: 35.153, lon: 128.877 },
                '제주': { lat: 33.415, lon: 126.402 },
                '영천': { lat: 35.973, lon: 128.938 }
            };
            const targetCoord = coords[loc] || coords['전체'];
            
            try {
                const res = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${targetCoord.lat}&longitude=${targetCoord.lon}&daily=weather_code,precipitation_sum&timezone=Asia%2FSeoul&start_date=${date}&end_date=${date}`);
                const data = await res.json();
                
                if (data && data.daily && data.daily.weather_code) {
                    const code = data.daily.weather_code[0];
                    const rainMM = data.daily.precipitation_sum[0] || 0; 
                    
                    let weatherStr = '맑음';
                    if (code <= 3) weatherStr = '맑음';
                    else if (code === 45 || code === 48) weatherStr = '흐림';
                    else if ((code >= 51 && code <= 67) || (code >= 80 && code <= 82) || code >= 95) weatherStr = '비';
                    else if ((code >= 71 && code <= 77) || (code >= 85 && code <= 86)) weatherStr = '눈';

                    document.getElementById('weather').value = weatherStr;
                    
                    let trackStr = '건조';
                    if (rainMM === 0) trackStr = '건조'; 
                    else if (rainMM <= 5) trackStr = '다습'; 
                    else if (rainMM <= 15) trackStr = '포화'; 
                    else trackStr = '불량'; 
                    
                    document.getElementById('trackCond').value = trackStr;
                }
            } catch (e) {
                console.error('날씨 연동 실패 (기본값 유지):', e);
            }
        }

        function renderBettingRecommendation() {
            const container = document.getElementById('bettingContainer');
            const selectedLoc = document.getElementById('meetLoc').value;

            // '전체' 선택 시 또는 데이터가 3마리 미만일 때 숨김
            if (selectedLoc === '전체' || !allData || allData.length < 3) {
                container.style.display = 'none';
                return;
            }

            const top3 = [...allData].sort((a, b) => b.pred_score_lgbm - a.pred_score_lgbm).slice(0, 3);
            const h1 = top3[0];
            const h2 = top3[1];
            const h3 = top3[2];

            document.getElementById('betSingle').innerHTML = `${h1.horse_no}번 <span style="font-size:0.7em">(${h1.horse_name})</span>`;
            document.getElementById('betDouble').innerHTML = `${h1.horse_no}번 - ${h2.horse_no}번`;
            document.getElementById('betTrio').innerHTML = `${h1.horse_no}번 - ${h2.horse_no}번 - ${h3.horse_no}번`;

            container.style.display = 'block';
        }

        async function handleDateChange() {
            document.getElementById('meetLoc').value = '전체';
            await resetToOneR();
        }
    </script>
</body>
</html>