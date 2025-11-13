/**
 * 3D Bin Packing 시뮬레이션 메인 앱
 * 모듈화된 구조
 */

import * as FileUpload from './modules/fileUpload.js';
import * as Simulation from './modules/simulation.js';
import * as UI from './modules/ui.js';

// 전역 상태
const state = {
    currentSessionId: null,
    currentItems: [],
    currentStats: null,
    selectedCategories: [],
    hasMasterData: false
};

// 초기화
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

/**
 * 앱 초기화
 */
function initializeApp() {
    // 이벤트 리스너 등록
    registerEventListeners();

    // 전역 오류 핸들러 설정
    setupErrorHandlers();

    // 마스터 상태 확인
    FileUpload.checkMasterStatus(state);
}

/**
 * 이벤트 리스너 등록
 */
function registerEventListeners() {
    // 마스터 파일 업로드
    const masterFileInput = document.getElementById('master-file');
    const masterUploadBtn = document.getElementById('master-upload-btn');
    if (masterFileInput) {
        masterFileInput.addEventListener('change', (e) => FileUpload.handleMasterFileSelect(e, state));
    }
    if (masterUploadBtn) {
        masterUploadBtn.addEventListener('click', () => FileUpload.handleMasterUpload(state));
    }

    // 주문서 업로드
    const orderFileInput = document.getElementById('order-file');
    const orderUploadBtn = document.getElementById('order-upload-btn');
    if (orderFileInput) {
        orderFileInput.addEventListener('change', (e) => FileUpload.handleOrderFileSelect(e, state));
    }
    if (orderUploadBtn) {
        orderUploadBtn.addEventListener('click', () => FileUpload.handleOrderUpload(state));
    }

    // CSV 업로드 (기존 방식)
    const csvFileInput = document.getElementById('csv-file');
    const uploadBtn = document.getElementById('upload-btn');
    if (csvFileInput) {
        csvFileInput.addEventListener('change', (e) => FileUpload.handleCSVFileSelect(e, state));
    }
    if (uploadBtn) {
        uploadBtn.addEventListener('click', () => FileUpload.handleCSVUpload(state));
    }

    // 시뮬레이션 실행
    const runSimBtn = document.getElementById('run-simulation-btn');
    if (runSimBtn) {
        runSimBtn.addEventListener('click', () => Simulation.runSimulation(state));
    }

    // 리포트 관련
    const downloadReportBtn = document.getElementById('download-report-btn');
    if (downloadReportBtn) {
        downloadReportBtn.addEventListener('click', () => Simulation.downloadReport(state));
    }

    const viewDetailedReportBtn = document.getElementById('view-detailed-report-btn');
    if (viewDetailedReportBtn) {
        viewDetailedReportBtn.addEventListener('click', () => Simulation.viewDetailedReport(state));
    }

    const viewWorkInstructionBtn = document.getElementById('view-work-instruction-btn');
    if (viewWorkInstructionBtn) {
        viewWorkInstructionBtn.addEventListener('click', () => Simulation.viewWorkInstruction(state));
    }

    // 파레트 모드 변경
    const isPalletCheckbox = document.getElementById('is-pallet');
    if (isPalletCheckbox) {
        isPalletCheckbox.addEventListener('change', handlePalletModeChange);
    }
}

/**
 * 파레트 모드 변경 핸들러
 */
function handlePalletModeChange(event) {
    const supportRatioInput = document.getElementById('support-ratio');
    if (!supportRatioInput) return;

    if (event.target.checked) {
        // 파레트 모드: 지지면 비율 체크 비활성화
        supportRatioInput.disabled = true;
        supportRatioInput.value = '0';
    } else {
        // 일반 모드: 지지면 비율 체크 활성화
        supportRatioInput.disabled = false;
        supportRatioInput.value = '0.75';
    }
}

/**
 * 전역 오류 핸들러 설정
 */
function setupErrorHandlers() {
    // 브라우저 확장 프로그램 오류 무시
    window.addEventListener('error', function(event) {
        if (event.message && (
            event.message.includes('message channel closed') ||
            event.message.includes('No tab with id') ||
            event.message.includes('runtime.lastError') ||
            event.message.includes('Unchecked runtime.lastError') ||
            event.message.includes('Extension context invalidated')
        )) {
            event.preventDefault();
            event.stopPropagation();
            return false;
        }
    }, true);

    // Promise rejection 무시 (확장 프로그램 관련)
    window.addEventListener('unhandledrejection', function(event) {
        const reason = event.reason;
        const message = reason?.message || reason?.toString() || '';
        if (
            message.includes('message channel closed') ||
            message.includes('No tab with id') ||
            message.includes('runtime.lastError') ||
            message.includes('Unchecked runtime.lastError') ||
            message.includes('Extension context invalidated')
        ) {
            event.preventDefault();
            event.stopPropagation();
            return false;
        }
    });

    // 콘솔 오류 필터링 (개발 환경에서만 활성화)
    if (process.env.NODE_ENV !== 'development') {
        const originalError = console.error;
        console.error = function(...args) {
            const message = args.join(' ');
            if (
                message.match(/Unchecked\s+runtime\.lastError/i) ||
                message.match(/No tab with id:\s*\d+/i) ||
                (message.includes('runtime.lastError') && message.includes('No tab with id')) ||
                message.includes('Extension context invalidated') ||
                message.includes('message channel closed')
            ) {
                return;
            }
            originalError.apply(console, args);
        };

        const originalWarn = console.warn;
        console.warn = function(...args) {
            const message = args.join(' ');
            if (
                message.match(/Unchecked\s+runtime\.lastError/i) ||
                message.match(/No tab with id:\s*\d+/i) ||
                (message.includes('runtime.lastError') && message.includes('No tab with id')) ||
                message.includes('Extension context invalidated') ||
                message.includes('message channel closed')
            ) {
                return;
            }
            originalWarn.apply(console, args);
        };
    }
}
