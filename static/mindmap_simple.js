// 🚨 간단한 mindmap.js 버전
console.log('🟢 mindmap_simple.js 파일이 로드되었습니다!');

// 전역 변수
let currentNodes = [];
let currentLinks = [];
let currentThreshold = 0.2;
let currentSimulation = null;
let currentSvg = null;

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
    
    infoDiv.innerHTML = `
        <h4>${nodeData.title || "제목 없음"}</h4>
        <p><strong>페이지 ID:</strong> ${nodeData.id || "ID 없음"}</p>
        <p><strong>키워드:</strong> ${keywordsText}</p>
        <p><strong>요약:</strong> ${nodeData.summary || "요약 없음"}</p>
        ${nodeData.url ? `<p><strong>URL:</strong> <a href="${nodeData.url}" target="_blank">${nodeData.url}</a></p>` : ''}
    `;
}

// 키워드와 관련된 모든 페이지 정보 표시
function showKeywordPages(nodeData, infoDiv) {
    const keyword = nodeData.title;
    
    try {
        // summary에서 페이지 정보 JSON 파싱
        const pages = JSON.parse(nodeData.summary);
        
        let pagesHtml = `
            <h4>🔑 키워드: "${keyword}"</h4>
            <p><strong>포함된 페이지 수:</strong> ${pages.length}개</p>
            <div style="max-height: 400px; overflow-y: auto; border: 1px solid #ddd; border-radius: 5px; padding: 10px; margin-top: 10px;">
        `;
        
        pages.forEach((page, index) => {
            const pageKeywords = Array.isArray(page.keywords) ? page.keywords.join(", ") : "키워드 없음";
            
            pagesHtml += `
                <div style="margin-bottom: 15px; padding: 10px; background: #f8f9fa; border-radius: 5px; border-left: 3px solid #007bff;">
                    <div style="font-weight: bold; color: #2c3e50; margin-bottom: 5px;">
                        ${index + 1}. ${page.title}
                    </div>
                    <div style="font-size: 0.9em; color: #6c757d; margin-bottom: 5px;">
                        ID: ${page.page_id}
                    </div>
                    <div style="margin-bottom: 5px;">
                        <strong>키워드:</strong> ${pageKeywords}
                    </div>
                    <div style="margin-bottom: 5px;">
                        <strong>요약:</strong> ${page.summary || '요약 없음'}
                    </div>
                    ${page.url ? `
                        <div>
                            <a href="${page.url}" target="_blank" style="color: #007bff; text-decoration: none;">
                                📄 원본 페이지 보기
                            </a> |
                            <a href="#" onclick="window.openPageModal('${page.page_id}')" style="color: #28a745; text-decoration: none;">
                                📖 상세 내용 보기
                            </a>
                        </div>
                    ` : ''}
                </div>
            `;
        });
        
        pagesHtml += `</div>`;
        
        infoDiv.innerHTML = pagesHtml;
        
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
    console.log('🚀 전체 키워드 마인드맵으로 이동 시작');
    
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
        
        // 가장 빈도가 높은 키워드를 기본값으로 사용하여 키워드 마인드맵으로 이동
        if (stats.top_keywords && stats.top_keywords.length > 0) {
            const topKeyword = stats.top_keywords[0].keyword;
            console.log('🔝 최상위 키워드 사용:', topKeyword);
            
            const url = `/mindmap?mode=keyword&keyword=${encodeURIComponent(topKeyword)}`;
            console.log('🔗 생성된 URL:', url);
            
            // 현재 창에서 이동
            window.location.href = url;
        } else {
            alert('키워드 정보를 불러올 수 없습니다.');
        }
        
    } catch (error) {
        console.error('❌ 키워드 마인드맵 이동 오류:', error);
        alert(`오류 발생: ${error.message}`);
    }
}

