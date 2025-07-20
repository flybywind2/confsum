class DataViewer {
    constructor() {
        this.currentPage = 1;
        this.perPage = 20;
        this.totalPages = 0;
        this.currentQuery = null;
        this.currentKeywords = null;
        this.currentModalPageId = null; // 현재 모달에 표시된 페이지 ID
        this.currentData = []; // 현재 표시된 데이터 저장
        this.currentTitle = ''; // 현재 검색/조회 제목
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
        const downloadCSV = document.getElementById('downloadCSV');
        const downloadJSON = document.getElementById('downloadJSON');
        
        resultsTitle.textContent = title;
        resultsInfo.textContent = `${data.total}개 중 ${data.pages.length}개 표시`;
        
        // 현재 데이터와 제목 저장
        this.currentData = data.pages;
        this.currentTitle = title;
        
        const bulkActionsPanel = document.getElementById('bulkActionsPanel');
        
        if (data.pages.length === 0) {
            resultsContainer.innerHTML = '<div class="loading">검색 결과가 없습니다.</div>';
            this.updatePagination(0, 1, 1);
            // 데이터가 없으면 다운로드 버튼과 일괄 작업 패널 숨기기
            if (downloadCSV) downloadCSV.style.display = 'none';
            if (downloadJSON) downloadJSON.style.display = 'none';
            if (bulkActionsPanel) bulkActionsPanel.style.display = 'none';
            return;
        }
        
        const pagesHtml = data.pages.map(page => this.createPageItem(page)).join('');
        resultsContainer.innerHTML = pagesHtml;
        
        // 데이터가 있으면 다운로드 버튼과 일괄 작업 패널 표시
        if (downloadCSV) downloadCSV.style.display = 'inline-block';
        if (downloadJSON) downloadJSON.style.display = 'inline-block';
        if (bulkActionsPanel) bulkActionsPanel.style.display = 'block';
        
        // 일괄 작업 상태 초기화
        this.resetBulkActions();
        
        this.updatePagination(data.total, data.page, data.per_page);
    }
    
    createPageItem(page) {
        const keywordsHtml = page.keywords.map(keyword => 
            `<span class="keyword-tag" onclick="event.stopPropagation(); dataViewer.filterByKeyword('${keyword}')" style="cursor: pointer;">${keyword}</span>`
        ).join('');
        
        // 두 요약이 다른지 확인
        const hasChunkBasedSummary = page.chunk_based_summary && page.chunk_based_summary !== page.summary;
        const summaryId = `summary-${page.page_id}`;
        
        const summaryHtml = hasChunkBasedSummary ? `
            <div class="summary-container">
                <div class="summary-selector">
                    <div class="summary-tab active" onclick="event.stopPropagation(); dataViewer.switchSummary('${page.page_id}', 'standard')">일반 요약</div>
                    <div class="summary-tab" onclick="event.stopPropagation(); dataViewer.switchSummary('${page.page_id}', 'chunk')">RAG 요약</div>
                </div>
                <div class="page-summary" id="${summaryId}">${page.summary || '요약 없음'}</div>
            </div>
        ` : `
            <div class="page-summary">${page.summary || '요약 없음'}</div>
        `;
        
        return `
            <div class="page-item" onclick="window.openPageModal('${page.page_id}')">
                <div style="display: flex; align-items: flex-start; gap: 10px;">
                    <input type="checkbox" class="page-checkbox" data-page-id="${page.page_id}" 
                           onchange="event.stopPropagation(); updateBulkActions()" 
                           onclick="event.stopPropagation()" style="margin-top: 5px;">
                    <div style="flex: 1;">
                        <div class="page-title">${page.title}</div>
                        ${summaryHtml}
                        <div class="page-keywords">${keywordsHtml}</div>
                        <div class="page-meta">
                            페이지 ID: ${page.page_id} | 
                            <a href="${page.url}" target="_blank" onclick="event.stopPropagation()">원본 보기</a> |
                            <button onclick="event.stopPropagation(); window.open('/mindmap?parent_id=${page.page_id}', '_blank')" class="btn btn-info" style="font-size: 0.8em; padding: 4px 8px;">마인드맵</button> |
                            <button onclick="event.stopPropagation(); dataViewer.regeneratePage('${page.page_id}')" class="btn btn-success" style="font-size: 0.8em; padding: 4px 8px;">재생성</button> |
                            <button onclick="event.stopPropagation(); dataViewer.deletePage('${page.page_id}')" class="btn btn-secondary" style="font-size: 0.8em; padding: 4px 8px;">삭제</button>
                        </div>
                    </div>
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
            console.log('🔗 페이지 모달 열기:', pageId);
            
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
            contentEl.innerHTML = '<div style="text-align: center; padding: 40px;"><div style="display: inline-block; width: 20px; height: 20px; border: 3px solid #f3f3f3; border-top: 3px solid #3498db; border-radius: 50%; animation: spin 1s linear infinite;"></div> 페이지 내용을 불러오는 중...</div>';
            
            const response = await fetch(`/pages/${pageId}/content`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const pageData = await response.json();
            
            // 현재 모달 페이지 ID와 데이터 저장
            this.currentModalPageId = pageData.page_id;
            this.currentModalPageData = pageData;
            
            // 모달 제목 설정
            titleEl.textContent = pageData.title || '제목 없음';
            
            // 키워드 태그 생성
            const keywordsHtml = Array.isArray(pageData.keywords) ? 
                pageData.keywords.map(keyword => 
                    `<span style="background: #e3f2fd; color: #1976d2; padding: 3px 8px; border-radius: 12px; font-size: 12px; margin: 2px; cursor: pointer;" onclick="dataViewer.filterByKeyword('${keyword}'); dataViewer.hideModal();">${keyword}</span>`
                ).join(' ') : '키워드 없음';
            
            // 날짜 포맷팅
            const formatDate = (dateStr) => {
                if (!dateStr) return '정보 없음';
                try {
                    return new Date(dateStr).toLocaleString('ko-KR');
                } catch {
                    return dateStr;
                }
            };
            
            // 모달 내용 설정 (마인드맵과 동일한 스타일)
            contentEl.innerHTML = `
                <div style="margin-bottom: 20px;">
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 10px;">
                            <div>
                                <strong style="color: #495057;">📄 페이지 ID:</strong><br>
                                <span style="font-family: monospace; background: #e9ecef; padding: 2px 6px; border-radius: 4px;">${pageData.page_id}</span>
                            </div>
                            <div>
                                <strong style="color: #495057;">🔗 원본 링크:</strong><br>
                                <a href="${pageData.url}" target="_blank" style="color: #007bff; text-decoration: none;">Confluence에서 보기 →</a>
                            </div>
                            <div>
                                <strong style="color: #495057;">📅 생성일:</strong><br>
                                <span>${formatDate(pageData.created_date)}</span>
                            </div>
                            <div>
                                <strong style="color: #495057;">✏️ 수정일:</strong><br>
                                <span>${formatDate(pageData.modified_date)}</span>
                            </div>
                            <div>
                                <strong style="color: #495057;">👤 생성자:</strong><br>
                                <span>${pageData.created_by || '정보 없음'}</span>
                            </div>
                            <div>
                                <strong style="color: #495057;">✍️ 수정자:</strong><br>
                                <span>${pageData.modified_by || '정보 없음'}</span>
                            </div>
                        </div>
                        <div style="margin-top: 15px;">
                            <strong style="color: #495057;">🏷️ 키워드:</strong><br>
                            <div style="margin-top: 8px;">${keywordsHtml}</div>
                        </div>
                    </div>
                    
                    <div style="background: #fff; border: 1px solid #dee2e6; border-radius: 8px; padding: 20px;">
                        <h4 style="color: #495057; margin-top: 0; border-bottom: 2px solid #e9ecef; padding-bottom: 10px;">📋 요약</h4>
                        ${this.createSummarySelector(pageData)}
                        <div id="modal-summary-content" style="line-height: 1.6; color: #6c757d; margin-bottom: 20px;">
                            ${pageData.summary || '요약 정보가 없습니다.'}
                        </div>
                        
                        <h4 style="color: #495057; border-bottom: 2px solid #e9ecef; padding-bottom: 10px;">📖 전체 내용</h4>
                        <div style="line-height: 1.6; color: #495057; max-height: 400px; overflow-y: auto; padding: 15px; background: #f8f9fa; border-radius: 5px;">
                            ${pageData.content ? pageData.content.replace(/\n/g, '<br>') : '내용이 없습니다.'}
                        </div>
                    </div>
                </div>
            `;
            
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

    async regeneratePage(pageId, showAlert = true) {
        if (showAlert && !confirm('이 페이지의 요약과 키워드를 재생성하시겠습니까?')) {
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
            
            if (showAlert) {
                alert('요약과 키워드가 재생성되었습니다!');
            }
            
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

    async deletePage(pageId, showAlert = true) {
        if (showAlert && !confirm('이 페이지를 삭제하시겠습니까?')) {
            return;
        }
        
        try {
            const response = await fetch(`/pages/${pageId}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                if (showAlert) {
                    alert('페이지가 삭제되었습니다.');
                }
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
    
    // 요약 전환 기능 (리스트용)
    switchSummary(pageId, summaryType) {
        const summaryElement = document.getElementById(`summary-${pageId}`);
        const tabs = document.querySelectorAll(`[onclick*="switchSummary('${pageId}'"]`);
        
        if (!summaryElement) return;
        
        // 현재 데이터에서 해당 페이지 찾기
        const page = this.currentData.find(p => p.page_id === pageId);
        if (!page) return;
        
        // 탭 상태 업데이트
        tabs.forEach(tab => tab.classList.remove('active'));
        
        if (summaryType === 'standard') {
            summaryElement.textContent = page.summary || '요약 없음';
            tabs[0].classList.add('active');
        } else if (summaryType === 'chunk') {
            summaryElement.textContent = page.chunk_based_summary || '요약 없음';
            tabs[1].classList.add('active');
        }
    }
    
    // 요약 선택기 생성 함수 (모달용)
    createSummarySelector(pageData) {
        const hasChunkBasedSummary = pageData.chunk_based_summary && pageData.chunk_based_summary !== pageData.summary;
        
        if (!hasChunkBasedSummary) {
            return ''; // 두 요약이 같거나 chunk 기반 요약이 없으면 선택기 숨김
        }
        
        return `
            <div style="display: flex; gap: 10px; margin-bottom: 15px; flex-wrap: wrap;">
                <div id="modal-summary-tab-standard" onclick="dataViewer.switchModalSummary('standard')" 
                     style="padding: 6px 12px; border: 1px solid #ddd; background: #3498db; color: white; border-radius: 4px; cursor: pointer; font-size: 14px; transition: all 0.3s;">
                    일반 요약
                </div>
                <div id="modal-summary-tab-chunk" onclick="dataViewer.switchModalSummary('chunk')" 
                     style="padding: 6px 12px; border: 1px solid #ddd; background: #f8f9fa; border-radius: 4px; cursor: pointer; font-size: 14px; transition: all 0.3s;">
                    RAG 요약
                </div>
            </div>
        `;
    }
    
    // 모달에서 요약 전환 함수
    switchModalSummary(summaryType) {
        const standardTab = document.getElementById('modal-summary-tab-standard');
        const chunkTab = document.getElementById('modal-summary-tab-chunk');
        const summaryContent = document.getElementById('modal-summary-content');
        
        if (!standardTab || !chunkTab || !summaryContent) return;
        
        // 현재 모달에 표시된 페이지 데이터 가져오기
        const currentPageData = this.currentModalPageData;
        if (!currentPageData) return;
        
        // 탭 상태 업데이트
        if (summaryType === 'standard') {
            standardTab.style.background = '#3498db';
            standardTab.style.color = 'white';
            chunkTab.style.background = '#f8f9fa';
            chunkTab.style.color = '#495057';
            summaryContent.textContent = currentPageData.summary || '요약 정보가 없습니다.';
        } else if (summaryType === 'chunk') {
            chunkTab.style.background = '#3498db';
            chunkTab.style.color = 'white';
            standardTab.style.background = '#f8f9fa';
            standardTab.style.color = '#495057';
            summaryContent.textContent = currentPageData.chunk_based_summary || '요약 정보가 없습니다.';
        }
    }
    
    // CSV 다운로드 기능
    downloadCSV() {
        if (!this.currentData || this.currentData.length === 0) {
            alert('다운로드할 데이터가 없습니다.');
            return;
        }
        
        try {
            // CSV 헤더 생성
            const headers = ['페이지ID', '제목', '일반요약', 'RAG요약', '키워드', 'URL', '생성일', '수정일', '생성자', '수정자'];
            
            // CSV 데이터 생성
            const csvData = this.currentData.map(page => {
                const keywords = Array.isArray(page.keywords) ? page.keywords.join('; ') : '';
                const summary = (page.summary || '').replace(/"/g, '""').replace(/\n/g, ' ');
                const chunkSummary = (page.chunk_based_summary || '').replace(/"/g, '""').replace(/\n/g, ' ');
                const title = (page.title || '').replace(/"/g, '""');
                
                return [
                    page.page_id || '',
                    `"${title}"`,
                    `"${summary}"`,
                    `"${chunkSummary}"`,
                    `"${keywords}"`,
                    page.url || '',
                    page.created_date || '',
                    page.modified_date || '',
                    `"${page.created_by || ''}"`,
                    `"${page.modified_by || ''}"`
                ].join(',');
            });
            
            // CSV 문자열 생성
            const csvContent = [headers.join(','), ...csvData].join('\n');
            
            // BOM 추가로 한글 깨짐 방지
            const BOM = '\uFEFF';
            const blob = new Blob([BOM + csvContent], { type: 'text/csv;charset=utf-8;' });
            
            // 파일명 생성
            const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
            const filename = `confluence_data_${this.currentTitle.replace(/[^a-zA-Z0-9가-힣]/g, '_')}_${timestamp}.csv`;
            
            // 다운로드 실행
            this.downloadFile(blob, filename);
            
        } catch (error) {
            console.error('CSV 다운로드 오류:', error);
            alert('CSV 다운로드 중 오류가 발생했습니다.');
        }
    }
    
    // JSON 다운로드 기능
    downloadJSON() {
        if (!this.currentData || this.currentData.length === 0) {
            alert('다운로드할 데이터가 없습니다.');
            return;
        }
        
        try {
            // JSON 데이터 생성
            const jsonData = {
                export_info: {
                    title: this.currentTitle,
                    exported_at: new Date().toISOString(),
                    total_pages: this.currentData.length,
                    query: this.currentQuery,
                    keywords: this.currentKeywords
                },
                pages: this.currentData.map(page => ({
                    page_id: page.page_id,
                    title: page.title,
                    summary: page.summary,
                    chunk_based_summary: page.chunk_based_summary,
                    keywords: page.keywords,
                    url: page.url,
                    created_date: page.created_date,
                    modified_date: page.modified_date,
                    created_by: page.created_by,
                    modified_by: page.modified_by,
                    content: page.content // 전체 내용도 포함
                }))
            };
            
            // JSON 문자열 생성 (들여쓰기 포함)
            const jsonString = JSON.stringify(jsonData, null, 2);
            const blob = new Blob([jsonString], { type: 'application/json;charset=utf-8;' });
            
            // 파일명 생성
            const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
            const filename = `confluence_data_${this.currentTitle.replace(/[^a-zA-Z0-9가-힣]/g, '_')}_${timestamp}.json`;
            
            // 다운로드 실행
            this.downloadFile(blob, filename);
            
        } catch (error) {
            console.error('JSON 다운로드 오류:', error);
            alert('JSON 다운로드 중 오류가 발생했습니다.');
        }
    }
    
    // 파일 다운로드 헬퍼 함수
    downloadFile(blob, filename) {
        // IE 체크
        if (window.navigator && window.navigator.msSaveOrOpenBlob) {
            window.navigator.msSaveOrOpenBlob(blob, filename);
            return;
        }
        
        // 다른 브라우저용
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        
        // 링크를 DOM에 추가하고 클릭 후 제거
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        // 메모리 정리
        window.URL.revokeObjectURL(url);
    }
    
    // 일괄 작업 관련 메서드들
    resetBulkActions() {
        const selectAllCheckbox = document.getElementById('selectAll');
        const pageCheckboxes = document.querySelectorAll('.page-checkbox');
        const selectedCount = document.getElementById('selectedCount');
        const bulkRegenerate = document.getElementById('bulkRegenerate');
        const bulkDelete = document.getElementById('bulkDelete');
        
        if (selectAllCheckbox) selectAllCheckbox.checked = false;
        pageCheckboxes.forEach(checkbox => checkbox.checked = false);
        if (selectedCount) selectedCount.textContent = '0개 선택됨';
        if (bulkRegenerate) bulkRegenerate.disabled = true;
        if (bulkDelete) bulkDelete.disabled = true;
    }
    
    async bulkRegenerate(selectedPageIds) {
        if (!selectedPageIds || selectedPageIds.length === 0) {
            alert('재생성할 페이지를 선택해주세요.');
            return;
        }
        
        if (!confirm(`선택된 ${selectedPageIds.length}개 페이지를 재생성하시겠습니까?`)) {
            return;
        }
        
        const progressInfo = document.getElementById('selectedCount');
        let completed = 0;
        
        for (const pageId of selectedPageIds) {
            try {
                if (progressInfo) {
                    progressInfo.textContent = `재생성 중... (${completed + 1}/${selectedPageIds.length})`;
                }
                
                await this.regeneratePage(pageId, false); // showAlert = false
                completed++;
            } catch (error) {
                console.error(`페이지 ${pageId} 재생성 실패:`, error);
            }
        }
        
        if (progressInfo) {
            progressInfo.textContent = `재생성 완료: ${completed}/${selectedPageIds.length}개`;
        }
        
        alert(`${completed}개 페이지 재생성이 완료되었습니다.`);
        
        // 현재 페이지 새로고침
        this.refreshCurrentView();
    }
    
    async bulkDelete(selectedPageIds) {
        if (!selectedPageIds || selectedPageIds.length === 0) {
            alert('삭제할 페이지를 선택해주세요.');
            return;
        }
        
        if (!confirm(`선택된 ${selectedPageIds.length}개 페이지를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.`)) {
            return;
        }
        
        const progressInfo = document.getElementById('selectedCount');
        let completed = 0;
        
        for (const pageId of selectedPageIds) {
            try {
                if (progressInfo) {
                    progressInfo.textContent = `삭제 중... (${completed + 1}/${selectedPageIds.length})`;
                }
                
                await this.deletePage(pageId, false); // showAlert = false
                completed++;
            } catch (error) {
                console.error(`페이지 ${pageId} 삭제 실패:`, error);
            }
        }
        
        if (progressInfo) {
            progressInfo.textContent = `삭제 완료: ${completed}/${selectedPageIds.length}개`;
        }
        
        alert(`${completed}개 페이지 삭제가 완료되었습니다.`);
        
        // 현재 페이지 새로고침
        this.refreshCurrentView();
    }
    
    refreshCurrentView() {
        // 현재 보고 있던 뷰를 다시 로드
        if (this.currentQuery || this.currentKeywords) {
            this.searchPages(this.currentPage);
        } else {
            this.loadAllPages(this.currentPage);
        }
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

// 전역 함수: 모달 닫기
window.hideModal = function() {
    if (window.dataViewer && typeof window.dataViewer.hideModal === 'function') {
        window.dataViewer.hideModal();
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
    
    // 다운로드 버튼 이벤트 리스너
    const downloadCSVBtn = document.getElementById('downloadCSV');
    const downloadJSONBtn = document.getElementById('downloadJSON');
    
    if (downloadCSVBtn) {
        downloadCSVBtn.addEventListener('click', () => {
            dataViewer.downloadCSV();
        });
    }
    
    if (downloadJSONBtn) {
        downloadJSONBtn.addEventListener('click', () => {
            dataViewer.downloadJSON();
        });
    }
    
    // 모달 이벤트 리스너
    const modal = document.getElementById('pageContentModal');
    
    // data.html에서는 inline onclick 이벤트를 사용하므로 별도 이벤트 리스너 불필요
    
    // 모달 배경 클릭 시 닫기
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                dataViewer.hideModal();
            }
        });
    }
    
    // ESC 키로 모달 닫기
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal && modal.style.display === 'block') {
            dataViewer.hideModal();
        }
    });
});

