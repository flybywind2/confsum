"""
이미지 to 텍스트 변환 기능 테스트
"""

from enhanced_content_processor import enhanced_processor
from llm_service import initialize_llm_service
from image_to_text_converter import ImageData, ImageFormat
import base64

def test_image_analysis():
    """이미지 분석 기능 테스트"""
    
    # 1x1 픽셀 빨간색 PNG 이미지 (테스트용)
    red_pixel_png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    
    try:
        # base64 데이터를 ImageData 객체로 변환
        image_bytes = base64.b64decode(red_pixel_png)
        
        test_image = ImageData(
            data=image_bytes,
            format=ImageFormat.PNG,
            alt_text="테스트 이미지",
            title="1x1 빨간색 픽셀",
            width=1,
            height=1
        )
        
        print("=== 이미지 to 텍스트 변환 테스트 ===")
        print(f"이미지 데이터 크기: {len(image_bytes)} bytes")
        print(f"이미지 포맷: {test_image.format.value}")
        print(f"Alt 텍스트: {test_image.alt_text}")
        
        # LLM 서비스 초기화
        llm_service = initialize_llm_service()
        print(f"사용 중인 LLM 서비스: {type(llm_service).__name__}")
        
        # 이미지 분석 실행
        print("\n이미지 분석 중...")
        description = llm_service.extract_image_text(test_image)
        
        print("\n=== 분석 결과 ===")
        print(description)
        
        return True
        
    except Exception as e:
        print(f"테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_full_pipeline():
    """전체 파이프라인 테스트 (HTML with 이미지)"""
    
    html_content = f'''
    <html>
    <head><title>테스트 문서</title></head>
    <body>
        <h1>이미지 분석 테스트</h1>
        <p>이 문서는 이미지 분석 기능을 테스트하기 위한 샘플입니다.</p>
        
        <h2>테스트 이미지</h2>
        <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==" alt="빨간색 점" title="1픽셀 빨간색 이미지" />
        
        <p>위 이미지는 테스트용 1x1 빨간색 픽셀입니다.</p>
        
        <h2>추가 정보</h2>
        <table>
            <tr><th>항목</th><th>값</th></tr>
            <tr><td>이미지 크기</td><td>1x1 픽셀</td></tr>
            <tr><td>색상</td><td>빨간색</td></tr>
        </table>
    </body>
    </html>
    '''
    
    try:
        print("\n=== 전체 파이프라인 테스트 ===")
        
        result = enhanced_processor.process_content(
            html_content, 
            "이미지 분석 테스트 문서"
        )
        
        print(f"원본 콘텐츠 길이: {len(result.original_content)} 문자")
        print(f"향상된 콘텐츠 길이: {len(result.enhanced_content)} 문자")
        print(f"추출된 이미지 수: {result.image_count}")
        print(f"변환된 테이블 수: {result.table_count}")
        print(f"처리 노트: {result.processing_notes}")
        
        print(f"\n=== 이미지 분석 결과 ===")
        for i, desc in enumerate(result.image_descriptions):
            print(f"이미지 {i+1}: {desc}")
        
        print(f"\n=== 향상된 콘텐츠 (첫 800자) ===")
        print(result.enhanced_content[:800])
        
        print(f"\n=== 처리 통계 ===")
        stats = enhanced_processor.get_processing_stats()
        for key, value in stats.items():
            print(f"{key}: {value}")
        
        return True
        
    except Exception as e:
        print(f"전체 파이프라인 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("이미지 to 텍스트 변환 기능 테스트 시작\n")
    
    # 개별 이미지 분석 테스트
    test1_success = test_image_analysis()
    
    # 전체 파이프라인 테스트
    test2_success = test_full_pipeline()
    
    print(f"\n=== 테스트 결과 ===")
    print(f"개별 이미지 분석: {'✅ 성공' if test1_success else '❌ 실패'}")
    print(f"전체 파이프라인: {'✅ 성공' if test2_success else '❌ 실패'}")
    
    if test1_success and test2_success:
        print("\n🎉 모든 테스트가 성공적으로 완료되었습니다!")
        print("\n이제 다음과 같은 기능들이 사용 가능합니다:")
        print("- HTML에서 이미지 자동 감지 및 추출")
        print("- Ollama 멀티모달 모델을 사용한 이미지 분석 (llama3.2-vision, llava 등)")
        print("- OpenAI GPT-4V를 사용한 이미지 분석 (base64 인코딩)")
        print("- 테이블과 이미지가 포함된 콘텐츠의 자동 텍스트 변환")
        print("- RAG 및 요약 생성에 최적화된 콘텐츠 처리")
    else:
        print("\n❌ 일부 테스트가 실패했습니다. 로그를 확인해주세요.")