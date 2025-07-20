class SpaceManager {
    constructor() {
        this.spaces = [];
        this.selectedSpace = null;
        this.init();
    }
    
    async init() {
        await this.loadSpaces();
    }
    
    async loadSpaces() {
        try {
            console.log('🔄 Space 목록 로딩 시작...');
            
            const response = await fetch('/api/spaces');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            this.spaces = data.spaces || [];
            
            console.log(`✅ ${this.spaces.length}개 Space 로드 완료:`, this.spaces);
            
            this.displaySpaces();
            
        } catch (error) {
            console.error('❌ Space 로딩 실패:', error);
            this.showError(`Space 목록을 불러오는데 실패했습니다: ${error.message}`);
        }
    }
    
    displaySpaces() {
        const loadingElement = document.getElementById('loadingSpaces');
        const gridElement = document.getElementById('spacesGrid');
        
        loadingElement.style.display = 'none';
        
        if (this.spaces.length === 0) {
            gridElement.innerHTML = `
                <div class="loading">
                    <h3>🔍 Space가 없습니다</h3>
                    <p>아직 처리된 Space가 없습니다. 먼저 Confluence 페이지를 처리해주세요.</p>
                </div>
            `;
            gridElement.style.display = 'block';
            return;
        }
        
        const spacesHtml = this.spaces.map(space => this.createSpaceCard(space)).join('');
        gridElement.innerHTML = spacesHtml;
        gridElement.style.display = 'grid';
    }
    
    createSpaceCard(space) {
        // Space Key의 첫 2글자를 아이콘으로 사용
        const iconText = space.space_key.substring(0, 2).toUpperCase();
        
        return `
            <div class="space-card" onclick="spaceManager.selectSpace('${space.space_key}')">
                <div class="space-title">
                    <div class="space-icon">${iconText}</div>
                    <span>${space.space_key}</span>
                </div>
                
                <div class="space-stats">
                    <div class="stat-item">
                        <div class="stat-number">${space.page_count}</div>
                        <div class="stat-label">페이지</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number">📊</div>
                        <div class="stat-label">통계</div>
                    </div>
                </div>
                
                <div class="space-actions" onclick="event.stopPropagation()">
                    <button class="btn btn-primary" onclick="spaceManager.viewSpacePages('${space.space_key}')">
                        📄 페이지
                    </button>
                    <button class="btn btn-success" onclick="spaceManager.generateMindmap('${space.space_key}')">
                        🗺️ 마인드맵
                    </button>
                </div>
            </div>
        `;
    }
    
    async selectSpace(spaceKey) {
        try {
            console.log(`🎯 Space 선택: ${spaceKey}`);
            
            // 이전 선택 제거
            document.querySelectorAll('.space-card').forEach(card => {
                card.classList.remove('selected');
            });
            
            // 현재 선택 표시
            event.target.closest('.space-card').classList.add('selected');
            
            this.selectedSpace = spaceKey;
            
            // 상세 정보 로드
            await this.loadSpaceDetails(spaceKey);
            
        } catch (error) {
            console.error('❌ Space 선택 실패:', error);
            this.showError(`Space 정보를 불러오는데 실패했습니다: ${error.message}`);
        }
    }
    
    async loadSpaceDetails(spaceKey) {
        try {
            const response = await fetch(`/api/spaces/${spaceKey}/stats`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const stats = await response.json();
            console.log(`📊 ${spaceKey} 통계:`, stats);
            
            this.displaySpaceDetails(stats);
            
        } catch (error) {
            console.error('❌ Space 통계 로딩 실패:', error);
            this.showError(`Space 통계를 불러오는데 실패했습니다: ${error.message}`);
        }
    }
    
    displaySpaceDetails(stats) {
        const panel = document.getElementById('selectedSpacePanel');
        const title = document.getElementById('selectedSpaceTitle');
        const details = document.getElementById('spaceDetails');
        
        title.textContent = `${stats.space_key} Space 상세 정보`;
        
        details.innerHTML = `
            <div class="detail-card">
                <div class="detail-number">${stats.total_pages}</div>
                <div class="detail-label">총 페이지 수</div>
            </div>
            <div class="detail-card">
                <div class="detail-number">${stats.recent_pages}</div>
                <div class="detail-label">최근 페이지</div>
            </div>
            <div class="detail-card">
                <div class="detail-number">${stats.total_unique_keywords}</div>
                <div class="detail-label">고유 키워드</div>
            </div>
            <div class="detail-card">
                <div class="detail-number">${stats.top_keywords.length}</div>
                <div class="detail-label">주요 키워드</div>
            </div>
        `;
        
        panel.classList.add('show');
        
        // 스크롤을 패널로 이동
        panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    
    viewSpacePages(spaceKey = null) {
        const targetSpace = spaceKey || this.selectedSpace;
        if (!targetSpace) {
            alert('Space를 먼저 선택해주세요.');
            return;
        }
        
        // 데이터 조회 페이지로 이동하면서 space 필터 적용
        window.open(`/data?space=${targetSpace}`, '_blank');
    }
    
    generateMindmap(type = 'title', spaceKey = null) {
        const targetSpace = spaceKey || this.selectedSpace;
        if (!targetSpace) {
            alert('Space를 먼저 선택해주세요.');
            return;
        }
        
        // 마인드맵 타입에 따라 다른 URL로 이동
        let url;
        if (type === 'keyword') {
            // 키워드 마인드맵: 전체 키워드 네트워크에서 space 필터 적용
            url = `/mindmap?space=${targetSpace}&type=keyword`;
        } else {
            // 타이틀 마인드맵: 일반 페이지 마인드맵에서 space 필터 적용
            url = `/mindmap?space=${targetSpace}&type=title`;
        }
        
        console.log(`🗺️ ${type} 마인드맵 생성: ${url}`);
        window.open(url, '_blank');
    }
    
    generateSpaceTitleMindmap() {
        this.generateMindmap('title');
    }
    
    generateSpaceKeywordMindmap() {
        this.generateMindmap('keyword');
    }
    
    async exportSpaceData() {
        if (!this.selectedSpace) {
            alert('Space를 먼저 선택해주세요.');
            return;
        }
        
        try {
            console.log(`📤 ${this.selectedSpace} 데이터 내보내기...`);
            
            const response = await fetch(`/api/spaces/${this.selectedSpace}/pages?per_page=1000`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            // CSV 형태로 데이터 변환
            const csvContent = this.convertToCSV(data.pages);
            
            // 파일 다운로드
            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const link = document.createElement('a');
            const url = URL.createObjectURL(blob);
            link.setAttribute('href', url);
            link.setAttribute('download', `${this.selectedSpace}_pages.csv`);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            console.log(`✅ ${this.selectedSpace} 데이터 내보내기 완료`);
            
        } catch (error) {
            console.error('❌ 데이터 내보내기 실패:', error);
            this.showError(`데이터 내보내기에 실패했습니다: ${error.message}`);
        }
    }
    
    convertToCSV(pages) {
        if (!pages || pages.length === 0) return '';
        
        const headers = ['Page ID', 'Title', 'Space Key', 'Keywords', 'Summary', 'URL', 'Modified Date'];
        const csvRows = [headers.join(',')];
        
        pages.forEach(page => {
            const row = [
                `"${page.page_id || ''}"`,
                `"${(page.title || '').replace(/"/g, '""')}"`,
                `"${page.space_key || ''}"`,
                `"${(page.keywords || []).join('; ')}"`,
                `"${(page.summary || '').replace(/"/g, '""')}"`,
                `"${page.url || ''}"`,
                `"${page.modified_date || ''}"`
            ];
            csvRows.push(row.join(','));
        });
        
        return csvRows.join('\\n');
    }
    
    closeSpacePanel() {
        const panel = document.getElementById('selectedSpacePanel');
        panel.classList.remove('show');
        
        // 선택 해제
        document.querySelectorAll('.space-card').forEach(card => {
            card.classList.remove('selected');
        });
        
        this.selectedSpace = null;
    }
    
    showError(message) {
        const errorElement = document.getElementById('errorMessage');
        const loadingElement = document.getElementById('loadingSpaces');
        
        loadingElement.style.display = 'none';
        errorElement.textContent = message;
        errorElement.style.display = 'block';
        
        // 5초 후 자동으로 에러 메시지 숨기기
        setTimeout(() => {
            errorElement.style.display = 'none';
        }, 5000);
    }
}

// 전역 변수 및 이벤트 리스너
let spaceManager;

document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Space Manager 초기화...');
    spaceManager = new SpaceManager();
});

// 전역 함수들
function viewSpacePages() {
    spaceManager.viewSpacePages();
}

function generateSpaceTitleMindmap() {
    spaceManager.generateSpaceTitleMindmap();
}

function generateSpaceKeywordMindmap() {
    spaceManager.generateSpaceKeywordMindmap();
}

function exportSpaceData() {
    spaceManager.exportSpaceData();
}

function closeSpacePanel() {
    spaceManager.closeSpacePanel();
}