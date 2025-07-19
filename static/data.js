class DataViewer {
    constructor() {
        this.currentPage = 1;
        this.perPage = 20;
        this.totalPages = 0;
        this.currentQuery = null;
        this.currentKeywords = null;
        this.currentModalPageId = null; // 현재 모달에 표시된 페이지 ID
        this.init();
    }
    
    init() {
        this.loadStats();
        this.loadAllPages();
    }
    
    async loadStats() {
        try {
            const response = await fetch('/pages/stats');
            const stats = await response.json();
            
            this.displayStats(stats);
            this.createQuickFilters(stats.top_keywords);
            
        } catch (error) {
            console.error('통계 로드 오류:', error);
        }
    }
    
    displayStats(stats) {
        const statsGrid = document.getElementById('statsGrid');
        
        statsGrid.innerHTML = `
            <div class="stat-item">
                <div class="stat-number">${stats.total_pages}</div>
                <div class="stat-label">총 페이지 수</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">${stats.total_unique_keywords}</div>
                <div class="stat-label">고유 키워드 수</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">${stats.recent_pages}</div>
                <div class="stat-label">최근 페이지</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">${stats.top_keywords.length > 0 ? stats.top_keywords[0].count : 0}</div>
                <div class="stat-label">최다 키워드 빈도</div>
            </div>
        `;
    }
    
    createQuickFilters(topKeywords) {
        const quickFilters = document.getElementById('quickFilters');
        
        const filterHtml = topKeywords.slice(0, 10).map(item => 
            `<button class="keyword-tag" onclick="dataViewer.filterByKeyword('${item.keyword}')" style="cursor: pointer;">
                ${item.keyword} (${item.count})
            </button>`
        ).join('');
        
        quickFilters.innerHTML = filterHtml;
    }
    
    async loadAllPages(page = 1) {
        this.currentPage = page;
        this.currentQuery = null;
        this.currentKeywords = null;
        this.perPage = parseInt(document.getElementById('perPage').value);
        
        try {
            const response = await fetch(`/pages?page=${page}&per_page=${this.perPage}`);
            const data = await response.json();
            
            this.displayResults(data, '전체 페이지');
            
        } catch (error) {
            console.error('페이지 로드 오류:', error);
            this.showError('페이지를 불러오는 중 오류가 발생했습니다.');
        }
    }
    
    async searchPages(page = 1) {
        const query = document.getElementById('searchQuery').value.trim();
        const keywordsStr = document.getElementById('searchKeywords').value.trim();
        const keywords = keywordsStr ? keywordsStr.split(',').map(k => k.trim()).filter(k => k) : null;
        
        this.currentPage = page;
        this.currentQuery = query || null;
        this.currentKeywords = keywords;
        this.perPage = parseInt(document.getElementById('perPage').value);
        
        if (!query && !keywords) {
            this.loadAllPages(page);
            return;
        }
        
        try {
            const searchRequest = {
                query: this.currentQuery,
                keywords: this.currentKeywords,
                page: page,
                per_page: this.perPage
            };
            
            const response = await fetch('/pages/search', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(searchRequest)
            });
            
            const data = await response.json();
            
            const title = `검색 결과${query ? ` - "${query}"` : ''}${keywords ? ` (키워드: ${keywords.join(', ')})` : ''}`;
            this.displayResults(data, title);
            
        } catch (error) {
            console.error('검색 오류:', error);
            this.showError('검색 중 오류가 발생했습니다.');
        }
    }
    
    async loadRecentPages() {
        try {
            const response = await fetch('/pages/recent?limit=20');
            const pages = await response.json();
            
            const data = {
                pages: pages,
                total: pages.length,
                page: 1,
                per_page: pages.length
            };
            
            this.displayResults(data, '최근 수정된 페이지');
            
        } catch (error) {
            console.error('최근 페이지 로드 오류:', error);
            this.showError('최근 페이지를 불러오는 중 오류가 발생했습니다.');
        }
    }
    
    filterByKeyword(keyword) {
        document.getElementById('searchKeywords').value = keyword;
        this.searchPages(1);
    }
    
    displayResults(data, title) {
        const resultsTitle = document.getElementById('resultsTitle');
        const resultsInfo = document.getElementById('resultsInfo');
        const resultsContainer = document.getElementById('resultsContainer');
        
        resultsTitle.textContent = title;
        resultsInfo.textContent = `${data.total}개 중 ${data.pages.length}개 표시`;
        
        if (data.pages.length === 0) {
            resultsContainer.innerHTML = '<div class="loading">검색 결과가 없습니다.</div>';
            this.updatePagination(0, 1, 1);
            return;
        }
        
        const pagesHtml = data.pages.map(page => this.createPageItem(page)).join('');
        resultsContainer.innerHTML = pagesHtml;
        
        this.updatePagination(data.total, data.page, data.per_page);
    }
    
    createPageItem(page) {
        const keywordsHtml = page.keywords.map(keyword => 
            `<span class="keyword-tag" onclick="event.stopPropagation(); dataViewer.filterByKeyword('${keyword}')" style="cursor: pointer;">${keyword}</span>`
        ).join('');
        
        return `
            <div class="page-item" onclick="window.openPageModal('${page.page_id}')">
                <div class="page-title">${page.title}</div>
                <div class="page-summary">${page.summary || '요약 없음'}</div>
                <div class="page-keywords">${keywordsHtml}</div>
                <div class="page-meta">
                    페이지 ID: ${page.page_id} | 
                    <a href="${page.url}" target="_blank" onclick="event.stopPropagation()">원본 보기</a> |
                    <button onclick="event.stopPropagation(); window.open('/mindmap?parent_id=${page.page_id}', '_blank')" class="btn btn-info" style="font-size: 0.8em; padding: 4px 8px;">마인드맵</button> |
                    <button onclick="event.stopPropagation(); dataViewer.regeneratePage('${page.page_id}')" class="btn btn-success" style="font-size: 0.8em; padding: 4px 8px;">재생성</button> |
                    <button onclick="event.stopPropagation(); dataViewer.deletePage('${page.page_id}')" class="btn btn-secondary" style="font-size: 0.8em; padding: 4px 8px;">삭제</button>
                </div>
            </div>
        `;
    }
    
    updatePagination(total, currentPage, perPage) {
        const totalPages = Math.ceil(total / perPage);
        this.totalPages = totalPages;
        
        if (totalPages <= 1) {
            document.getElementById('pagination').innerHTML = '';
            return;
        }
        
        let paginationHtml = '';
        
        // 이전 버튼
        paginationHtml += `<button ${currentPage <= 1 ? 'disabled' : ''} onclick="dataViewer.goToPage(${currentPage - 1})">이전</button>`;
        
        // 페이지 번호들
        const startPage = Math.max(1, currentPage - 2);
        const endPage = Math.min(totalPages, currentPage + 2);
        
        if (startPage > 1) {
            paginationHtml += `<button onclick="dataViewer.goToPage(1)">1</button>`;
            if (startPage > 2) {
                paginationHtml += '<span>...</span>';
            }
        }
        
        for (let i = startPage; i <= endPage; i++) {
            const isCurrentPage = i === currentPage;
            paginationHtml += `<button class="${isCurrentPage ? 'current-page' : ''}" onclick="dataViewer.goToPage(${i})">${i}</button>`;
        }
        
        if (endPage < totalPages) {
            if (endPage < totalPages - 1) {
                paginationHtml += '<span>...</span>';
            }
            paginationHtml += `<button onclick="dataViewer.goToPage(${totalPages})">${totalPages}</button>`;
        }
        
        // 다음 버튼
        paginationHtml += `<button ${currentPage >= totalPages ? 'disabled' : ''} onclick="dataViewer.goToPage(${currentPage + 1})">다음</button>`;
        
        document.getElementById('pagination').innerHTML = paginationHtml;
    }
    
    goToPage(page) {
        if (this.currentQuery || this.currentKeywords) {
            this.searchPages(page);
        } else {
            this.loadAllPages(page);
        }
    }
    
    async showPageContent(pageId) {
        try {
            // 모달 요소 확인
            const modal = document.getElementById('pageContentModal');
            if (!modal) {
                console.error('모달 요소를 찾을 수 없습니다');
                return;
            }
            
            // 로딩 표시
            this.showModal();
            
            // 모달 내용 요소들 확인
            const titleEl = document.getElementById('modalTitle');
            const contentEl = document.getElementById('modalContent');
            
            if (!titleEl || !contentEl) {
                console.error('모달 내부 요소를 찾을 수 없습니다');
                return;
            }
            
            titleEl.textContent = '로딩 중...';
            contentEl.innerHTML = '<div style="text-align: center; padding: 40px;">페이지 내용을 불러오는 중...</div>';
            
            const response = await fetch(`/pages/${pageId}/content`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const pageData = await response.json();
            
            // 현재 모달 페이지 ID 저장
            this.currentModalPageId = pageData.page_id;
            
            // 모달 내용 업데이트
            titleEl.textContent = pageData.title;
            
            // 페이지 메타 정보 업데이트
            const pageIdEl = document.getElementById('modalPageId');
            const urlEl = document.getElementById('modalUrl');
            const modifiedDateEl = document.getElementById('modalModifiedDate');
            
            if (pageIdEl) pageIdEl.textContent = pageData.page_id;
            if (urlEl) {
                urlEl.href = pageData.url || '#';
                urlEl.textContent = pageData.url ? '🔗 원본 페이지 보기' : 'URL 없음';
            }
            if (modifiedDateEl) modifiedDateEl.textContent = pageData.modified_date || '정보 없음';
            
            // 요약 업데이트
            const summaryEl = document.getElementById('modalSummary');
            if (summaryEl) {
                summaryEl.textContent = pageData.summary || '요약이 없습니다.';
            }
            
            // 키워드 업데이트
            const keywordsEl = document.getElementById('modalKeywords');
            if (keywordsEl) {
                const keywordsHtml = pageData.keywords && pageData.keywords.length > 0 ? 
                    pageData.keywords.map(keyword => 
                        `<span class="keyword-tag" onclick="dataViewer.filterByKeyword('${keyword}'); dataViewer.hideModal();" style="cursor: pointer;">${keyword}</span>`
                    ).join('') : 
                    '<div class="no-content">키워드가 없습니다.</div>';
                keywordsEl.innerHTML = keywordsHtml;
            }
            
            // 페이지 내용 업데이트
            if (contentEl) {
                const content = pageData.content || '페이지 내용이 없습니다.';
                contentEl.textContent = content;
            }
            
        } catch (error) {
            console.error('페이지 내용 로드 오류:', error);
            
            // 에러 시에도 모달이 표시되도록 함
            this.showModal();
            
            const titleEl = document.getElementById('modalTitle');
            const contentEl = document.getElementById('modalContent');
            
            if (titleEl) titleEl.textContent = '오류';
            if (contentEl) {
                contentEl.innerHTML = `
                    <div style="text-align: center; padding: 40px; color: #e74c3c;">
                        페이지 내용을 불러오는 중 오류가 발생했습니다.<br>
                        ${error.message}
                    </div>
                `;
            }
        }
    }
    
    showModal() {
        const modal = document.getElementById('pageContentModal');
        if (!modal) {
            console.error('모달 요소를 찾을 수 없습니다');
            return;
        }
        
        modal.style.display = 'block';
        document.body.style.overflow = 'hidden'; // 배경 스크롤 방지
    }
    
    hideModal() {
        const modal = document.getElementById('pageContentModal');
        if (!modal) {
            console.error('모달 요소를 찾을 수 없습니다');
            return;
        }
        
        modal.style.display = 'none';
        document.body.style.overflow = 'auto'; // 배경 스크롤 복원
    }

    async regeneratePage(pageId) {
        if (!confirm('이 페이지의 요약과 키워드를 재생성하시겠습니까?')) {
            return;
        }
        
        try {
            console.log('페이지 재생성 시작:', pageId);
            
            // 버튼 상태 변경
            const regenerateBtn = document.getElementById('regenerateBtn');
            const originalText = regenerateBtn ? regenerateBtn.textContent : '';
            
            if (regenerateBtn) {
                regenerateBtn.textContent = '재생성 중...';
                regenerateBtn.disabled = true;
            }
            
            const response = await fetch(`/pages/${pageId}/regenerate`, {
                method: 'POST'
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }
            
            const result = await response.json();
            console.log('재생성 완료:', result);
            
            alert('요약과 키워드가 재생성되었습니다!');
            
            // 잠시 후 페이지 새로고침 (버튼 상태 복원 후)
            setTimeout(() => {
                this.goToPage(this.currentPage);
            }, 100);
            
            // 모달이 열려있다면 내용 업데이트
            if (regenerateBtn) {
                // 모달 요약 업데이트
                const summaryEl = document.getElementById('modalSummary');
                if (summaryEl) {
                    summaryEl.textContent = result.summary || '요약이 없습니다.';
                }
                
                // 모달 키워드 업데이트
                const keywordsEl = document.getElementById('modalKeywords');
                if (keywordsEl) {
                    const keywordsHtml = result.keywords && result.keywords.length > 0 ? 
                        result.keywords.map(keyword => 
                            `<span class="keyword-tag" onclick="dataViewer.filterByKeyword('${keyword}'); dataViewer.hideModal();" style="cursor: pointer;">${keyword}</span>`
                        ).join('') : 
                        '<div class="no-content">키워드가 없습니다.</div>';
                    keywordsEl.innerHTML = keywordsHtml;
                }
            }
            
        } catch (error) {
            console.error('페이지 재생성 오류:', error);
            alert(`재생성 중 오류가 발생했습니다: ${error.message}`);
        } finally {
            // 버튼 상태 복원
            const regenerateBtn = document.getElementById('regenerateBtn');
            if (regenerateBtn) {
                regenerateBtn.textContent = '재생성';
                regenerateBtn.disabled = false;
                console.log('재생성 버튼 상태 복원됨');
            }
        }
    }

    async deletePage(pageId) {
        if (!confirm('이 페이지를 삭제하시겠습니까?')) {
            return;
        }
        
        try {
            const response = await fetch(`/pages/${pageId}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                alert('페이지가 삭제되었습니다.');
                // 현재 페이지 새로고침
                this.goToPage(this.currentPage);
                // 통계 업데이트
                this.loadStats();
            } else {
                throw new Error('삭제 실패');
            }
            
        } catch (error) {
            console.error('삭제 오류:', error);
            alert('페이지 삭제 중 오류가 발생했습니다.');
        }
    }
    
    showError(message) {
        document.getElementById('resultsContainer').innerHTML = `<div class="loading" style="color: #e74c3c;">${message}</div>`;
    }
}

// 전역 함수들
function searchPages() {
    dataViewer.searchPages(1);
}

function loadAllPages() {
    dataViewer.loadAllPages(1);
}

function loadRecentPages() {
    dataViewer.loadRecentPages();
}

// 전역 함수: 페이지 모달 열기
window.openPageModal = function(pageId) {
    if (window.dataViewer && typeof window.dataViewer.showPageContent === 'function') {
        window.dataViewer.showPageContent(pageId);
    } else {
        console.error('dataViewer를 찾을 수 없습니다');
    }
};

// 페이지 로드 시 초기화
const dataViewer = new DataViewer();
window.dataViewer = dataViewer; // 전역으로 설정

// 마인드맵 버튼 기능
function goToMindmap() {
    // 사용 가능한 페이지 ID 찾기
    const pageItems = document.querySelectorAll('.page-item');
    if (pageItems.length === 0) {
        alert('먼저 페이지를 조회해주세요.');
        return;
    }
    
    // 첫 번째 페이지의 ID를 기본으로 사용하거나 사용자에게 선택하도록 함
    const pageIds = Array.from(pageItems).map(item => {
        const metaText = item.querySelector('.page-meta').textContent;
        const match = metaText.match(/페이지 ID: (\S+)/);
        return match ? match[1] : null;
    }).filter(id => id);
    
    if (pageIds.length === 0) {
        alert('유효한 페이지 ID를 찾을 수 없습니다.');
        return;
    }
    
    // 여러 페이지가 있으면 선택하도록 함
    let selectedPageId;
    if (pageIds.length === 1) {
        selectedPageId = pageIds[0];
    } else {
        const pageOptions = Array.from(pageItems).slice(0, 10).map((item, index) => {
            const title = item.querySelector('.page-title').textContent;
            const metaText = item.querySelector('.page-meta').textContent;
            const match = metaText.match(/페이지 ID: (\S+)/);
            const pageId = match ? match[1] : null;
            return `${index + 1}. ${title} (${pageId})`;
        }).join('\n');
        
        const choice = prompt(`마인드맵을 생성할 페이지를 선택하세요 (1-${Math.min(pageIds.length, 10)}):\n\n${pageOptions}`);
        const choiceNum = parseInt(choice);
        
        if (isNaN(choiceNum) || choiceNum < 1 || choiceNum > Math.min(pageIds.length, 10)) {
            alert('잘못된 선택입니다.');
            return;
        }
        
        selectedPageId = pageIds[choiceNum - 1];
    }
    
    // 마인드맵 페이지로 이동
    window.open(`/mindmap?parent_id=${selectedPageId}`, '_blank');
}

// 엔터 키로 검색
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('searchQuery').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            searchPages();
        }
    });
    
    document.getElementById('searchKeywords').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            searchPages();
        }
    });
    
    // 마인드맵 버튼 이벤트 연결
    document.getElementById('goToMindmap').addEventListener('click', goToMindmap);
    
    // 모달 이벤트 리스너
    const modal = document.getElementById('pageContentModal');
    const closeBtn = document.getElementById('closeModal');
    const regenerateBtn = document.getElementById('regenerateBtn');
    
    // 닫기 버튼 클릭
    closeBtn.addEventListener('click', () => {
        dataViewer.hideModal();
    });
    
    // 재생성 버튼 클릭
    regenerateBtn.addEventListener('click', () => {
        if (dataViewer.currentModalPageId) {
            dataViewer.regeneratePage(dataViewer.currentModalPageId);
        } else {
            alert('페이지 ID를 찾을 수 없습니다.');
        }
    });
    
    // 모달 배경 클릭 시 닫기
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            dataViewer.hideModal();
        }
    });
    
    // ESC 키로 모달 닫기
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.style.display === 'block') {
            dataViewer.hideModal();
        }
    });
});