/**
 * 시뮬레이션 관련 모듈
 */

import * as API from './api.js';
import * as UI from './ui.js';

/**
 * 시뮬레이션 실행
 */
export async function runSimulation(state) {
    if (!state.currentSessionId) {
        UI.showStatus('먼저 CSV 파일을 업로드해주세요.', 'error');
        return;
    }

    UI.showLoading(true);

    // 박스 설정 수집
    const boxData = {
        name: document.getElementById('box-name')?.value || '20ft_Container',
        WHD: [
            parseFloat(document.getElementById('box-width')?.value || 589.8),
            parseFloat(document.getElementById('box-height')?.value || 243.8),
            parseFloat(document.getElementById('box-depth')?.value || 259.1)
        ],
        weight: parseFloat(document.getElementById('box-weight')?.value || 28080),
        coner: parseFloat(document.getElementById('box-corner')?.value || 15),
        openTop: [1],
        is_pallet: document.getElementById('is-pallet')?.checked || false
    };

    // 아이템 개수 수집
    const itemCounts = getItemCounts(state);

    // 시뮬레이션 파라미터
    const simParams = {
        bigger_first: document.getElementById('bigger-first')?.checked !== false,
        fix_point: document.getElementById('fix-point')?.checked !== false,
        check_stable: document.getElementById('check-stable')?.checked !== false,
        support_surface_ratio: parseFloat(document.getElementById('support-ratio')?.value || 0.75),
        distribute_items: true,
        use_advanced_strategy: document.getElementById('use-advanced-strategy')?.checked || false,
        try_multiple_strategies: document.getElementById('try-multiple-strategies')?.checked || false
    };

    const requestData = {
        session_id: state.currentSessionId,
        box: boxData,
        item_counts: itemCounts,
        simulation_params: simParams
    };

    try {
        const data = await API.runVisualization(requestData);

        if (data.Success) {
            UI.displayResults(data, state.currentSessionId);
            UI.showSection('results-section', true);
            UI.scrollToSection('results-section');
        } else {
            UI.showStatus(`시뮬레이션 오류: ${data.Reason}`, 'error');
        }
    } catch (error) {
        UI.showStatus(`시뮬레이션 오류: ${error.message}`, 'error');
    } finally {
        UI.showLoading(false);
    }
}

/**
 * 아이템 개수 수집
 */
function getItemCounts(state) {
    const itemCounts = {};

    // 주문서인 경우 자동으로 수량 설정
    if (state.currentItems && state.currentItems.length > 0 &&
        state.currentItems[0] && state.currentItems[0].order_quantity) {
        state.currentItems.forEach(item => {
            itemCounts[item.name] = item.order_quantity || 1;
        });
    } else {
        // 기존 방식 (직접 선택)
        document.querySelectorAll('.item-count').forEach(input => {
            const count = parseInt(input.value) || 0;
            if (count > 0) {
                itemCounts[input.dataset.name] = count;
            }
        });
    }

    return itemCounts;
}

/**
 * 리포트 다운로드
 */
export function downloadReport(state) {
    if (!state.currentSessionId) {
        UI.showStatus('리포트를 다운로드할 수 없습니다.', 'error');
        return;
    }

    window.location.href = `/api/report/${state.currentSessionId}`;
}

/**
 * 상세 보고서 보기
 */
export async function viewDetailedReport(state) {
    if (!state.currentSessionId) {
        UI.showStatus('상세 보고서를 볼 수 없습니다.', 'error');
        return;
    }

    UI.showLoading(true);

    try {
        const data = await API.getDetailedReport(state.currentSessionId);

        if (data.Success && data.reports && Array.isArray(data.reports) && data.reports.length > 0) {
            const reportsList = document.getElementById('detailed-reports-list');
            if (reportsList) {
                reportsList.style.display = 'block';

                reportsList.innerHTML = `
                    <h3>상세 보고서</h3>
                    <div class="reports-grid">
                        ${data.reports.map(report => {
                            const workInstructionUrl = `/api/workInstruction/${state.currentSessionId}/${report.bin_name}`;
                            return `
                            <div class="report-card">
                                <h4>${report.bin_name}</h4>
                                <div class="report-actions">
                                    <a href="${report.url}" target="_blank" class="btn btn-primary">
                                        📊 상세 보고서
                                    </a>
                                    <a href="${workInstructionUrl}" target="_blank" class="btn btn-secondary btn-success">
                                        🖨️ 작업 지시서
                                    </a>
                                </div>
                            </div>
                        `;
                        }).join('')}
                    </div>
                `;

                UI.scrollToSection('detailed-reports-list');
            }
        } else {
            UI.showStatus('상세 보고서를 찾을 수 없습니다.', 'error');
        }
    } catch (error) {
        UI.showStatus(`상세 보고서 조회 오류: ${error.message}`, 'error');
    } finally {
        UI.showLoading(false);
    }
}

/**
 * 작업 지시서 보기
 */
export async function viewWorkInstruction(state) {
    if (!state.currentSessionId) {
        UI.showStatus('작업 지시서를 볼 수 없습니다.', 'error');
        return;
    }

    UI.showLoading(true);

    try {
        const data = await API.getDetailedReport(state.currentSessionId);

        if (data.Success && data.reports && Array.isArray(data.reports) && data.reports.length > 0) {
            // 첫 번째 보고서의 작업 지시서 열기
            const firstReport = data.reports[0];
            if (firstReport && firstReport.bin_name) {
                const workInstructionUrl = `/api/workInstruction/${state.currentSessionId}/${firstReport.bin_name}`;
                openWindow(workInstructionUrl);

                // 여러 보고서가 있으면 모두 열기
                if (data.reports.length > 1) {
                    setTimeout(() => {
                        data.reports.slice(1).forEach((report, index) => {
                            if (report && report.bin_name) {
                                const url = `/api/workInstruction/${state.currentSessionId}/${report.bin_name}`;
                                setTimeout(() => {
                                    openWindow(url);
                                }, index * 300);
                            }
                        });
                    }, 1000);
                }
            }
        } else {
            UI.showStatus('작업 지시서를 찾을 수 없습니다.', 'error');
        }
    } catch (error) {
        UI.showStatus(`작업 지시서 조회 오류: ${error.message}`, 'error');
    } finally {
        UI.showLoading(false);
    }
}

/**
 * 새 창 열기 (팝업 차단 대응)
 */
function openWindow(url) {
    try {
        const newWindow = window.open(url, '_blank');
        if (!newWindow) {
            window.location.href = url;
        }
    } catch (error) {
        window.location.href = url;
    }
}
