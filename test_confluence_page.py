"""
Confluence 페이지에서 테이블 테스트
"""
import sys
sys.path.append('.')
from confluence_api import ConfluenceClient
from config import config
import re
from table_to_text_converter import convert_table_html_to_text

def test_confluence_page():
    try:
        # Confluence 클라이언트 생성 및 페이지 조회
        client = ConfluenceClient(
            base_url='http://localhost:8090',
            username='',
            password=''
        )
        page_data = client.get_page_content('6258694')
        
        if not page_data:
            print('페이지를 가져올 수 없음')
            return
        
        print(f'페이지 제목: {page_data.get("title", "제목 없음")}')
        print(f'페이지 ID: {page_data.get("id")}')
        
        content = page_data.get('body', {}).get('storage', {}).get('value', '')
        print(f'콘텐츠 길이: {len(content)}')
        
        # 테이블 확인
        if '<table' in content:
            table_count = content.count('<table')
            print(f'테이블 개수: {table_count}')
            
            # 정규식으로 테이블 추출
            tables = re.findall(r'<table[^>]*>.*?</table>', content, re.DOTALL | re.IGNORECASE)
            print(f'정규식으로 추출된 테이블 개수: {len(tables)}')
            
            for i, table in enumerate(tables):
                print(f'\n=== 테이블 {i+1} ===')
                print(f'테이블 HTML 길이: {len(table)}')
                print('테이블 HTML (첫 500자):')
                print(table[:500])
                print('\n변환된 텍스트:')
                try:
                    converted_text = convert_table_html_to_text(table)
                    print(converted_text)
                except Exception as e:
                    print(f'테이블 변환 오류: {e}')
                print('-' * 60)
        else:
            print('테이블이 포함되지 않음')
            # HTML 구조 확인
            if '<' in content:
                html_tags = re.findall(r'<[^>]+>', content)
                unique_tags = list(set(tag.split()[0].strip('<>/') for tag in html_tags if tag.strip('<>/'))[:15])
                print(f'포함된 HTML 태그들 (일부): {unique_tags}')
            else:
                print('HTML 태그가 없는 순수 텍스트')
            
    except Exception as e:
        print(f'오류 발생: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_confluence_page()