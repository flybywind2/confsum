"""
Confluence 첨부파일 다운로드 디버깅
"""
from confluence_api import ConfluenceClient

def debug_attachment_download():
    try:
        client = ConfluenceClient(
            base_url='http://localhost:8090',
            username='kyusik.jeong',
            password='ekskrk!2'
        )
        
        page_id = '6455299'
        filename = 'image-2025-7-22_6-57-40.png'
        
        print(f'페이지 ID: {page_id}')
        print(f'파일명: {filename}')
        
        # 첨부파일 목록 조회
        print('\n=== 첨부파일 목록 조회 ===')
        attachments = client.get_page_attachments(page_id)
        print(f'첨부파일 개수: {len(attachments)}')
        
        for i, attachment in enumerate(attachments):
            print(f'첨부파일 {i+1}:')
            print(f'  ID: {attachment.get("id")}')
            print(f'  제목: {attachment.get("title")}')
            print(f'  타입: {attachment.get("type")}')
            print(f'  미디어타입: {attachment.get("extensions", {}).get("mediaType")}')
            print(f'  파일크기: {attachment.get("extensions", {}).get("fileSize")}')
            print(f'  다운로드 링크: {attachment.get("_links", {}).get("download")}')
            print()
        
        # 특정 파일 정보 조회
        print(f'\n=== 파일 {filename} 정보 조회 ===')
        file_info = client.get_attachment_info(page_id, filename)
        if file_info:
            print('파일 정보:')
            for key, value in file_info.items():
                print(f'  {key}: {value}')
        else:
            print('파일을 찾을 수 없음')
        
        # 첨부파일 다운로드 시도
        print(f'\n=== 파일 {filename} 다운로드 시도 ===')
        file_data = client.download_attachment(page_id, filename)
        
        if file_data:
            print(f'다운로드 성공: {len(file_data)} bytes')
            
            # 파일 헤더 확인 (PNG 시그니처 확인)
            if file_data[:4] == b'\x89PNG':
                print('올바른 PNG 파일입니다')
            else:
                print(f'파일 헤더: {file_data[:10].hex()}')
        else:
            print('다운로드 실패')
            
    except Exception as e:
        print(f'오류: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_attachment_download()