// 일괄 작업 관련 전역 함수들
function toggleSelectAll() {
    const selectAllCheckbox = document.getElementById('selectAll');
    const pageCheckboxes = document.querySelectorAll('.page-checkbox');
    
    pageCheckboxes.forEach(checkbox => {
        checkbox.checked = selectAllCheckbox.checked;
    });
    
    updateBulkActions();
}

function updateBulkActions() {
    const pageCheckboxes = document.querySelectorAll('.page-checkbox');
    const selectedCheckboxes = document.querySelectorAll('.page-checkbox:checked');
    const selectAllCheckbox = document.getElementById('selectAll');
    const selectedCount = document.getElementById('selectedCount');
    const bulkRegenerate = document.getElementById('bulkRegenerate');
    const bulkDelete = document.getElementById('bulkDelete');
    
    const selectedNum = selectedCheckboxes.length;
    const totalNum = pageCheckboxes.length;
    
    // 전체 선택 체크박스 상태 업데이트
    if (selectAllCheckbox) {
        selectAllCheckbox.checked = selectedNum === totalNum && totalNum > 0;
        selectAllCheckbox.indeterminate = selectedNum > 0 && selectedNum < totalNum;
    }
    
    // 선택 개수 표시
    if (selectedCount) {
        selectedCount.textContent = `${selectedNum}개 선택됨`;
    }
    
    // 버튼 활성화/비활성화
    const hasSelection = selectedNum > 0;
    if (bulkRegenerate) bulkRegenerate.disabled = !hasSelection;
    if (bulkDelete) bulkDelete.disabled = !hasSelection;
}

function bulkRegenerate() {
    const selectedCheckboxes = document.querySelectorAll('.page-checkbox:checked');
    const selectedPageIds = Array.from(selectedCheckboxes).map(checkbox => checkbox.dataset.pageId);
    
    if (window.dataViewer) {
        window.dataViewer.bulkRegenerate(selectedPageIds);
    }
}

function bulkDelete() {
    const selectedCheckboxes = document.querySelectorAll('.page-checkbox:checked');
    const selectedPageIds = Array.from(selectedCheckboxes).map(checkbox => checkbox.dataset.pageId);
    
    if (window.dataViewer) {
        window.dataViewer.bulkDelete(selectedPageIds);
    }
}