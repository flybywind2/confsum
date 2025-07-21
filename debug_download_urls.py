"""
Confluence 다운로드 URL 테스트
"""
import requests
from confluence_api import ConfluenceClient

def test_download_urls():
    try:
        client = ConfluenceClient(
            base_url='http://localhost:8090',
            username='',
            password=''
        )
        
        page_id = '6455299'
        attachment_id = '6455300'
        filename = 'image-2025-7-22_6-57-40.png'
        
        # 가능한 다운로드 URL들 테스트
        test_urls = [
            f"http://localhost:8090/rest/api/content/{attachment_id}/download",
            f"http://localhost:8090/download/attachments/{page_id}/{filename}",
            f"http://localhost:8090/download/attachments/{page_id}/{filename}?api=v2",
            f"http://localhost:8090/rest/api/content/{page_id}/child/attachment/{attachment_id}/download",
        ]
        
        session = requests.Session()
        session.auth = (client.username, client.password)
        
        for i, url in enumerate(test_urls, 1):
            print(f'\n=== URL {i} 테스트 ===')
            print(f'URL: {url}')
            
            try:
                response = session.get(url, timeout=10)
                print(f'상태코드: {response.status_code}')
                print(f'Content-Type: {response.headers.get("content-type")}')
                
                if response.status_code == 200:
                    content = response.content
                    print(f'파일 크기: {len(content)} bytes')
                    
                    # PNG 시그니처 확인
                    if content[:4] == b'\x89PNG':
                        print('✅ 올바른 PNG 파일!')
                        
                        # 파일로 저장해보기
                        with open(f'test_download_{i}.png', 'wb') as f:
                            f.write(content)
                        print(f'파일이 test_download_{i}.png로 저장되었습니다')
                        
                        return url  # 성공한 URL 반환
                    else:
                        print(f'파일 헤더: {content[:10].hex()}')
                        print('내용 미리보기:', content[:200])
                else:
                    print(f'응답 내용: {response.text[:200]}')
                    
            except Exception as e:
                print(f'오류: {e}')
        
        print('\n❌ 모든 다운로드 URL이 실패했습니다')
        return None
        
    except Exception as e:
        print(f'전체 오류: {e}')
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    successful_url = test_download_urls()
    if successful_url:
        print(f'\n🎉 성공한 다운로드 URL: {successful_url}')
    else:
        print('\n💡 Confluence 서버 설정을 확인해보세요')