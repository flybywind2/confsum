// 🚨 mindmap.js 파일 로드 확인
console.log('🟢 mindmap.js 파일이 로드되었습니다!');
console.log('🌍 현재 페이지 URL:', window.location.href);

class MindmapVisualization {
    constructor() {
        console.log('🏗️ MindmapVisualization 생성자 호출됨');
        this.svg = null;
        this.simulation = null;
        this.nodes = [];
        this.links = [];
        this.parentId = null;
        this.threshold = 0.2;
        this.tooltip = d3.select("#tooltip");
        
        console.log('🚀 MindmapVisualization 초기화 시작');
        this.init();
    }
    
    init() {
        this.setupSVG();
        this.bindEvents();
        this.loadData();
    }
    
    setupSVG() {
        const container = document.querySelector('.mindmap-container');
        const width = container.clientWidth;
        const height = container.clientHeight;
        
        this.svg = d3.select("#mindmapSvg")
            .attr("width", width)
            .attr("height", height);
        
        // 줌 기능 추가
        const zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on("zoom", (event) => {
                this.svg.select(".main-group").attr("transform", event.transform);
            });
        
        this.svg.call(zoom);
        
        // 메인 그룹 추가
        this.svg.append("g").attr("class", "main-group");
    }
    
    bindEvents() {
        // 임계값 슬라이더
        const thresholdSlider = document.getElementById('thresholdSlider');
        const thresholdValue = document.getElementById('thresholdValue');
        
        thresholdSlider.addEventListener('input', (e) => {
            this.threshold = parseFloat(e.target.value);
            thresholdValue.textContent = this.threshold;
            this.updateVisualization();
        });
        
        // 키워드 필터
        const keywordFilter = document.getElementById('keywordFilter');
        keywordFilter.addEventListener('input', (e) => {
            this.filterByKeyword(e.target.value);
        });
        
        // 뷰 리셋
        document.getElementById('resetView').addEventListener('click', () => {
            this.resetView();
        });
    }
    
    async loadData() {
        console.log('🚀 loadData 함수 시작');
        
        // URL 파라미터 파싱
        const urlParams = new URLSearchParams(window.location.search);
        const mode = urlParams.get('mode');
        const keyword = urlParams.get('keyword');
        this.parentId = urlParams.get('parent_id');
        
        console.log('🔗 URL 정보:');
        console.log('  전체 URL:', window.location.href);
        console.log('  search:', window.location.search);
        console.log('  mode:', mode);
        console.log('  keyword:', keyword);
        console.log('  parent_id:', this.parentId);
        
        // 1. 키워드 모드 처리 (최우선)
        if (keyword && mode === 'keyword') {
            console.log('🎯 키워드 모드 실행:', keyword);
            await this.loadKeywordMindmap(keyword);
            return;
        }
        
        // 2. 전체 모드 처리
        if (mode === 'all') {
            console.log('🌐 전체 모드 실행');
            await this.loadAllMindmap();
            return;
        }
        
        // 3. 특정 페이지 모드 처리
        if (this.parentId) {
            console.log('📄 특정 페이지 모드 실행:', this.parentId);
            await this.loadSpecificMindmap();
            return;
        }
        
        // 4. 모든 조건에 해당하지 않는 경우
        console.log('❌ 모든 모드 조건에 해당하지 않음');
        this.showError('부모 페이지 ID가 지정되지 않았습니다. 홈페이지에서 마인드맵 버튼을 사용해주세요.');
        
        const errorContainer = this.svg.node().parentElement;
        errorContainer.innerHTML += `
            <div style="text-align: center; margin-top: 20px;">
                <a href="/" class="btn btn-primary">홈페이지로 이동</a>
                <a href="/data" class="btn btn-info">데이터 조회 페이지로 이동</a>
            </div>
        `;
    }
    
