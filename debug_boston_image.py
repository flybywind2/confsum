"""
Boston image 페이지 디버깅
"""
import requests
import re
from confluence_api import ConfluenceClient
from enhanced_content_processor import process_page_content

def debug_boston_image_page():
    try:
        # Confluence 클라이언트로 페이지 내용 가져오기
        client = ConfluenceClient(
            base_url='http://localhost:8090',
            username='',
            password=''
        )
        
        page_data = client.get_page_content('6455299')
        
        if not page_data:
            print('페이지 데이터를 가져올 수 없음')
            return
        
        print(f'페이지 제목: {page_data.get("title")}')
        print(f'페이지 ID: {page_data.get("id")}')
        
        content = page_data.get('body', {}).get('storage', {}).get('value', '')
        print(f'콘텐츠 길이: {len(content)}')
        
        # 이미지 포함 여부 확인
        print('\n=== 이미지 태그 검사 ===')
        
        # 기본 img 태그
        img_tags = re.findall(r'<img[^>]*>', content, re.IGNORECASE)
        print(f'기본 img 태그 개수: {len(img_tags)}')
        
        for i, tag in enumerate(img_tags[:3]):  # 처음 3개만 출력
            print(f'img 태그 {i+1}: {tag}')
        
        # Confluence ac:image 태그
        ac_image_tags = re.findall(r'<ac:image[^>]*>.*?</ac:image>', content, re.DOTALL | re.IGNORECASE)
        print(f'Confluence ac:image 태그 개수: {len(ac_image_tags)}')
        
        for i, tag in enumerate(ac_image_tags[:2]):
            print(f'ac:image 태그 {i+1}: {tag[:200]}...')
        
        # Confluence ri:attachment 태그
        ri_attachment_tags = re.findall(r'<ri:attachment[^>]*>', content, re.IGNORECASE)
        print(f'Confluence ri:attachment 태그 개수: {len(ri_attachment_tags)}')
        
        for i, tag in enumerate(ri_attachment_tags[:2]):
            print(f'ri:attachment 태그 {i+1}: {tag}')
        
        # 'image' 단어 포함 여부
        image_mentions = content.lower().count('image')
        print(f'"image" 단어 출현 횟수: {image_mentions}')
        
        # 콘텐츠 미리보기
        print(f'\n=== 콘텐츠 미리보기 (첫 800자) ===')
        print(content[:800])
        
        # Enhanced content processor로 처리 테스트
        if '<img' in content or 'image' in content.lower() or '<ac:image' in content:
            print('\n=== Enhanced Content Processor 테스트 ===')
            
            try:
                result = process_page_content(content, page_data.get('title', ''), 'http://localhost:8090', '6455299')
                
                print(f'이미지 개수: {result.image_count}')
                print(f'테이블 개수: {result.table_count}')
                print(f'처리 노트: {result.processing_notes}')
                
                if result.extracted_images:
                    print(f'\n추출된 이미지 정보:')
                    for i, img_data in enumerate(result.extracted_images):
                        print(f'이미지 {i+1}:')
                        print(f'  포맷: {img_data.format.value}')
                        print(f'  크기: {len(img_data.data)} bytes')
                        print(f'  Alt 텍스트: {img_data.alt_text}')
                        print(f'  제목: {img_data.title}')
                        print(f'  소스 URL: {img_data.source_url}')
                
                if result.image_descriptions:
                    print('\n이미지 분석 결과:')
                    for i, desc in enumerate(result.image_descriptions):
                        print(f'이미지 {i+1}: {desc}')
                
                print(f'\n향상된 콘텐츠 길이: {len(result.enhanced_content)}')
                
                if result.enhanced_content != content:
                    print('\n=== 향상된 콘텐츠 변경사항 ===')
                    if len(result.enhanced_content) != len(content):
                        print(f'길이 변화: {len(content)} → {len(result.enhanced_content)}')
                    
                    # 변경된 부분 찾기
                    if '[이미지 분석 결과]' in result.enhanced_content:
                        print('이미지가 텍스트로 변환되었습니다!')
                
            except Exception as e:
                print(f'Enhanced Content Processor 오류: {e}')
                import traceback
                traceback.print_exc()
        else:
            print('\n이미지 관련 태그를 찾을 수 없습니다.')
        
    except Exception as e:
        print(f'전체 오류: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_boston_image_page()