// 전역 함수: 페이지 모달 열기 (data.js와 동일한 기능)
window.openPageModal = async function(pageId) {
    try {
        console.log('🔗 페이지 모달 열기:', pageId);
        
        // 페이지 내용 가져오기
        const response = await fetch(`/pages/${pageId}/content`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const pageData = await response.json();
        
        // 새 창에서 페이지 내용 표시
        const newWindow = window.open('', '_blank', 'width=900,height=700,scrollbars=yes,resizable=yes');
        
        const content = `
            <!DOCTYPE html>
            <html>
            <head>
                <title>${pageData.title}</title>
                <meta charset="utf-8">
                <style>
                    body { 
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                        margin: 0; 
                        padding: 20px; 
                        line-height: 1.6; 
                        background-color: #f8f9fa;
                    }
                    .container {
                        max-width: 800px;
                        margin: 0 auto;
                        background: white;
                        border-radius: 8px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                        overflow: hidden;
                    }
                    .header { 
                        background: #2c3e50; 
                        color: white; 
                        padding: 20px; 
                        margin-bottom: 0; 
                    }
                    .title { 
                        margin: 0 0 10px 0; 
                        font-size: 1.8em; 
                        font-weight: 600;
                    }
                    .meta { 
                        opacity: 0.8; 
                        font-size: 0.9em; 
                    }
                    .meta a { 
                        color: #3498db; 
                        text-decoration: none; 
                    }
                    .meta a:hover { 
                        text-decoration: underline; 
                    }
                    .content-area {
                        padding: 20px;
                    }
                    .section { 
                        margin: 25px 0; 
                    }
                    .section-title { 
                        color: #2c3e50; 
                        font-weight: 600; 
                        margin-bottom: 15px; 
                        font-size: 1.1em;
                        border-bottom: 2px solid #ecf0f1;
                        padding-bottom: 8px;
                    }
                    .keyword-tag { 
                        display: inline-block; 
                        background: #3498db; 
                        color: white; 
                        padding: 4px 12px; 
                        margin: 3px; 
                        border-radius: 20px; 
                        font-size: 0.85em; 
                        font-weight: 500;
                    }
                    .content-text { 
                        background: #f8f9fa; 
                        padding: 20px; 
                        border-radius: 6px; 
                        white-space: pre-wrap; 
                        max-height: 400px; 
                        overflow-y: auto; 
                        border: 1px solid #e9ecef;
                        font-family: 'Courier New', monospace;
                        font-size: 0.9em;
                        line-height: 1.5;
                    }
                    .summary-text { 
                        background: #e8f6ff; 
                        padding: 20px; 
                        border-radius: 6px; 
                        border-left: 4px solid #3498db; 
                        font-style: italic;
                    }
                    .keywords-container {
                        min-height: 50px;
                    }
                    .no-content {
                        color: #7f8c8d;
                        font-style: italic;
                        text-align: center;
                        padding: 20px;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1 class="title">${pageData.title}</h1>
                        <div class="meta">
                            📋 페이지 ID: ${pageData.page_id} | 
                            📅 수정일: ${pageData.modified_date || '정보 없음'} | 
                            <a href="${pageData.url || '#'}" target="_blank">🔗 원본 페이지 보기</a>
                        </div>
                    </div>
                    
                    <div class="content-area">
                        <div class="section">
                            <div class="section-title">📝 요약</div>
                            <div class="summary-text">${pageData.summary || '요약이 없습니다.'}</div>
                        </div>
                        
                        <div class="section">
                            <div class="section-title">🏷️ 키워드</div>
                            <div class="keywords-container">
                                ${pageData.keywords && pageData.keywords.length > 0 ? 
                                    pageData.keywords.map(keyword => 
                                        `<span class="keyword-tag">${keyword}</span>`
                                    ).join('') : 
                                    '<div class="no-content">키워드가 없습니다.</div>'
                                }
                            </div>
                        </div>
                        
                        <div class="section">
                            <div class="section-title">📄 페이지 내용</div>
                            <div class="content-text">${pageData.content || '페이지 내용이 없습니다.'}</div>
                        </div>
                    </div>
                </div>
            </body>
            </html>
        `;
        
        newWindow.document.write(content);
        newWindow.document.close();
        newWindow.focus();
        
        console.log('✅ 페이지 모달 표시 완료');
        
    } catch (error) {
        console.error('❌ 페이지 내용 로드 오류:', error);
        alert(`페이지 내용을 불러오는 중 오류가 발생했습니다: ${error.message}`);
    }
};

// DOM 로드 시 초기화
document.addEventListener('DOMContentLoaded', () => {
    console.log('📋 DOM 로드 완료');
    
    try {
        // URL 파라미터 확인
        const urlParams = new URLSearchParams(window.location.search);
        const mode = urlParams.get('mode');
        const keyword = urlParams.get('keyword');
        const parentId = urlParams.get('parent_id');
        
        console.log('🔍 URL 파라미터:');
        console.log('  mode:', mode);
        console.log('  keyword:', keyword);
        console.log('  parent_id:', parentId);
        
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
        // 3. 특정 페이지 모드 처리 (parent_id가 있는 경우)
        else if (parentId) {
            console.log('📄 특정 페이지 모드 감지, 로드 시작:', parentId);
            // 특정 페이지 모드에서는 키워드 마인드맵 버튼 표시
            if (keywordMindmapBtn) keywordMindmapBtn.style.display = 'inline-block';
            if (allMindmapBtn) allMindmapBtn.style.display = 'none';
            loadSpecificMindmap(parentId);
        } 
        // 4. 모든 조건에 해당하지 않는 경우
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

console.log('🔗 mindmap_simple.js 로드 완료');