"""
테이블 변환기 테스트 스크립트
다양한 테이블 형태에 대한 변환 결과를 확인
"""

from table_to_text_converter import table_converter

def test_key_value_table():
    """키-값 테이블 테스트"""
    html = """
    <table>
        <tr><td>이름</td><td>홍길동</td></tr>
        <tr><td>나이</td><td>30세</td></tr>
        <tr><td>직업</td><td>개발자</td></tr>
    </table>
    """
    
    result = table_converter.convert_table_to_text(html)
    print("=== 키-값 테이블 테스트 ===")
    print(result)
    print()

def test_data_table():
    """데이터 테이블 테스트"""
    html = """
    <table>
        <caption>직원 정보 테이블</caption>
        <tr>
            <th>이름</th>
            <th>부서</th>
            <th>급여</th>
        </tr>
        <tr>
            <td>김철수</td>
            <td>개발팀</td>
            <td>5000만원</td>
        </tr>
        <tr>
            <td>이영희</td>
            <td>마케팅팀</td>
            <td>4500만원</td>
        </tr>
        <tr>
            <td>박민수</td>
            <td>영업팀</td>
            <td>4800만원</td>
        </tr>
    </table>
    """
    
    result = table_converter.convert_table_to_text(html)
    print("=== 데이터 테이블 테스트 ===")
    print(result)
    print()

def test_complex_table():
    """복잡한 테이블 테스트 (병합된 셀)"""
    html = """
    <table>
        <tr>
            <th rowspan="2">항목</th>
            <th colspan="2">2023년</th>
            <th colspan="2">2024년</th>
        </tr>
        <tr>
            <th>1분기</th>
            <th>2분기</th>
            <th>1분기</th>
            <th>2분기</th>
        </tr>
        <tr>
            <td>매출</td>
            <td>100억</td>
            <td>120억</td>
            <td>130억</td>
            <td>140억</td>
        </tr>
        <tr>
            <td>순이익</td>
            <td>10억</td>
            <td>15억</td>
            <td>18억</td>
            <td>20억</td>
        </tr>
    </table>
    """
    
    result = table_converter.convert_table_to_text(html)
    print("=== 복잡한 테이블 테스트 ===")
    print(result)
    print()

def test_layout_table():
    """레이아웃 테이블 테스트"""
    html = """
    <table>
        <tr>
            <td>좌측 메뉴</td>
            <td></td>
            <td>메인 콘텐츠 영역입니다</td>
        </tr>
        <tr>
            <td></td>
            <td></td>
            <td>추가 정보가 여기 있습니다</td>
        </tr>
        <tr>
            <td colspan="3">하단 푸터</td>
        </tr>
    </table>
    """
    
    result = table_converter.convert_table_to_text(html)
    print("=== 레이아웃 테이블 테스트 ===")
    print(result)
    print()

def test_fallback_conversion():
    """Beautiful Soup 없이 폴백 변환 테스트"""
    html = """
    <table>
        <tr><th>제목1</th><th>제목2</th></tr>
        <tr><td>데이터1</td><td>데이터2</td></tr>
    </table>
    """
    
    result = table_converter._fallback_table_conversion(html)
    print("=== 폴백 변환 테스트 ===")
    print(result)
    print()

if __name__ == "__main__":
    print("테이블 변환기 테스트 시작\n")
    
    try:
        test_key_value_table()
        test_data_table()
        test_complex_table()
        test_layout_table()
        test_fallback_conversion()
        
        print("모든 테스트 완료!")
        
    except Exception as e:
        print(f"테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()