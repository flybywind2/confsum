// localStorage 기본 기능 테스트
console.log('🧪 localStorage 테스트 시작');
try {
    localStorage.setItem('test', 'working');
    const testValue = localStorage.getItem('test');
    console.log('✅ localStorage 작동:', testValue);
    localStorage.removeItem('test');
} catch (e) {
    console.error('❌ localStorage 오류:', e);
}

class ConfluenceController {
    constructor() {
        console.log('🚀 ConfluenceController 생성자 시작');
        this.connectionStatus = false;
        this.currentTaskId = null;
        this.statusCheckInterval = null;
        console.log('🔥 init() 메서드 호출 직전');
        try {
            this.init();
            console.log('✅ init() 메서드 호출 완료');
        } catch (error) {
            console.error('❌ init() 메서드 호출 중 오류:', error);
        }
        console.log('✅ ConfluenceController 생성자 완료');
    }
    
    init() {
        console.log('🚀 ConfluenceController.init() 시작');
        this.bindEvents();
        console.log('🔥 loadSavedConnection 호출 직전');
        this.loadSavedConnection();
        console.log('🔥 loadSavedConnection 호출 직후');
        this.updateLog("시스템 초기화 완료");
        console.log('✅ ConfluenceController.init() 완료');
    }
    
    bindEvents() {
        // 기본 이벤트들
        const testConnectionBtn = document.getElementById('testConnection');
        const processForm = document.getElementById('processForm');
        const viewMindmapBtn = document.getElementById('viewMindmap');
        const downloadResultsBtn = document.getElementById('downloadResults');
        
        if (testConnectionBtn) {
            testConnectionBtn.addEventListener('click', () => this.testConnection());
        }
        if (processForm) {
            processForm.addEventListener('submit', (e) => this.processPages(e));
        }
        if (viewMindmapBtn) {
            viewMindmapBtn.addEventListener('click', () => this.viewMindmap());
        }
        if (downloadResultsBtn) {
            downloadResultsBtn.addEventListener('click', () => this.downloadResults());
        }
        
        // 마인드맵 버튼들 - 지연 등록으로 변경
        setTimeout(() => {
            this.bindMindmapButtons();
        }, 100);
    }
    
    bindMindmapButtons() {
        // 이 메서드는 더 이상 사용하지 않음 (DOMContentLoaded에서 직접 처리)
        console.log('bindMindmapButtons 메서드 호출됨 (현재 사용하지 않음)');
    }
    
