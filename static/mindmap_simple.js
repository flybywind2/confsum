// 🚨 간단한 mindmap.js 버전
console.log('🟢 mindmap_simple.js 파일이 로드되었습니다!');

// 전역 변수
let currentNodes = [];
let currentLinks = [];
let currentThreshold = 0.2;
let currentSimulation = null;
let currentSvg = null;

// 모달 관련 함수들 (상단에 정의)
async function openPageModal(pageId) {
    try {
        console.log('🔗 페이지 모달 열기:', pageId);
        
        // 모달 요소 확인
        const modal = document.getElementById('pageContentModal');
        if (!modal) {
            console.error('모달 요소를 찾을 수 없습니다');
            return;
        }
        
        // 로딩 표시
        showModal();
        
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
        
        // 현재 페이지 데이터 저장
        currentModalPageData = pageData;
        
        // 모달 제목 설정
        titleEl.textContent = pageData.title || '제목 없음';
        
        // 키워드 태그 생성
        const keywordsHtml = Array.isArray(pageData.keywords) ? 
            pageData.keywords.map(keyword => 
                `<span style="background: #e3f2fd; color: #1976d2; padding: 3px 8px; border-radius: 12px; font-size: 12px; margin: 2px;">${keyword}</span>`
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
        
        // 모달 내용 설정
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
                    ${createSummarySelector(pageData)}
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
        console.error('❌ 페이지 모달 오류:', error);
        const contentEl = document.getElementById('modalContent');
        if (contentEl) {
            contentEl.innerHTML = `
                <div style="text-align: center; padding: 40px; color: #dc3545;">
                    <h4>오류 발생</h4>
                    <p>페이지 내용을 불러오는 중 오류가 발생했습니다.</p>
                    <p style="font-family: monospace; background: #f8f9fa; padding: 10px; border-radius: 5px;">${error.message}</p>
                </div>
            `;
        }
    }
}

function showModal() {
    const modal = document.getElementById('pageContentModal');
    if (modal) {
        modal.style.display = 'block';
        document.body.style.overflow = 'hidden'; // 배경 스크롤 방지
    }
}

function closeModal() {
    const modal = document.getElementById('pageContentModal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto'; // 배경 스크롤 복원
    }
}

// 전역 함수로 등록
window.openPageModal = openPageModal;
window.closeModal = closeModal;

// 키워드 마인드맵 로드
async function loadKeywordMindmap(keyword) {
    console.log(`🎯 키워드 마인드맵 로드: ${keyword}`);
    
    try {
        const response = await fetch(`/mindmap-keyword?keyword=${encodeURIComponent(keyword)}&threshold=0.2`);
        console.log(`📡 API 응답: ${response.status}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log(`📊 데이터: 노드 ${data.nodes?.length || 0}개, 링크 ${data.links?.length || 0}개`);
        
        if (!data.nodes || data.nodes.length === 0) {
            showMessage(`키워드 '${keyword}'와 관련된 페이지가 없습니다.`);
            return;
        }
        
        // 제목 업데이트
        document.querySelector('h1').textContent = `키워드 '${keyword}' 마인드맵`;
        document.querySelector('#subtitle').textContent = `'${keyword}' 키워드를 포함한 ${data.nodes.length}개 페이지의 관계 시각화`;
        
        // 전역 변수에 저장
        currentNodes = data.nodes;
        currentLinks = data.links;
        
        // 간단한 D3 시각화
        createSimpleVisualization(currentNodes, currentLinks);
        
    } catch (error) {
        console.error(`❌ 키워드 마인드맵 로드 실패:`, error);
        showMessage(`키워드 마인드맵 로드 실패: ${error.message}`);
    }
}

// 전체 마인드맵 로드
async function loadAllMindmap() {
    console.log('🌐 전체 마인드맵 로드 시작');
    
    try {
        const response = await fetch(`/mindmap-all?threshold=${currentThreshold}&limit=100`);
        console.log(`📡 API 응답: ${response.status}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log(`📊 데이터: 노드 ${data.nodes?.length || 0}개, 링크 ${data.links?.length || 0}개`);
        
        // 디버깅: 첫 3개 노드의 space_key 확인
        if (data.nodes && data.nodes.length > 0) {
            console.log('🔍 API 응답 첫 3개 노드의 space_key:');
            data.nodes.slice(0, 3).forEach((node, index) => {
                console.log(`  API 노드 ${index + 1}:`, {
                    title: node.title,
                    space_key: node.space_key,
                    keys: Object.keys(node)
                });
            });
        }
        
        if (!data.nodes || data.nodes.length === 0) {
            showMessage('저장된 페이지가 없습니다. 먼저 Confluence 페이지를 처리해주세요.');
            return;
        }
        
        // 제목 업데이트
        document.querySelector('h1').textContent = '전체 페이지 마인드맵';
        document.querySelector('#subtitle').textContent = `총 ${data.nodes.length}개 페이지의 키워드 관계 시각화`;
        
        // 전역 변수에 저장
        currentNodes = data.nodes;
        currentLinks = data.links;
        
        // 간단한 D3 시각화
        createSimpleVisualization(currentNodes, currentLinks);
        
        console.log('✅ 전체 마인드맵 로드 완료');
        
    } catch (error) {
        console.error(`❌ 전체 마인드맵 로드 실패:`, error);
        showMessage(`전체 마인드맵 로드 실패: ${error.message}`);
    }
}

// 전체 키워드 네트워크 마인드맵 로드
async function loadAllKeywordsMindmap() {
    console.log('🏷️ 전체 키워드 네트워크 마인드맵 로드 시작');
    
    try {
        const response = await fetch(`/mindmap-all-keywords?threshold=${currentThreshold}&limit=200`);
        console.log(`📡 API 응답: ${response.status}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log(`📊 데이터: 노드 ${data.nodes?.length || 0}개, 링크 ${data.links?.length || 0}개`);
        
        // 디버깅: 키워드 마인드맵 첫 3개 노드의 space_key 확인
        if (data.nodes && data.nodes.length > 0) {
            console.log('🔍 키워드 마인드맵 API 응답 첫 3개 노드의 space_key:');
            data.nodes.slice(0, 3).forEach((node, index) => {
                console.log(`  키워드 노드 ${index + 1}:`, {
                    title: node.title,
                    space_key: node.space_key,
                    keys: Object.keys(node)
                });
            });
        }
        
        if (!data.nodes || data.nodes.length === 0) {
            showMessage('저장된 키워드가 없습니다. 먼저 Confluence 페이지를 처리해주세요.');
            return;
        }
        
        // 제목 업데이트
        document.querySelector('h1').textContent = '전체 키워드 네트워크 마인드맵';
        document.querySelector('#subtitle').textContent = `${data.nodes.length}개 주요 키워드 간의 관계 네트워크`;
        
        // 전역 변수에 저장
        currentNodes = data.nodes;
        currentLinks = data.links;
        
        // 간단한 D3 시각화
        createSimpleVisualization(currentNodes, currentLinks);
        
        console.log('✅ 전체 키워드 네트워크 마인드맵 로드 완료');
        
    } catch (error) {
        console.error(`❌ 전체 키워드 마인드맵 로드 실패:`, error);
        showMessage(`전체 키워드 마인드맵 로드 실패: ${error.message}`);
    }
}

// 특정 페이지 마인드맵 로드
async function loadSpecificMindmap(parentId) {
    console.log(`📄 특정 페이지 마인드맵 로드 시작: ${parentId}`);
    
    try {
        const apiUrl = `/mindmap/${parentId}?threshold=${currentThreshold}`;
        console.log(`🌐 API 요청 URL: ${apiUrl}`);
        
        const response = await fetch(apiUrl);
        console.log(`📡 API 응답: ${response.status}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log(`📊 데이터: 노드 ${data.nodes?.length || 0}개, 링크 ${data.links?.length || 0}개`);
        
        if (!data.nodes || data.nodes.length === 0) {
            showMessage('해당 페이지와 관련된 마인드맵 데이터가 없습니다.');
            return;
        }
        
        // 중심 노드 찾기
        const centerNode = data.nodes.find(n => n.id === data.center_node);
        const centerTitle = centerNode ? centerNode.title : '알 수 없는 페이지';
        
        // 제목 업데이트
        document.querySelector('h1').textContent = `${centerTitle} - 마인드맵`;
        document.querySelector('#subtitle').textContent = `${data.nodes.length}개 페이지의 키워드 관계 시각화`;
        
        // 전역 변수에 저장
        currentNodes = data.nodes;
        currentLinks = data.links;
        
        // 간단한 D3 시각화
        createSimpleVisualization(currentNodes, currentLinks);
        
        console.log('✅ 특정 페이지 마인드맵 로드 완료');
        
    } catch (error) {
        console.error(`❌ 특정 페이지 마인드맵 로드 실패:`, error);
        showMessage(`특정 페이지 마인드맵 로드 실패: ${error.message}`);
    }
}

// Space별 마인드맵 로드
async function loadSpaceMindmap(spaceKey) {
    console.log(`🏢 Space 마인드맵 로드 시작: ${spaceKey}`);
    
    try {
        const response = await fetch(`/mindmap/space/${spaceKey}?threshold=${currentThreshold}&limit=100`);
        console.log(`📡 API 응답: ${response.status}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log(`📊 Space 마인드맵 데이터:`, {
            nodes: data.nodes.length,
            links: data.links.length,
            space: spaceKey
        });
        
        // 제목 업데이트
        document.querySelector('h1').textContent = `Space "${spaceKey}" 마인드맵`;
        document.querySelector('#subtitle').textContent = `Space "${spaceKey}"의 ${data.nodes.length}개 페이지 관계 시각화`;
        
        currentNodes = data.nodes;
        currentLinks = data.links;
        
        // 간단한 D3 시각화
        createSimpleVisualization(currentNodes, currentLinks);
        
        console.log('✅ Space 마인드맵 로드 완료');
        
    } catch (error) {
        console.error(`❌ Space 마인드맵 로드 실패:`, error);
        showMessage(`Space 마인드맵 로드 실패: ${error.message}`);
    }
}

// 간단한 메시지 표시
function showMessage(message) {
    const svg = d3.select("#mindmapSvg");
    svg.selectAll("*").remove();
    
    svg.append("text")
        .attr("x", "50%")
        .attr("y", "50%")
        .attr("text-anchor", "middle")
        .attr("font-size", "18px")
        .attr("fill", "#333")
        .text(message);
}

// 선택된 페이지 정보 표시
function showSelectedPageInfo(nodeData) {
    console.log('📄 선택된 페이지 정보 표시:', nodeData);
    
    const infoDiv = document.getElementById('selectedPageInfo');
    if (!infoDiv) {
        console.error('❌ selectedPageInfo 요소를 찾을 수 없습니다');
        return;
    }
    
    // 키워드 노드인지 확인
    if (nodeData.id && nodeData.id.startsWith('keyword_')) {
        // 키워드 노드인 경우 - 해당 키워드를 포함하는 모든 페이지 표시
        showKeywordPages(nodeData, infoDiv);
    } else {
        // 일반 페이지 노드인 경우 - 기존 로직
        showSinglePageInfo(nodeData, infoDiv);
    }
    
    console.log('✅ 선택된 페이지 정보 업데이트 완료');
}

// 단일 페이지 정보 표시
function showSinglePageInfo(nodeData, infoDiv) {
    // 키워드 배열 처리
    let keywords = [];
    if (Array.isArray(nodeData.keywords)) {
        keywords = nodeData.keywords;
    } else if (typeof nodeData.keywords === 'string') {
        try {
            keywords = JSON.parse(nodeData.keywords);
        } catch (e) {
            keywords = [nodeData.keywords];
        }
    }
    
    const keywordsText = keywords.length > 0 ? keywords.join(", ") : "키워드 없음";
    const modifiedDate = nodeData.modified_date ? new Date(nodeData.modified_date).toLocaleDateString('ko-KR') : '정보 없음';
    const summary = nodeData.summary || '요약 정보가 없습니다.';
    const truncatedSummary = summary.length > 150 ? summary.substring(0, 150) + '...' : summary;
    const truncatedKeywords = keywordsText.length > 60 ? keywordsText.substring(0, 60) + '...' : keywordsText;
    
    infoDiv.innerHTML = `
        <div style="margin-bottom: 15px; padding: 15px; background: linear-gradient(135deg, #3498db 0%, #2980b9 100%); color: white; border-radius: 8px;">
            <h4 style="margin: 0 0 10px 0; font-size: 18px;">📄 선택된 페이지</h4>
            <div style="display: flex; gap: 20px; flex-wrap: wrap; font-size: 14px;">
                <div><strong>📊 페이지 ID:</strong> ${nodeData.id || "ID 없음"}</div>
                <div><strong>📅 수정일:</strong> ${modifiedDate}</div>
            </div>
        </div>
        <div style="max-height: 450px; overflow-y: auto; border: 1px solid #e0e0e0; border-radius: 8px; background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
            <div style="padding: 15px;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;">
                    <div style="flex: 1;">
                        <h5 style="margin: 0 0 5px 0; color: #2c3e50; font-size: 16px; font-weight: 600;">
                            ${nodeData.url ? `<a href="${nodeData.url}" target="_blank" style="text-decoration: none; color: #3498db;">📄 ${nodeData.title || "제목 없음"}</a>` : `📄 ${nodeData.title || "제목 없음"}`}
                        </h5>
                        <small style="color: #888; font-size: 12px;">
                            ID: ${nodeData.id || "ID 없음"} | 수정일: ${modifiedDate}
                        </small>
                    </div>
                </div>
                
                <div style="margin-bottom: 12px; padding: 10px; background: #f8f9fa; border-radius: 5px; border-left: 3px solid #3498db;">
                    <p style="margin: 0; font-size: 14px; color: #555; line-height: 1.5;">
                        ${truncatedSummary}
                    </p>
                </div>
                
                <div style="margin-bottom: 10px;">
                    <div style="display: inline-block; padding: 5px 10px; background: #e8f4fd; border-radius: 15px; font-size: 12px;">
                        <strong style="color: #2980b9;">🏷️ 키워드:</strong> 
                        <span style="color: #34495e;">${truncatedKeywords}</span>
                    </div>
                </div>
                
                <div style="display: flex; gap: 10px; margin-top: 10px;">
                    ${nodeData.url ? `<button onclick="window.open('${nodeData.url}', '_blank')" style="padding: 6px 12px; background: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">🔗 원본 보기</button>` : ''}
                    <button onclick="window.open('/mindmap?parent_id=${nodeData.id}', '_blank')" style="padding: 6px 12px; background: #27ae60; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">🗺️ 마인드맵</button>
                </div>
            </div>
        </div>
    `;
}

// 키워드와 관련된 모든 페이지 정보 표시
function showKeywordPages(nodeData, infoDiv) {
    const keyword = nodeData.title;
    
    try {
        // summary가 JSON인지 일반 텍스트인지 확인
        let pages;
        if (nodeData.summary.startsWith('[') || nodeData.summary.startsWith('{')) {
            // JSON 형태의 페이지 정보 (기존 키워드 마인드맵)
            pages = JSON.parse(nodeData.summary);
        } else {
            // 단순 텍스트 형태라면 JSON 파싱을 시도해보고, 실패하면 기본 메시지 표시
            try {
                pages = JSON.parse(nodeData.summary);
            } catch (secondError) {
                // JSON 파싱에 실패한 경우 기본 정보만 표시
                infoDiv.innerHTML = `
                    <h4>🔑 키워드: "${keyword}"</h4>
                    <p>${nodeData.summary}</p>
                    <p><em>이 키워드에 대한 상세 페이지 정보를 불러올 수 없습니다.</em></p>
                `;
                return;
            }
        }
        
        // 페이지들을 최근 수정일 순으로 정렬
        pages.sort((a, b) => {
            const dateA = new Date(a.modified_date || a.created_date || '1970-01-01');
            const dateB = new Date(b.modified_date || b.created_date || '1970-01-01');
            return dateB - dateA;
        });
        
        let pagesHtml = `
            <div style="margin-bottom: 15px; padding: 15px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 8px;">
                <h4 style="margin: 0 0 10px 0; font-size: 18px;">🔑 키워드: "${keyword}"</h4>
                <div style="display: flex; gap: 20px; flex-wrap: wrap; font-size: 14px;">
                    <div><strong>📊 포함된 페이지:</strong> ${pages.length}개</div>
                    <div><strong>📅 최근 업데이트:</strong> ${pages[0]?.modified_date ? new Date(pages[0].modified_date).toLocaleDateString('ko-KR') : '정보 없음'}</div>
                </div>
            </div>
            <div style="max-height: 450px; overflow-y: auto; border: 1px solid #e0e0e0; border-radius: 8px; background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
        `;
        
        pages.forEach((page, index) => {
            const pageKeywords = Array.isArray(page.keywords) ? page.keywords.join(", ") : "키워드 없음";
            const modifiedDate = page.modified_date ? new Date(page.modified_date).toLocaleDateString('ko-KR') : '정보 없음';
            const summary = page.summary || '요약 정보가 없습니다.';
            const truncatedSummary = summary.length > 120 ? summary.substring(0, 120) + '...' : summary;
            const truncatedKeywords = pageKeywords.length > 60 ? pageKeywords.substring(0, 60) + '...' : pageKeywords;
            
            pagesHtml += `
                <div style="border-bottom: 1px solid #f0f0f0; padding: 15px; ${index === pages.length - 1 ? 'border-bottom: none;' : ''} transition: all 0.2s;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;">
                        <div style="flex: 1;">
                            <h5 style="margin: 0 0 5px 0; color: #2c3e50; font-size: 16px; font-weight: 600;">
                                <a href="${page.url}" target="_blank" style="text-decoration: none; color: #3498db;">
                                    📄 ${page.title}
                                </a>
                            </h5>
                            <small style="color: #888; font-size: 12px;">
                                ID: ${page.page_id} | 수정일: ${modifiedDate}
                            </small>
                        </div>
                    </div>
                    
                    <div style="margin-bottom: 12px; padding: 10px; background: #f8f9fa; border-radius: 5px; border-left: 3px solid #3498db;">
                        <p style="margin: 0; font-size: 14px; color: #555; line-height: 1.5;">
                            ${truncatedSummary}
                        </p>
                    </div>
                    
                    <div style="margin-bottom: 10px;">
                        <div style="display: inline-block; padding: 5px 10px; background: #e8f4fd; border-radius: 15px; font-size: 12px;">
                            <strong style="color: #2980b9;">🏷️ 키워드:</strong> 
                            <span style="color: #34495e;">${truncatedKeywords}</span>
                        </div>
                    </div>
                    
                    <div style="display: flex; gap: 10px; margin-top: 10px;">
                        <button class="detail-btn" data-page-id="${page.page_id}" 
                                style="background: linear-gradient(135deg, #3498db, #2980b9); color: white; border: none; padding: 6px 12px; border-radius: 5px; font-size: 12px; cursor: pointer; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                            📖 상세보기
                        </button>
                        <a href="${page.url}" target="_blank" 
                           style="background: linear-gradient(135deg, #27ae60, #229954); color: white; text-decoration: none; padding: 6px 12px; border-radius: 5px; font-size: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                            🔗 원본보기
                        </a>
                    </div>
                </div>
            `;
        });
        
        pagesHtml += `
            </div>
            <div style="margin-top: 15px; padding: 10px; background: #f1f8ff; border-radius: 5px; border-left: 3px solid #3498db;">
                <small style="color: #2c3e50; line-height: 1.4;">
                    💡 <strong>팁:</strong> 페이지는 최근 수정일 순으로 정렬되어 있습니다. 
                    '상세보기'로 페이지 내용을 미리 보거나 '원본보기'로 Confluence에서 직접 확인할 수 있습니다.
                </small>
            </div>
        `;
        
        infoDiv.innerHTML = pagesHtml;
        
        // 상세보기 버튼들에 이벤트 리스너 추가
        const detailButtons = infoDiv.querySelectorAll('.detail-btn');
        detailButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                const pageId = this.getAttribute('data-page-id');
                console.log('상세보기 버튼 클릭:', pageId);
                openPageModal(pageId);
            });
        });
        
    } catch (error) {
        console.error('키워드 페이지 정보 파싱 오류:', error);
        infoDiv.innerHTML = `
            <h4>🔑 키워드: "${keyword}"</h4>
            <p style="color: #dc3545;">페이지 정보를 불러오는 중 오류가 발생했습니다.</p>
        `;
    }
}

// 간단한 D3 시각화
function createSimpleVisualization(nodes, links) {
    console.log('🎨 간단한 시각화 생성 시작');
    
    const svg = d3.select("#mindmapSvg");
    currentSvg = svg; // 전역 변수에 저장
    const width = parseInt(svg.attr("width")) || 800;
    const height = parseInt(svg.attr("height")) || 600;
    
    // 임계값에 따라 링크 필터링
    const filteredLinks = links.filter(link => link.weight >= currentThreshold);
    console.log(`🔗 링크 필터링: 전체 ${links.length}개 → 임계값 ${currentThreshold} 적용 후 ${filteredLinks.length}개`);
    
    // 기존 내용 제거
    svg.selectAll("*").remove();
    
    // 줌 기능 추가
    const zoom = d3.zoom()
        .scaleExtent([0.1, 4])
        .on("zoom", (event) => {
            mainGroup.attr("transform", event.transform);
        });
    
    svg.call(zoom);
    
    // 메인 그룹 추가
    const mainGroup = svg.append("g").attr("class", "main-group");
    
    // 시뮬레이션 생성
    const simulation = d3.forceSimulation(nodes)
        .force("link", d3.forceLink(filteredLinks).id(d => d.id).distance(100))
        .force("charge", d3.forceManyBody().strength(-300))
        .force("center", d3.forceCenter(width / 2, height / 2));
    
    currentSimulation = simulation; // 전역 변수에 저장
    
    // 링크 생성
    const link = mainGroup.selectAll(".link")
        .data(filteredLinks)
        .enter().append("line")
        .attr("class", "link")
        .attr("stroke", "#999")
        .attr("stroke-width", 2);
    
    // 노드 생성
    const node = mainGroup.selectAll(".node")
        .data(nodes)
        .enter().append("g")
        .attr("class", "node");
    
    // 노드 원
    node.append("circle")
        .attr("r", d => d.size || 20)
        .attr("fill", d => {
            // 키워드 노드인지 확인 (ID가 'keyword_'로 시작)
            if (d.id && d.id.startsWith('keyword_')) {
                return "#ff6b6b";  // 키워드 노드는 빨간색
            }
            return "#4ecdc4";  // 일반 페이지 노드는 청록색
        })
        .attr("stroke", "#333")
        .attr("stroke-width", 2);
    
    // 노드 텍스트
    node.append("text")
        .attr("dy", ".35em")
        .attr("text-anchor", "middle")
        .attr("font-size", d => {
            // 키워드 노드인지 확인
            if (d.id && d.id.startsWith('keyword_')) {
                return "14px";  // 키워드 노드는 큰 글자
            }
            return "12px";  // 일반 노드는 기본 크기
        })
        .attr("fill", "white")
        .attr("font-weight", d => {
            // 키워드 노드는 굵게
            if (d.id && d.id.startsWith('keyword_')) {
                return "bold";
            }
            return "normal";
        })
        .text(d => {
            // 키워드 노드는 전체 텍스트 표시, 일반 노드는 10자 제한
            if (d.id && d.id.startsWith('keyword_')) {
                return d.title.length > 8 ? d.title.substring(0, 8) + "..." : d.title;
            }
            return d.title.length > 10 ? d.title.substring(0, 10) + "..." : d.title;
        });
    
    // 툴팁
    node.append("title")
        .text(d => {
            if (d.id && d.id.startsWith('keyword_')) {
                // 키워드 노드 툴팁 - 포함된 페이지 수 표시
                try {
                    const pages = JSON.parse(d.summary);
                    return `키워드: ${d.title}\n포함된 페이지: ${pages.length}개\n클릭하여 상세 정보 보기`;
                } catch (e) {
                    return `키워드: ${d.title}\n클릭하여 상세 정보 보기`;
                }
            } else {
                // 일반 페이지 노드 툴팁
                return `${d.title}\n키워드: ${d.keywords ? d.keywords.join(", ") : "없음"}`;
            }
        });
    
    // 클릭 이벤트 추가
    node.on("click", function(event, d) {
        console.log('🖱️ 노드 클릭됨:', d);
        showSelectedPageInfo(d);
        
        // 선택된 노드 강조
        svg.selectAll(".node circle")
            .attr("stroke", "#333")
            .attr("stroke-width", 2);
        
        d3.select(this).select("circle")
            .attr("stroke", "#ff6b6b")
            .attr("stroke-width", 4);
    });
    
    // 드래그 기능
    node.call(d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended));
    
    // 시뮬레이션 업데이트
    simulation.on("tick", () => {
        link
            .attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);
        
        node.attr("transform", d => `translate(${d.x},${d.y})`);
    });
    
    function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }
    
    function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }
    
    function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }
    
    console.log('✅ 간단한 시각화 생성 완료');
}

// 임계값 업데이트 함수
function updateThreshold(newThreshold) {
    console.log(`🔄 임계값 업데이트: ${currentThreshold} → ${newThreshold}`);
    currentThreshold = newThreshold;
    
    if (currentNodes.length > 0) {
        console.log('🔁 시각화 재생성 시작');
        createSimpleVisualization(currentNodes, currentLinks);
    }
}

// 뷰 리셋 함수
function resetView() {
    console.log('🔄 뷰 리셋 시작');
    
    // Space 필터 초기화 (Tom Select)
    if (spaceSelectInstance) {
        spaceSelectInstance.clear();
        console.log('🧹 Space 필터 초기화 (Tom Select)');
    }
    
    // 키워드 필터 초기화
    const keywordFilter = document.getElementById('keywordFilter');
    if (keywordFilter) {
        keywordFilter.value = '';
        console.log('🧹 키워드 필터 초기화');
    }
    
    // 임계값을 기본값으로 리셋
    const thresholdSlider = document.getElementById('thresholdSlider');
    const thresholdValue = document.getElementById('thresholdValue');
    if (thresholdSlider && thresholdValue) {
        thresholdSlider.value = 0.2;
        thresholdValue.textContent = '0.2';
        currentThreshold = 0.2;
        console.log('🎛️ 임계값을 기본값(0.2)으로 리셋');
    }
    
    // SVG 줌 리셋
    if (currentSvg) {
        currentSvg.transition()
            .duration(750)
            .call(d3.zoom().transform, d3.zoomIdentity);
        console.log('🔍 줌 리셋');
    }
    
    // 시뮬레이션 재시작
    if (currentSimulation) {
        currentSimulation.alpha(1).restart();
        console.log('⚡ 시뮬레이션 재시작');
    }
    
    // 시각화 재생성
    if (currentNodes.length > 0) {
        console.log('🎨 시각화 재생성');
        createSimpleVisualization(currentNodes, currentLinks);
    }
    
    console.log('✅ 뷰 리셋 완료');
}

// 키워드 필터 함수
function filterByKeyword(keyword) {
    if (!currentSvg) return;
    
    console.log(`🔍 키워드 필터 적용: "${keyword}"`);
    
    if (!keyword) {
        // 필터 제거 - 모든 노드와 링크 표시
        currentSvg.selectAll(".node").style("opacity", 1);
        currentSvg.selectAll(".link").style("opacity", 1);
        console.log('🧹 키워드 필터 제거됨');
        return;
    }
    
    // 키워드를 포함한 노드 찾기
    const filteredNodes = currentNodes.filter(node => {
        const titleMatch = node.title.toLowerCase().includes(keyword.toLowerCase());
        let keywordMatch = false;
        
        if (Array.isArray(node.keywords)) {
            keywordMatch = node.keywords.some(k => k.toLowerCase().includes(keyword.toLowerCase()));
        } else if (typeof node.keywords === 'string') {
            try {
                const keywords = JSON.parse(node.keywords);
                keywordMatch = keywords.some(k => k.toLowerCase().includes(keyword.toLowerCase()));
            } catch (e) {
                keywordMatch = node.keywords.toLowerCase().includes(keyword.toLowerCase());
            }
        }
        
        return titleMatch || keywordMatch;
    });
    
    const filteredNodeIds = new Set(filteredNodes.map(n => n.id));
    console.log(`📊 필터 결과: ${filteredNodes.length}/${currentNodes.length} 노드`);
    
    // 노드 투명도 조정
    currentSvg.selectAll(".node")
        .style("opacity", d => filteredNodeIds.has(d.id) ? 1 : 0.2);
    
    // 링크 투명도 조정
    currentSvg.selectAll(".link")
        .style("opacity", d => 
            filteredNodeIds.has(d.source.id) && filteredNodeIds.has(d.target.id) ? 1 : 0.1
        );
}

// 기존 단일 Space 필터 함수는 제거됨 - 다중 선택 함수로 대체

// 이벤트 리스너 등록
function bindEventListeners() {
    // 임계값 슬라이더
    const thresholdSlider = document.getElementById('thresholdSlider');
    const thresholdValue = document.getElementById('thresholdValue');
    
    if (thresholdSlider && thresholdValue) {
        console.log('🎛️ 임계값 슬라이더 이벤트 등록');
        
        thresholdSlider.addEventListener('input', (e) => {
            const newThreshold = parseFloat(e.target.value);
            thresholdValue.textContent = newThreshold;
            updateThreshold(newThreshold);
        });
        
        // 초기값 설정
        thresholdSlider.value = currentThreshold;
        thresholdValue.textContent = currentThreshold;
        
        console.log('✅ 임계값 슬라이더 이벤트 등록 완료');
    } else {
        console.warn('⚠️ 임계값 슬라이더 요소를 찾을 수 없습니다');
    }
    
    // Space 필터는 이제 Tom Select로 처리되므로 별도 이벤트 리스너 불필요
    console.log('🏢 Space 필터는 Tom Select로 관리됩니다.');
    
    // 모든 Space 선택 취소 버튼
    const clearSpaceFilterBtn = document.getElementById('clearSpaceFilter');
    if (clearSpaceFilterBtn) {
        console.log('🧹 모든 Space 선택 취소 버튼 이벤트 등록');
        clearSpaceFilterBtn.addEventListener('click', () => {
            if (spaceSelectInstance) {
                spaceSelectInstance.clear();
                console.log('🧹 모든 Space 선택 취소됨');
            }
        });
        console.log('✅ 모든 Space 선택 취소 버튼 이벤트 등록 완료');
    } else {
        console.warn('⚠️ 모든 Space 선택 취소 버튼을 찾을 수 없습니다');
    }
    
    // 키워드 필터
    const keywordFilter = document.getElementById('keywordFilter');
    if (keywordFilter) {
        console.log('🔍 키워드 필터 이벤트 등록');
        keywordFilter.addEventListener('input', (e) => {
            filterByKeyword(e.target.value);
        });
        console.log('✅ 키워드 필터 이벤트 등록 완료');
    } else {
        console.warn('⚠️ 키워드 필터 요소를 찾을 수 없습니다');
    }
    
    // 뷰 리셋 버튼
    const resetViewBtn = document.getElementById('resetView');
    if (resetViewBtn) {
        console.log('🔄 뷰 리셋 버튼 이벤트 등록');
        resetViewBtn.addEventListener('click', () => {
            resetView();
        });
        console.log('✅ 뷰 리셋 버튼 이벤트 등록 완료');
    } else {
        console.warn('⚠️ 뷰 리셋 버튼을 찾을 수 없습니다');
    }
    
    // 키워드 마인드맵 이동 버튼
    const goToKeywordMindmapBtn = document.getElementById('goToKeywordMindmap');
    if (goToKeywordMindmapBtn) {
        console.log('🔗 키워드 마인드맵 버튼 이벤트 등록');
        goToKeywordMindmapBtn.addEventListener('click', () => {
            goToKeywordMindmap();
        });
        console.log('✅ 키워드 마인드맵 버튼 이벤트 등록 완료');
    } else {
        console.warn('⚠️ 키워드 마인드맵 버튼을 찾을 수 없습니다');
    }
    
    // 전체 마인드맵 이동 버튼
    const goToAllMindmapBtn = document.getElementById('goToAllMindmap');
    if (goToAllMindmapBtn) {
        console.log('🌐 전체 마인드맵 버튼 이벤트 등록');
        goToAllMindmapBtn.addEventListener('click', () => {
            goToAllMindmap();
        });
        console.log('✅ 전체 마인드맵 버튼 이벤트 등록 완료');
    } else {
        console.warn('⚠️ 전체 마인드맵 버튼을 찾을 수 없습니다');
    }
}

// 전체 마인드맵으로 이동하는 함수
async function goToAllMindmap() {
    console.log('🚀 전체 마인드맵으로 이동 시작');
    
    try {
        // 페이지 통계 확인
        const response = await fetch('/pages/stats');
        console.log('📡 통계 API 응답:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const stats = await response.json();
        console.log('📊 통계 정보:', stats);
        
        if (stats.total_pages === 0) {
            alert('저장된 페이지가 없습니다. 먼저 Confluence 페이지를 처리해주세요.');
            return;
        }
        
        console.log('🌐 전체 마인드맵으로 이동');
        const url = '/mindmap?mode=all';
        console.log('🔗 생성된 URL:', url);
        
        // 현재 창에서 이동
        window.location.href = url;
        
    } catch (error) {
        console.error('❌ 전체 마인드맵 이동 오류:', error);
        alert(`오류 발생: ${error.message}`);
    }
}

// 키워드 마인드맵으로 이동하는 함수
async function goToKeywordMindmap() {
    console.log('🚀 전체 키워드 네트워크 마인드맵으로 이동 시작');
    
    try {
        // 페이지 통계 확인 (키워드 존재 여부)
        const response = await fetch('/pages/stats');
        console.log('📡 통계 API 응답:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const stats = await response.json();
        console.log('📊 통계 정보:', stats);
        
        if (stats.total_pages === 0) {
            alert('저장된 페이지가 없습니다. 먼저 Confluence 페이지를 처리해주세요.');
            return;
        }
        
        if (stats.total_unique_keywords === 0) {
            alert('저장된 키워드가 없습니다. 먼저 Confluence 페이지를 처리해주세요.');
            return;
        }
        
        // 전체 키워드 네트워크 마인드맵으로 이동
        console.log('🏷️ 전체 키워드 네트워크 마인드맵으로 이동');
        const url = '/mindmap?mode=all_keywords';
        console.log('🔗 생성된 URL:', url);
        
        // 현재 창에서 이동
        window.location.href = url;
        
    } catch (error) {
        console.error('❌ 키워드 마인드맵 이동 오류:', error);
        alert(`오류 발생: ${error.message}`);
    }
}

// 다중 Space 필터링 함수
function filterByMultipleSpaces(selectedSpaces) {
    if (!currentSvg || !currentNodes) return;
    
    console.log(`🏢 다중 Space 필터 적용: [${selectedSpaces.join(', ')}]`);
    
    // 선택된 Space들에 해당하는 노드 찾기
    const filteredNodes = currentNodes.filter(node => {
        return selectedSpaces.includes(node.space_key);
    });
    
    const filteredNodeIds = new Set(filteredNodes.map(n => n.id));
    console.log(`📊 다중 Space 필터 결과: ${filteredNodes.length}/${currentNodes.length} 노드`);
    
    // 해당하지 않는 노드들은 완전히 숨기기
    currentSvg.selectAll(".node")
        .style("display", d => filteredNodeIds.has(d.id) ? "block" : "none");
    
    // 해당하지 않는 링크들도 완전히 숨기기
    currentSvg.selectAll(".link")
        .style("display", d => 
            filteredNodeIds.has(d.source.id) && filteredNodeIds.has(d.target.id) ? "block" : "none"
        );
    
    // 시뮬레이션 재시작 (필터된 노드들의 위치 재조정)
    if (currentSimulation) {
        currentSimulation.alpha(0.3).restart();
    }
}

// 모든 노드 표시 함수
function showAllNodes() {
    if (!currentSvg) return;
    
    console.log('👁️ 모든 노드 표시');
    
    // 모든 노드와 링크 표시
    currentSvg.selectAll(".node").style("display", "block");
    currentSvg.selectAll(".link").style("display", "block");
    
    // 시뮬레이션 재시작
    if (currentSimulation) {
        currentSimulation.alpha(0.3).restart();
    }
}

// Space 목록 로드 함수 및 Tom Select 초기화
let spaceSelectInstance = null; // Tom Select 인스턴스 저장

async function loadSpaceList(currentSpace = null) {
    try {
        const response = await fetch('/api/spaces');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        const spaceFilter = document.getElementById('spaceFilter');
        
        if (!spaceFilter) {
            console.log('🔍 spaceFilter 요소가 없습니다.');
            return;
        }
        
        // 기존 Tom Select 인스턴스가 있으면 제거
        if (spaceSelectInstance) {
            spaceSelectInstance.destroy();
        }
        
        // Space 옵션 추가
        data.spaces.forEach(space => {
            const option = document.createElement('option');
            option.value = space.space_key;
            option.textContent = `${space.space_key} (${space.page_count}개)`;
            spaceFilter.appendChild(option);
        });
        
        // Tom Select 초기화 (다중 선택 가능)
        spaceSelectInstance = new TomSelect('#spaceFilter', {
            maxItems: null, // 무제한 선택 허용
            placeholder: 'Space를 선택하세요...',
            allowEmptyOption: true,
            hideSelected: false, // 선택된 항목도 옵션에서 보이게 함
            closeAfterSelect: false, // 선택 후에도 드롭다운 열린 상태 유지
            onDelete: function(values, evt) {
                // Delete/Backspace 키로 선택된 항목들 제거
                console.log(`⌫ 키보드로 Space 제거: [${values.join(', ')}]`);
                return true; // 제거 허용
            },
            onItemAdd: function(value, item) {
                console.log(`🏢 Space 추가: ${value}`);
                updateSpaceFilter();
                // 추가된 항목에 클릭 이벤트로 제거 기능 추가
                addRemoveButtonToItem(item, value);
            },
            onItemRemove: function(value, item) {
                console.log(`🏢 Space 제거: ${value}`);
                updateSpaceFilter();
            },
            onClear: function() {
                console.log('🧹 모든 Space 필터 제거');
                updateSpaceFilter();
            },
            render: {
                item: function(data, escape) {
                    return `<div class="space-item" data-value="${escape(data.value)}">
                        <span class="space-text">${escape(data.text)}</span>
                        <button class="space-remove" type="button" title="제거">×</button>
                    </div>`;
                }
            }
        });
        
        // 현재 space가 있으면 선택
        if (currentSpace) {
            spaceSelectInstance.addItem(currentSpace);
            console.log(`🏢 Space 필터 설정: ${currentSpace}`);
        }
        
        console.log(`✅ ${data.spaces.length}개 Space 로드 완료 (Tom Select 초기화됨)`);
        
    } catch (error) {
        console.error('❌ Space 목록 로딩 실패:', error);
    }
}

// Space 필터 업데이트 함수
function updateSpaceFilter() {
    if (!spaceSelectInstance || !currentNodes) return;
    
    const selectedSpaces = spaceSelectInstance.getValue();
    console.log(`🏢 선택된 Space들: [${selectedSpaces.join(', ')}]`);
    
    if (selectedSpaces.length === 0) {
        // 선택된 Space가 없으면 모든 노드 표시
        showAllNodes();
    } else {
        // 선택된 Space들에 해당하는 노드만 표시
        filterByMultipleSpaces(selectedSpaces);
    }
}

// 추가된 항목에 제거 버튼 이벤트 추가
function addRemoveButtonToItem(item, value) {
    const removeButton = item.querySelector('.space-remove');
    if (removeButton) {
        removeButton.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log(`🗑️ X 버튼으로 Space 제거: ${value}`);
            spaceSelectInstance.removeItem(value);
        });
    }
}

// DOM 로드 시 초기화
document.addEventListener('DOMContentLoaded', async () => {
    console.log('📋 DOM 로드 완료');
    
    try {
        // URL 파라미터 확인
        const urlParams = new URLSearchParams(window.location.search);
        const mode = urlParams.get('mode');
        const keyword = urlParams.get('keyword');
        const parentId = urlParams.get('parent_id');
        const space = urlParams.get('space');
        const type = urlParams.get('type');
        
        console.log('🔍 URL 파라미터:');
        console.log('  mode:', mode);
        console.log('  keyword:', keyword);
        console.log('  parent_id:', parentId);
        console.log('  space:', space);
        console.log('  type:', type);
        
        // Space 목록 로드
        await loadSpaceList(space);
        
        // SVG 크기 설정
        const container = document.querySelector('.mindmap-container');
        const svg = d3.select("#mindmapSvg");
        
        if (container && svg.node()) {
            const width = container.clientWidth;
            const height = container.clientHeight;
            svg.attr("width", width).attr("height", height);
            console.log(`📏 SVG 크기 설정: ${width}x${height}`);
        }
        
        // 이벤트 리스너 등록
        bindEventListeners();
        
        // 모드에 따라 적절한 버튼 표시
        const keywordMindmapBtn = document.getElementById('goToKeywordMindmap');
        const allMindmapBtn = document.getElementById('goToAllMindmap');
        
        
        // 1. 키워드 모드 처리 (최우선)
        if (mode === 'keyword' && keyword) {
            console.log('🎯 키워드 모드 감지, 로드 시작');
            // 키워드 모드에서는 전체 마인드맵 버튼 표시
            if (keywordMindmapBtn) keywordMindmapBtn.style.display = 'none';
            if (allMindmapBtn) allMindmapBtn.style.display = 'inline-block';
            loadKeywordMindmap(keyword);
        } 
        // 2. 전체 모드 처리
        else if (mode === 'all') {
            console.log('🌐 전체 모드 감지, 로드 시작');
            // 전체 모드에서는 키워드 마인드맵 버튼 표시
            if (keywordMindmapBtn) keywordMindmapBtn.style.display = 'inline-block';
            if (allMindmapBtn) allMindmapBtn.style.display = 'none';
            loadAllMindmap();
        } 
        // 2-1. 전체 키워드 네트워크 모드 처리
        else if (mode === 'all_keywords') {
            console.log('🏷️ 전체 키워드 네트워크 모드 감지, 로드 시작');
            // 키워드 네트워크 모드에서는 전체 마인드맵 버튼 표시
            if (keywordMindmapBtn) keywordMindmapBtn.style.display = 'none';
            if (allMindmapBtn) allMindmapBtn.style.display = 'inline-block';
            loadAllKeywordsMindmap();
        } 
        // 3. Space 모드 처리 (space가 있는 경우)
        else if (space) {
            console.log(`🏢 Space 모드 감지, 로드 시작: ${space}, type: ${type}`);
            
            if (type === 'keyword') {
                // 키워드 마인드맵: 전체 키워드 네트워크 로드 후 Space 필터 적용
                console.log('🏷️ Space 키워드 마인드맵 로드');
                if (keywordMindmapBtn) keywordMindmapBtn.style.display = 'none';
                if (allMindmapBtn) allMindmapBtn.style.display = 'inline-block';
                
                // 키워드 마인드맵 로드 후 Space 필터 적용
                await loadAllKeywordsMindmap();
                
                // 마인드맵 로드 완료 후 Space 필터 적용
                if (space) {
                    console.log(`🏷️ 키워드 마인드맵에 Space 필터 적용 대기: ${space}`);
                    setTimeout(() => {
                        if (spaceSelectInstance) {
                            console.log(`🏷️ Space 필터 적용 실행: ${space}`);
                            spaceSelectInstance.clear();
                            spaceSelectInstance.addItem(space);
                            
                            // 제목도 Space에 맞게 업데이트
                            document.querySelector('h1').textContent = `${space} Space 키워드 네트워크 마인드맵`;
                        } else {
                            console.warn('❌ spaceSelectInstance가 아직 생성되지 않음');
                        }
                    }, 1000); // 더 긴 지연으로 안정성 확보
                }
            } else {
                // 타이틀 마인드맵: Space 전용 마인드맵 로드
                console.log('🗺️ Space 타이틀 마인드맵 로드');
                if (keywordMindmapBtn) keywordMindmapBtn.style.display = 'inline-block';
                if (allMindmapBtn) allMindmapBtn.style.display = 'none';
                loadSpaceMindmap(space);
            }
        } 
        // 4. 특정 페이지 모드 처리 (parent_id가 있는 경우)
        else if (parentId) {
            console.log('📄 특정 페이지 모드 감지, 로드 시작:', parentId);
            // 특정 페이지 모드에서는 키워드 마인드맵 버튼 표시
            if (keywordMindmapBtn) keywordMindmapBtn.style.display = 'inline-block';
            if (allMindmapBtn) allMindmapBtn.style.display = 'none';
            loadSpecificMindmap(parentId);
        } 
        // 5. 모든 조건에 해당하지 않는 경우
        else {
            console.log('❌ 알 수 없는 모드');
            // 기본 상태에서는 키워드 마인드맵 버튼만 표시
            if (keywordMindmapBtn) keywordMindmapBtn.style.display = 'inline-block';
            if (allMindmapBtn) allMindmapBtn.style.display = 'none';
            showMessage('부모 페이지 ID가 지정되지 않았습니다. 홈페이지에서 마인드맵 버튼을 사용해주세요.');
        }
        
    } catch (error) {
        console.error('❌ 초기화 실패:', error);
        showMessage(`초기화 실패: ${error.message}`);
    }
});

// 모달 외부 클릭 시 닫기
window.onclick = function(event) {
    const modal = document.getElementById('pageContentModal');
    if (event.target === modal) {
        closeModal();
    }
}

// ESC 키로 모달 닫기
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        const modal = document.getElementById('pageContentModal');
        if (modal && modal.style.display === 'block') {
            closeModal();
        }
    }
});

// 요약 선택기 생성 함수
function createSummarySelector(pageData) {
    const hasChunkBasedSummary = pageData.chunk_based_summary && pageData.chunk_based_summary !== pageData.summary;
    
    if (!hasChunkBasedSummary) {
        return ''; // 두 요약이 같거나 chunk 기반 요약이 없으면 선택기 숨김
    }
    
    return `
        <div style="display: flex; gap: 10px; margin-bottom: 15px; flex-wrap: wrap;">
            <div id="modal-summary-tab-standard" onclick="switchModalSummary('standard')" 
                 style="padding: 6px 12px; border: 1px solid #ddd; background: #3498db; color: white; border-radius: 4px; cursor: pointer; font-size: 14px; transition: all 0.3s;">
                일반 요약
            </div>
            <div id="modal-summary-tab-chunk" onclick="switchModalSummary('chunk')" 
                 style="padding: 6px 12px; border: 1px solid #ddd; background: #f8f9fa; border-radius: 4px; cursor: pointer; font-size: 14px; transition: all 0.3s;">
                RAG 요약
            </div>
        </div>
    `;
}

// 모달에서 요약 전환 함수
function switchModalSummary(summaryType) {
    const standardTab = document.getElementById('modal-summary-tab-standard');
    const chunkTab = document.getElementById('modal-summary-tab-chunk');
    const summaryContent = document.getElementById('modal-summary-content');
    
    if (!standardTab || !chunkTab || !summaryContent) return;
    
    // 현재 모달에 표시된 페이지 데이터 가져오기 (전역 변수 또는 DOM에서)
    const currentPageData = getCurrentPageData();
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

// 현재 페이지 데이터를 저장하기 위한 전역 변수
let currentModalPageData = null;

// getCurrentPageData 함수 구현
function getCurrentPageData() {
    return currentModalPageData;
}

console.log('🔗 mindmap_simple.js 로드 완료');