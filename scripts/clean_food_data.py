import pandas as pd
import os

# 제거할 쓰레기 데이터 리스트
GARBAGE_FOOD_NAMES = [
    "바베큐풀드포크파스타샐러드",
    "풀만식빵", 
    "풀드포크바비큐피자",
    "BBQ풀드포크버거",
    "당고풀세트",
    "풀리스트",
    "파인풀업",
    "원더풀 배도수 젤리",
    "백합막장용메주가루",
    "돈까스클럽빵가루",
    "중식한상)한상가득도시락",
    "전립분용밀가루C",
    "닭가슴살두부김밥",
    "닭가슴살스팸김밥",
    "급색대가정석김밥",
    "죽선가 색죽시공 그린",
    "돈가스정식도시락",
    "홈술가번데기떡볶이",
    "제철나물비빔밥",
    "다섯가지나물밥&한돈떡갈비",
    "유기농듀럼밀세몰리나링귀네",
    "카라논나링귀니",
    "[3구]황태채강정",
    "맛깔나는먹거리고기순대",
    "시나몬러스크",
    "개나리콘",
    "퓨어잇떡뻥바나나쌀과자",
    "라쿠치나 소프트 바게트",
    "맛이차이나짜장면",
    "비건 모둠나물",
    "곤드레나물밥&마늘맛닭가슴살",
    "곤드레나물솥밥",
    "진짜진짜많구나도시락",
    "화이트비엔나",
    # 추가 쓰레기 데이터
    "청록미나리 생칼국수",
    "클라우드나인",
    "튀겨나온 곰돌이 돈까스",
    "산채나물비빔밥세트",
    "가지나물",
    "무나물",
    "이터나8",
    "한방수랏간 맛낭옥 인삼딸기",
    "라이비엔나",
    "시나몬말이야",
    "나가사키카스테라(상온)",
    "과일나박물김치",
    "옥천푸드 명이나물장아찌",
    "포천 방축리 맛나 내장",
    "요플레떠먹는키즈바나나",
    "덴마크시나몬초코우유",
    "메로나 보틀",
    "연세대학교바나나퐁당",
    "바나나는 원래 하얗다",
    "가마솥방식으로지은곤드레나물밥",
    "다섯가지 나물밥",
    "참나물페트소파스타",
    "맞깔나는먹거리찰순대",
    "한입 미니도나스",
    "바나나떡",
    "미드나잇 다크 콜드브루"
]

def clean_food_data():
    # 원본 CSV 파일 읽기
    df = pd.read_csv('food_clean_data.csv')
    print(f"원본 데이터: {len(df)}개 행")
    
    # 쓰레기 데이터 제거 전 상태 확인
    garbage_count = 0
    for garbage_name in GARBAGE_FOOD_NAMES:
        count = df[df['food_name'].str.contains(garbage_name, na=False, regex=False)].shape[0]
        if count > 0:
            print(f"제거할 데이터 '{garbage_name}': {count}개")
            garbage_count += count
    
    # 쓰레기 데이터 제거
    for garbage_name in GARBAGE_FOOD_NAMES:
        df = df[~df['food_name'].str.contains(garbage_name, na=False, regex=False)]
    
    print(f"제거된 데이터: {garbage_count}개")
    print(f"정리된 데이터: {len(df)}개 행")
    
    # 새 파일로 저장
    df.to_csv('food_clean_data_optimized.csv', index=False)
    print("최적화된 파일 'food_clean_data_optimized.csv' 생성 완료")

if __name__ == "__main__":
    clean_food_data()