    async testConnection() {
        const url = document.getElementById('confluenceUrl').value;
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        
        if (!url || !username || !password) {
            this.showMessage('connectionStatus', '모든 필드를 입력해주세요.', 'error');
            return;
        }
        
        const testButton = document.getElementById('testConnection');
        testButton.disabled = true;
        testButton.innerHTML = '<span class="loading"></span> 연결 테스트 중...';
        
        this.updateLog(`연결 테스트 시작: ${url}`);
        
        try {
            const response = await fetch('/test-connection', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({url, username, password})
            });
            
            const result = await response.json();
            this.updateConnectionStatus(result);
            
            if (result.status === 'success') {
                this.updateLog(`연결 성공: ${result.message}`);
                
                // localStorage에 연결 정보 저장
                console.log('🔥 연결 성공 - localStorage 저장 시작');
                this.saveConnectionToStorage(url, username, password, true);
            } else {
                this.updateLog(`연결 실패: ${result.message}`);
                
                // 연결 실패 시에도 입력 정보는 저장 (연결 상태는 false)
                console.log('🔥 연결 실패 - localStorage 저장 시작');
                this.saveConnectionToStorage(url, username, password, false);
            }
            
        } catch (error) {
            this.updateConnectionStatus({status: 'failed', message: `연결 오류: ${error.message}`});
            this.updateLog(`연결 오류: ${error.message}`);
            
            // 연결 오류 시에도 입력 정보는 저장 (연결 상태는 false)
            console.log('🔥 연결 오류 - localStorage 저장 시작');
            this.saveConnectionToStorage(url, username, password, false);
        } finally {
            testButton.disabled = false;
            testButton.innerHTML = '연결 테스트';
        }
    }
    
    async processPages(event) {
        event.preventDefault();
        
        if (!this.connectionStatus) {
            this.showMessage('processStatus', '먼저 Confluence 연결을 테스트해주세요.', 'error');
            return;
        }
        
        const pageId = document.getElementById('pageId').value;
        const url = document.getElementById('confluenceUrl').value;
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        
        if (!pageId) {
            this.showMessage('processStatus', '페이지 ID를 입력해주세요.', 'error');
            return;
        }
        
        const processButton = document.getElementById('processPages');
        processButton.disabled = true;
        processButton.innerHTML = '<span class="loading"></span> 처리 중...';
        
        this.updateLog(`페이지 처리 시작: ${pageId}`);
        this.showProgressBar();
        
        try {
            // localStorage에서 연결 정보 가져오기
            const savedConnection = localStorage.getItem('confluence_connection');
            let requestBody = {};
            
            if (savedConnection) {
                const connectionInfo = JSON.parse(savedConnection);
                requestBody = {
                    confluence_url: connectionInfo.url,
                    username: connectionInfo.username,
                    password: connectionInfo.password
                };
            }
            
            const response = await fetch(`/process-pages/${pageId}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(requestBody)
            });
            
            const result = await response.json();
            this.currentTaskId = result.task_id;
            
            this.showMessage('processStatus', `처리 시작됨 (Task ID: ${result.task_id})`, 'info');
            this.updateLog(`백그라운드 작업 시작: ${result.task_id}`);
            
            this.startStatusPolling();
            
        } catch (error) {
            this.showMessage('processStatus', `처리 시작 실패: ${error.message}`, 'error');
            this.updateLog(`처리 오류: ${error.message}`);
            this.hideProgressBar();
        } finally {
            processButton.disabled = false;
            processButton.innerHTML = '처리 시작';
        }
    }
    
    startStatusPolling() {
        if (this.statusCheckInterval) {
            clearInterval(this.statusCheckInterval);
        }
        
        this.statusCheckInterval = setInterval(async () => {
            if (!this.currentTaskId) return;
            
            try {
                const response = await fetch(`/status/${this.currentTaskId}`);
                const status = await response.json();
                
                this.updateProgress(status.progress);
                
                if (status.status === 'completed') {
                    this.handleProcessComplete(status);
                } else if (status.status === 'failed') {
                    this.handleProcessFailed(status);
                }
                
            } catch (error) {
                this.updateLog(`상태 확인 오류: ${error.message}`);
            }
        }, 2000); // 2초마다 상태 확인
    }
    
    updateProgress(progress) {
        if (!progress) return;
        
        const percentage = progress.total > 0 ? Math.round((progress.completed / progress.total) * 100) : 0;
        
        const progressFill = document.querySelector('.progress-fill');
        const progressText = document.querySelector('.progress-text');
        
        if (progressFill && progressText) {
            progressFill.style.width = `${percentage}%`;
            progressText.textContent = `${percentage}% (${progress.completed}/${progress.total})`;
        }
        
        this.updateLog(`진행률: ${percentage}% (${progress.completed}/${progress.total})`);
    }
    
    handleProcessComplete(status) {
        clearInterval(this.statusCheckInterval);
        this.statusCheckInterval = null;
        
        this.showMessage('processStatus', '페이지 처리가 완료되었습니다!', 'success');
        this.updateLog(`처리 완료: ${status.processed_at}`);
        
        // 결과 버튼 활성화
        document.getElementById('viewMindmap').disabled = false;
        document.getElementById('downloadResults').disabled = false;
        
        // 결과 표시
        this.loadResults();
        
        this.hideProgressBar();
    }
    
    handleProcessFailed(status) {
        clearInterval(this.statusCheckInterval);
        this.statusCheckInterval = null;
        
        this.showMessage('processStatus', `페이지 처리 실패: ${status.error || '알 수 없는 오류'}`, 'error');
        this.updateLog(`처리 실패: ${status.error || '알 수 없는 오류'}`);
        
        this.hideProgressBar();
    }
    
    async loadResults() {
        const pageId = document.getElementById('pageId').value;
        
        try {
            const response = await fetch(`/summary/${pageId}`);
            if (response.ok) {
                const summary = await response.json();
                this.displayResults(summary);
            }
        } catch (error) {
            this.updateLog(`결과 로드 오류: ${error.message}`);
        }
    }
    
    displayResults(summary) {
        const resultsContainer = document.getElementById('results');
        
        const resultHtml = `
            <div class="result-item">
                <h4>${summary.title}</h4>
                <p><strong>페이지 ID:</strong> ${summary.page_id}</p>
                <p><strong>요약:</strong> ${summary.summary}</p>
                <div class="keywords">
                    <strong>키워드:</strong>
                    ${summary.keywords.map(keyword => `<span class="keyword">${keyword}</span>`).join('')}
                </div>
                <p><strong>URL:</strong> <a href="${summary.url}" target="_blank">${summary.url}</a></p>
            </div>
        `;
        
        resultsContainer.innerHTML = resultHtml;
    }
    
    updateConnectionStatus(result) {
        const statusDiv = document.getElementById('connectionStatus');
        statusDiv.className = `status-message ${result.status === 'success' ? 'success' : 'error'}`;
        statusDiv.textContent = result.message;
        statusDiv.style.display = 'block';
        
        this.connectionStatus = result.status === 'success';
        
        // 페이지 처리 버튼 활성화/비활성화
        const processButton = document.getElementById('processPages');
        if (processButton) {
            processButton.disabled = !this.connectionStatus;
        }
        
        // 프로세스 섹션 표시/숨김
        const processSection = document.getElementById('processSection');
        if (processSection) {
            processSection.style.display = this.connectionStatus ? 'block' : 'none';
        }
    }
    
    showMessage(elementId, message, type) {
        const element = document.getElementById(elementId);
        element.className = `status-message ${type}`;
        element.textContent = message;
        element.style.display = 'block';
    }
    
    showProgressBar() {
        const progressBar = document.getElementById('progressBar');
        progressBar.style.display = 'block';
    }
    
    hideProgressBar() {
        const progressBar = document.getElementById('progressBar');
        progressBar.style.display = 'none';
    }
    
    updateLog(message) {
        const logContent = document.getElementById('logContent');
        const timestamp = new Date().toLocaleTimeString();
        const logMessage = `[${timestamp}] ${message}\n`;
        
        logContent.textContent += logMessage;
        logContent.scrollTop = logContent.scrollHeight;
    }
    
    viewMindmap() {
        const pageId = document.getElementById('pageId').value;
        if (pageId) {
            window.open(`/mindmap?parent_id=${pageId}`, '_blank');
        }
    }
    
    async viewAllMindmap() {
        console.log('viewAllMindmap 메서드 호출됨');
        this.updateLog('전체 마인드맵 로딩 중...');
        
        try {
            // 데이터베이스에 저장된 페이지가 있는지 확인
            console.log('페이지 통계 조회 중...');
            const response = await fetch('/pages/stats');
            const stats = await response.json();
            console.log('페이지 통계:', stats);
            
            if (stats.total_pages === 0) {
                alert('저장된 페이지가 없습니다. 먼저 Confluence 페이지를 처리해주세요.');
                return;
            }
            
            // 전체 마인드맵 페이지로 이동
            console.log('전체 마인드맵 페이지로 이동 중...');
            window.open('/mindmap?mode=all', '_blank');
            this.updateLog(`전체 마인드맵 열기 (총 ${stats.total_pages}개 페이지)`);
            
        } catch (error) {
            console.error('전체 마인드맵 오류:', error);
            this.updateLog(`전체 마인드맵 오류: ${error.message}`);
            alert('전체 마인드맵을 불러오는 중 오류가 발생했습니다.');
        }
    }
    
    viewSpecificMindmap() {
        console.log('viewSpecificMindmap 메서드 호출됨');
        const pageId = prompt('마인드맵을 생성할 페이지 ID를 입력하세요:');
        
        if (!pageId) {
            console.log('페이지 ID 입력 취소됨');
            return;
        }
        
        console.log('입력된 페이지 ID:', pageId);
        
        if (!/^\d+$/.test(pageId.trim())) {
            alert('유효한 페이지 ID를 입력해주세요. (숫자만)');
            return;
        }
        
        console.log('유효한 페이지 ID, 마인드맵 페이지로 이동 중...');
        this.updateLog(`특정 페이지 마인드맵 열기: ${pageId}`);
        window.open(`/mindmap?parent_id=${pageId.trim()}`, '_blank');
    }
    
    async viewKeywordMindmap() {
        console.log('🔥 viewKeywordMindmap 메서드 시작 - 전체 키워드 마인드맵으로 변경');
        this.updateLog('전체 키워드 마인드맵 로딩 중...');
        
        try {
            // 데이터베이스에 저장된 페이지가 있는지 확인
            console.log('📊 페이지 통계 조회 중...');
            const response = await fetch('/pages/stats');
            const stats = await response.json();
            console.log('📈 페이지 통계:', stats);
            
            if (stats.total_pages === 0) {
                alert('저장된 페이지가 없습니다. 먼저 Confluence 페이지를 처리해주세요.');
                return;
            }
            
            // 전체 키워드 마인드맵 페이지로 이동 (키워드 네트워크 모드)
            console.log('🌐 전체 키워드 마인드맵 페이지로 이동 중...');
            window.open('/mindmap?mode=all_keywords', '_blank');
            this.updateLog(`전체 키워드 마인드맵 열기 (총 ${stats.total_pages}개 페이지, ${stats.total_unique_keywords}개 키워드)`);
            
        } catch (error) {
            console.error('❌ 키워드 마인드맵 오류:', error);
            this.updateLog(`키워드 마인드맵 오류: ${error.message}`);
            alert('키워드 마인드맵을 불러오는 중 오류가 발생했습니다.');
        }
    }
    
    showKeywordSelectionModal(keywords) {
        // 기존 모달이 있으면 제거
        const existingModal = document.getElementById('keywordModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // 모달 HTML 생성
        const modalHtml = `
            <div id="keywordModal" style="
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.5);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 1000;
            ">
                <div style="
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    max-width: 600px;
                    max-height: 80vh;
                    overflow-y: auto;
                    width: 90%;
                ">
                    <h3>키워드 선택</h3>
                    <p>마인드맵을 생성할 키워드를 선택하세요:</p>
                    <div style="
                        max-height: 300px;
                        overflow-y: auto;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                        padding: 10px;
                        margin: 10px 0;
                    ">
                        ${keywords.slice(0, 50).map((keyword, index) => `
                            <label style="
                                display: block;
                                padding: 5px;
                                cursor: pointer;
                                border-bottom: 1px solid #eee;
                            ">
                                <input type="radio" name="selectedKeyword" value="${keyword}" style="margin-right: 8px;">
                                ${keyword} 
                                <small style="color: #666;">(빈도: ${index + 1})</small>
                            </label>
                        `).join('')}
                    </div>
                    <div style="text-align: center; margin-top: 15px;">
                        <button id="confirmKeyword" class="btn btn-primary" style="margin-right: 10px;">마인드맵 생성</button>
                        <button id="cancelKeyword" class="btn btn-secondary">취소</button>
                    </div>
                </div>
            </div>
        `;
        
        // 모달을 body에 추가
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // 이벤트 리스너 등록
        const modal = document.getElementById('keywordModal');
        const confirmBtn = document.getElementById('confirmKeyword');
        const cancelBtn = document.getElementById('cancelKeyword');
        
        confirmBtn.addEventListener('click', () => {
            const selectedKeyword = document.querySelector('input[name="selectedKeyword"]:checked');
            if (selectedKeyword) {
                const keyword = selectedKeyword.value;
                console.log('선택된 키워드:', keyword);
                this.updateLog(`키워드 마인드맵 열기: ${keyword}`);
                window.open(`/mindmap?mode=keyword&keyword=${encodeURIComponent(keyword)}`, '_blank');
                modal.remove();
            } else {
                alert('키워드를 선택해주세요.');
            }
        });
        
        cancelBtn.addEventListener('click', () => {
            modal.remove();
        });
        
        // 모달 외부 클릭 시 닫기
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
    }
    
    downloadResults() {
        // 결과 다운로드 기능 구현
        this.updateLog('결과 다운로드 기능은 추후 구현 예정입니다.');
    }
    
    // 저장된 연결 정보 로드 (localStorage 사용)
    loadSavedConnection() {
        try {
            console.log('🔍 loadSavedConnection 시작');
            
            // localStorage에서 연결 정보 가져오기
            const savedConnection = localStorage.getItem('confluence_connection');
            console.log('🔍 localStorage에서 가져온 데이터:', savedConnection);
            
            if (savedConnection) {
                const connectionInfo = JSON.parse(savedConnection);
                console.log('🔍 파싱된 연결 정보:', connectionInfo);
                
                // 폼 필드에 저장된 정보 설정
                const urlField = document.getElementById('confluenceUrl');
                const usernameField = document.getElementById('username');
                
                if (urlField && connectionInfo.url) {
                    urlField.value = connectionInfo.url;
                    console.log('✅ URL 필드 복원:', connectionInfo.url);
                }
                if (usernameField && connectionInfo.username) {
                    usernameField.value = connectionInfo.username;
                    console.log('✅ 사용자명 필드 복원:', connectionInfo.username);
                }
                
                // 연결 상태가 성공이었던 경우에만 상태 복원
                if (connectionInfo.connected) {
                    this.connectionStatus = true;
                    this.updateConnectionStatus({
                        status: 'success',
                        message: '저장된 연결 정보를 불러왔습니다.'
                    });
                    
                    this.updateLog(`저장된 연결 정보 로드: ${connectionInfo.url} (${connectionInfo.username})`);
                    console.log('✅ 연결 상태 복원 완료');
                } else {
                    console.log('⚠️ 저장된 연결은 실패 상태였음');
                }
            } else {
                console.log('⚠️ localStorage에 저장된 연결 정보 없음');
            }
        } catch (error) {
            console.error('❌ 연결 정보 로드 실패:', error);
            // localStorage 오류 시 정보 삭제
            localStorage.removeItem('confluence_connection');
        }
    }
    
    // 연결 정보를 localStorage에 저장
    saveConnectionToStorage(url, username, password, connected) {
        try {
            console.log('🔍 saveConnectionToStorage 메서드 호출됨:', url, username, connected);
            
            const connectionInfo = {
                url: url,
                username: username,
                password: password,  // 보안상 주의: 실제 운영환경에서는 패스워드 저장 지양
                connected: connected,
                savedAt: new Date().toISOString()
            };
            
            console.log('💾 localStorage에 저장할 데이터:', connectionInfo);
            localStorage.setItem('confluence_connection', JSON.stringify(connectionInfo));
            console.log('✅ localStorage 저장 완료');
            
            // 저장 확인
            const savedData = localStorage.getItem('confluence_connection');
            console.log('🔍 저장된 데이터 확인:', savedData);
            
            this.updateLog('연결 정보가 브라우저에 저장되었습니다.');
        } catch (error) {
            console.error('❌ 연결 정보 저장 실패:', error);
            this.updateLog('연결 정보 저장에 실패했습니다.');
        }
    }
}

// 스크립트 로드 확인
console.log('🟢 main.js 파일이 로드되었습니다');

// 전역 함수로 키워드 마인드맵 처리
async function handleKeywordMindmap() {
    console.log('🚀 handleKeywordMindmap 전역 함수 호출됨');
    
    try {
        if (window.confluenceController) {
            console.log('📞 confluenceController.viewKeywordMindmap 호출');
            await window.confluenceController.viewKeywordMindmap();
        } else {
            console.log('⚠️ confluenceController가 없음, 직접 처리');
            await directHandleKeywordMindmap();
        }
    } catch (error) {
        console.error('❌ handleKeywordMindmap 오류:', error);
        alert(`키워드 마인드맵 오류: ${error.message}`);
    }
}

// 직접 키워드 마인드맵 처리
async function directHandleKeywordMindmap() {
    console.log('🔄 직접 키워드 마인드맵 처리 시작');
    
    try {
        const response = await fetch('/keywords');
        console.log('📡 키워드 API 응답:', response.status);
        
        const keywords = await response.json();
        console.log('📋 키워드 목록:', keywords.length, '개');
        
        if (keywords.length === 0) {
            alert('저장된 키워드가 없습니다. 먼저 Confluence 페이지를 처리해주세요.');
            return;
        }
        
        // 간단한 키워드 선택
        const keyword = prompt(`키워드를 선택하세요:\n\n${keywords.slice(0, 10).join('\n')}\n\n위 중 하나를 입력하세요:`);
        
        if (keyword && keywords.includes(keyword)) {
            console.log('✅ 키워드 선택됨:', keyword);
            window.open(`/mindmap?mode=keyword&keyword=${encodeURIComponent(keyword)}`, '_blank');
        } else if (keyword) {
            alert('유효하지 않은 키워드입니다.');
        }
        
    } catch (error) {
        console.error('❌ 직접 처리 오류:', error);
        alert(`오류 발생: ${error.message}`);
    }
}

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', () => {
    console.log('🟢 DOM이 로드되었습니다');
    console.log('=== DOM 로드됨, ConfluenceController 초기화 시작 ===');
    
    try {
        console.log('🔥 ConfluenceController 클래스 인스턴스화 시작');
        window.confluenceController = new ConfluenceController();
        console.log('=== ConfluenceController 초기화 완료 ===');
    } catch (error) {
        console.error('❌ ConfluenceController 초기화 실패:', error);
        console.error('오류 스택:', error.stack);
    }
    
    // 마인드맵 버튼들 직접 이벤트 등록
    setTimeout(() => {
        console.log('=== 마인드맵 버튼 이벤트 등록 시작 ===');
        
        // 전체 마인드맵 버튼
        const viewAllBtn = document.getElementById('viewAllMindmap');
        if (viewAllBtn) {
            viewAllBtn.addEventListener('click', function(e) {
                console.log('🚀 전체 마인드맵 버튼 클릭!');
                e.preventDefault();
                if (window.confluenceController) {
                    window.confluenceController.viewAllMindmap();
                }
            });
            console.log('✅ 전체 마인드맵 버튼 이벤트 등록 완료');
        }
        
        
        // 키워드 마인드맵 버튼
        const viewKeywordBtn = document.getElementById('viewKeywordMindmap');
        if (viewKeywordBtn) {
            viewKeywordBtn.addEventListener('click', function(e) {
                console.log('🚀 키워드 마인드맵 버튼 클릭!');
                e.preventDefault();
                if (window.confluenceController) {
                    console.log('viewKeywordMindmap 메서드 호출 시작...');
                    window.confluenceController.viewKeywordMindmap();
                } else {
                    console.error('confluenceController가 없습니다');
                    alert('시스템 초기화 오류가 발생했습니다. 페이지를 새로고침해주세요.');
                }
            });
            console.log('✅ 키워드 마인드맵 버튼 이벤트 등록 완료');
        }
        
        console.log('=== 마인드맵 버튼 이벤트 등록 완료 ===');
    }, 1000); // 1초 지연으로 확실히 로드 대기
});