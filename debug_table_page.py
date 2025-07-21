"""
테이블 페이지 디버깅 스크립트
"""
import requests
import json
import re
from table_to_text_converter import convert_table_html_to_text

def debug_page():
    try:
        # 해당 페이지 데이터 조회
        response = requests.get('http://localhost:8090/api/pages/6258694')
        if response.status_code != 200:
            print(f'페이지 조회 실패: {response.status_code}')
            print(f'응답 내용: {response.text[:500]}')
            return
        
        print(f'응답 상태: {response.status_code}')
        print(f'응답 길이: {len(response.text)}')
        print(f'응답 미리보기: {response.text[:200]}')
        
        try:
            page_data = response.json()
        except json.JSONDecodeError as e:
            print(f'JSON 파싱 오류: {e}')
            print(f'응답 전체 내용: {response.text}')
            return
        print(f'페이지 제목: {page_data.get("title")}')
        
        content = page_data.get('content', '')
        print(f'콘텐츠 길이: {len(content)}')
        
        # 테이블 포함 여부 확인
        if '<table' in content:
            table_count = content.count('<table')
            print(f'테이블 개수: {table_count}')
            
            # 모든 테이블 추출
            tables = re.findall(r'<table[^>]*>.*?</table>', content, re.DOTALL | re.IGNORECASE)
            print(f'추출된 테이블 개수: {len(tables)}')
            
            for i, table in enumerate(tables):
                print(f'\n=== 테이블 {i+1} ===')
                print(f'테이블 HTML 길이: {len(table)}')
                print(f'테이블 HTML 미리보기: {table[:300]}...')
                
                # 테이블 변환 테스트
                print('\n변환된 텍스트:')
                converted_text = convert_table_html_to_text(table)
                print(converted_text)
                print('-' * 50)
        else:
            print('테이블이 포함되지 않음')
            # HTML 태그 확인
            html_tags = re.findall(r'<[^>]+>', content)
            unique_tags = set(tag.split()[0].strip('<>') for tag in html_tags)
            print(f'포함된 HTML 태그들: {list(unique_tags)[:10]}')
        
    except Exception as e:
        print(f'오류 발생: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_page()