    async loadKeywordMindmap(keyword) {
        console.log(`🔍 키워드 마인드맵 로드 시작: "${keyword}"`);
        try {
            const apiUrl = `/mindmap-keyword?keyword=${encodeURIComponent(keyword)}&threshold=${this.threshold}`;
            console.log(`🌐 API 요청: ${apiUrl}`);
            
            const response = await fetch(apiUrl);
            console.log(`📡 응답: ${response.status} ${response.statusText}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log(`📊 데이터 수신: 노드 ${data.nodes?.length || 0}개, 링크 ${data.links?.length || 0}개`);
            
            this.nodes = data.nodes || [];
            this.links = data.links || [];
            
            if (this.nodes.length === 0) {
                this.showError(`키워드 '${keyword}'와 관련된 페이지가 없습니다.`);
                return;
            }
            
            // 제목 업데이트
            document.querySelector('h1').textContent = `키워드 '${keyword}' 마인드맵`;
            document.querySelector('#subtitle').textContent = `'${keyword}' 키워드를 포함한 ${this.nodes.length}개 페이지의 관계 시각화`;
            
            this.createVisualization();
            console.log(`✅ 키워드 마인드맵 로드 완료`);
            
        } catch (error) {
            console.error(`❌ 키워드 마인드맵 로드 실패:`, error);
            this.showError(`키워드 마인드맵 로드 실패: ${error.message}`);
        }
    }
    
    async loadAllMindmap() {
        console.log('🌐 전체 마인드맵 로드 시작');
        try {
            const response = await fetch(`/mindmap-all?threshold=${this.threshold}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            this.nodes = data.nodes;
            this.links = data.links;
            
            if (this.nodes.length === 0) {
                this.showError('저장된 페이지가 없습니다. 먼저 Confluence 페이지를 처리해주세요.');
                return;
            }
            
            document.querySelector('h1').textContent = '전체 페이지 마인드맵';
            document.querySelector('#subtitle').textContent = `총 ${this.nodes.length}개 페이지의 키워드 관계 시각화`;
            
            this.createVisualization();
            
        } catch (error) {
            this.showError(`전체 마인드맵 로드 실패: ${error.message}`);
        }
    }
    
    async loadSpecificMindmap() {
        console.log(`📄 특정 페이지 마인드맵 로드 시작: ${this.parentId}`);
        try {
            const response = await fetch(`/mindmap/${this.parentId}?threshold=${this.threshold}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            this.nodes = data.nodes;
            this.links = data.links;
            
            const centerNode = this.nodes.find(n => n.id === data.center_node);
            if (centerNode) {
                document.querySelector('h1').textContent = `${centerNode.title} - 마인드맵`;
                document.querySelector('#subtitle').textContent = `${this.nodes.length}개 페이지의 키워드 관계 시각화`;
            }
            
            this.createVisualization();
            
        } catch (error) {
            this.showError(`데이터 로드 실패: ${error.message}`);
        }
    }
    
    createVisualization() {
        const width = this.svg.attr("width");
        const height = this.svg.attr("height");
        
        // 임계값에 따라 링크 필터링
        const filteredLinks = this.links.filter(link => link.weight >= this.threshold);
        console.log(`초기 생성 - 전체 링크: ${this.links.length}, 필터된 링크: ${filteredLinks.length}`);
        
        // 시뮬레이션 설정
        this.simulation = d3.forceSimulation(this.nodes)
            .force("link", d3.forceLink(filteredLinks).id(d => d.id).distance(d => {
                const distance = 100 / (d.weight + 0.1);
                return Math.min(Math.max(distance, 50), 200);
            }))
            .force("charge", d3.forceManyBody().strength(-300))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collision", d3.forceCollide().radius(d => d.size + 10));
        
        const mainGroup = this.svg.select(".main-group");
        
        // 링크 생성 (필터된 링크 사용)
        const linkGroup = mainGroup.append("g").attr("class", "links");
        const link = linkGroup.selectAll(".link")
            .data(filteredLinks)
            .enter().append("line")
            .attr("class", "link")
            .attr("stroke-width", d => Math.sqrt(d.weight) * 3)
            .attr("stroke", d => this.getLinkColor(d.weight));
        
        // 노드 생성
        const nodeGroup = mainGroup.append("g").attr("class", "nodes");
        const node = nodeGroup.selectAll(".node")
            .data(this.nodes)
            .enter().append("g")
            .attr("class", "node")
            .call(this.drag());
        
        // 노드 원
        node.append("circle")
            .attr("r", d => d.size)
            .attr("fill", d => this.getNodeColor(d))
            .attr("stroke", d => d.id === this.parentId ? "#ff6b6b" : "#333")
            .attr("stroke-width", d => d.id === this.parentId ? 4 : 2);
        
        // 노드 텍스트
        node.append("text")
            .attr("dy", ".35em")
            .text(d => this.truncateText(d.title, 12))
            .attr("font-size", d => Math.min(d.size / 2, 12))
            .attr("fill", "white")
            .attr("text-anchor", "middle");
        
        // 이벤트 리스너
        node.on("mouseover", (event, d) => this.showTooltip(event, d))
            .on("mouseout", () => this.hideTooltip())
            .on("click", (event, d) => this.selectNode(d));
        
        // 시뮬레이션 업데이트
        this.simulation.on("tick", () => {
            link.attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);
            
            node.attr("transform", d => `translate(${d.x},${d.y})`);
        });
    }
    
    drag() {
        return d3.drag()
            .on("start", (event, d) => {
                if (!event.active) this.simulation.alphaTarget(0.3).restart();
                d.fx = d.x;
                d.fy = d.y;
            })
            .on("drag", (event, d) => {
                d.fx = event.x;
                d.fy = event.y;
            })
            .on("end", (event, d) => {
                if (!event.active) this.simulation.alphaTarget(0);
                d.fx = null;
                d.fy = null;
            });
    }
    
    getNodeColor(node) {
        if (node.id === this.parentId) {
            return "#ff6b6b"; // 부모 노드
        }
        
        const colors = ["#4ecdc4", "#45b7d1", "#96ceb4", "#ffeaa7", "#dda0dd"];
        return colors[node.keywords.length % colors.length];
    }
    
    getLinkColor(weight) {
        const intensity = weight * 255;
        return `rgba(102, 102, 102, ${weight})`;
    }
    
    truncateText(text, maxLength) {
        return text.length > maxLength ? text.substring(0, maxLength) + "..." : text;
    }
    
    showTooltip(event, node) {
        const tooltip = this.tooltip;
        
        tooltip.html(`
            <strong>${node.title}</strong><br>
            <strong>키워드:</strong> ${node.keywords.join(", ")}<br>
            <strong>요약:</strong> ${node.summary || "요약 없음"}<br>
            <strong>URL:</strong> <a href="${node.url}" target="_blank">페이지 열기</a>
        `)
        .style("left", (event.pageX + 10) + "px")
        .style("top", (event.pageY - 10) + "px")
        .style("display", "block");
    }
    
    hideTooltip() {
        this.tooltip.style("display", "none");
    }
    
    selectNode(node) {
        const infoDiv = document.getElementById('selectedPageInfo');
        
        infoDiv.innerHTML = `
            <h4>${node.title}</h4>
            <p><strong>페이지 ID:</strong> ${node.id}</p>
            <p><strong>키워드:</strong> ${node.keywords.join(", ")}</p>
            <p><strong>요약:</strong> ${node.summary || "요약 없음"}</p>
            <p><strong>URL:</strong> <a href="${node.url}" target="_blank">${node.url}</a></p>
        `;
        
        // 선택된 노드 강조
        this.svg.selectAll(".node circle")
            .attr("stroke", d => d.id === node.id ? "#ff6b6b" : (d.id === this.parentId ? "#ff6b6b" : "#333"))
            .attr("stroke-width", d => d.id === node.id ? 4 : (d.id === this.parentId ? 4 : 2));
    }
    
    updateVisualization() {
        console.log(`임계값 업데이트: ${this.threshold}`);
        
        // 임계값에 따라 링크 필터링
        const filteredLinks = this.links.filter(link => link.weight >= this.threshold);
        console.log(`전체 링크: ${this.links.length}, 필터된 링크: ${filteredLinks.length}`);
        
        // 기존 링크 완전 제거
        this.svg.select(".links").selectAll(".link").remove();
        
        // 새로운 링크 생성
        const linkGroup = this.svg.select(".links");
        const link = linkGroup.selectAll(".link")
            .data(filteredLinks)
            .enter().append("line")
            .attr("class", "link")
            .attr("stroke-width", d => Math.sqrt(d.weight) * 3)
            .attr("stroke", d => this.getLinkColor(d.weight));
        
        // 시뮬레이션 force 업데이트
        this.simulation.force("link")
            .links(filteredLinks)
            .distance(d => {
                // 가중치가 높을수록 가까이, 낮을수록 멀리
                const distance = 100 / (d.weight + 0.1);
                return Math.min(Math.max(distance, 50), 200);
            });
        
        // 시뮬레이션 tick 이벤트 재등록
        this.simulation.on("tick", () => {
            link.attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);
            
            this.svg.selectAll(".node").attr("transform", d => `translate(${d.x},${d.y})`);
        });
        
        // 시뮬레이션 재시작 (더 강하게)
        this.simulation.alpha(0.8).alphaTarget(0.1).restart();
        
        // 잠시 후 alphaTarget을 0으로 되돌림
        setTimeout(() => {
            this.simulation.alphaTarget(0);
        }, 3000);
        
        console.log('시각화 업데이트 완료');
    }
    
    filterByKeyword(keyword) {
        if (!keyword) {
            this.svg.selectAll(".node").style("opacity", 1);
            this.svg.selectAll(".link").style("opacity", 1);
            return;
        }
        
        const filteredNodes = this.nodes.filter(node => 
            node.keywords.some(k => k.toLowerCase().includes(keyword.toLowerCase())) ||
            node.title.toLowerCase().includes(keyword.toLowerCase())
        );
        
        const filteredNodeIds = new Set(filteredNodes.map(n => n.id));
        
        // 노드 필터링
        this.svg.selectAll(".node")
            .style("opacity", d => filteredNodeIds.has(d.id) ? 1 : 0.2);
        
        // 링크 필터링
        this.svg.selectAll(".link")
            .style("opacity", d => 
                filteredNodeIds.has(d.source.id) && filteredNodeIds.has(d.target.id) ? 1 : 0.1
            );
    }
    
    resetView() {
        // 필터 초기화
        document.getElementById('keywordFilter').value = '';
        this.filterByKeyword('');
        
        // 줌 리셋
        this.svg.transition().duration(750).call(
            d3.zoom().transform,
            d3.zoomIdentity
        );
        
        // 시뮬레이션 재시작
        this.simulation.alpha(1).restart();
    }
    
    showError(message) {
        this.svg.append("text")
            .attr("x", this.svg.attr("width") / 2)
            .attr("y", this.svg.attr("height") / 2)
            .attr("text-anchor", "middle")
            .attr("font-size", "18px")
            .attr("fill", "#ff6b6b")
            .text(message);
    }
}

// 페이지 로드 시 초기화
console.log('🔗 DOMContentLoaded 이벤트 리스너 등록');
document.addEventListener('DOMContentLoaded', () => {
    console.log('📋 DOM 로드 완료, MindmapVisualization 생성 시작');
    try {
        const mindmap = new MindmapVisualization();
        console.log('✅ MindmapVisualization 생성 완료');
        window.mindmapVisualization = mindmap; // 디버깅용 전역 변수
    } catch (error) {
        console.error('❌ MindmapVisualization 생성 실패:', error);
        console.error('스택 트레이스:', error.stack);
    }
});

// 즉시 실행 테스트
console.log('🧪 즉시 실행 테스트 - D3.js 사용 가능?', typeof d3);
console.log('🧪 즉시 실행 테스트 - document 상태:', document.readyState);