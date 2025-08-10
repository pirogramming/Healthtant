from foods.models import Food

# 나트륨(mg)을 받아 소금(g)으로 변환하는 함수
def sodium_into_salt(sodium):
    return sodium*2.5/1000

#영양소 이름과 food를 입력하면 영양소 함량이 GOOD, NEUTRAL, BAD 인지, 그리고 낮음/적정/높음 인지 반환하는 함수
# *주의* 영양적인 관점에서 칼로리는 낮고 높은 기준을 명시하지 않는게 좋음!! 칼로리가 낮다고 좋은 음식인게 아니고 칼로리가 높다고 안 좋은 음식인게 아니기 때문!
# 따라서 칼로리에 대한 GOOD, BAD 문구는 출력하지 않는걸로 합시다!
def get_level(nutrient, food):

    #고형식과 음료의 FSA Front-of-Pack 기준이 다르기 때문에 cutoff를 분리해서 구현 
    cutoff = {
        "drink": {"sugar":[2.5, 11.25], "saturated_fatty_acids": [0.75, 1.5], "salt": [0.3, 0.75]},
        "solid": {"sugar":[5.0, 22.5], "saturated_fatty_acids": [1.5, 5.0], "salt": [0.3, 1.5]}
        }
    
    category = "drink" if getattr(food, "food_category") == "음료류" else "solid"

    if nutrient == "sugar":
        sugar = getattr(food, "sugar", 0)
        if sugar <= cutoff[category]["sugar"][0]: return {"level": "낮음", "class": "GOOD"}
        elif sugar <= cutoff[category]["sugar"][1]: return {"level": "적정", "class": "NEUTRAL"}
        else: return {"level": "높음", "class": "BAD"}
    
    if nutrient == "saturated_fatty_acids":
        saturated_fatty_acids = getattr(food, "saturated_fatty_acids", 0)
        if saturated_fatty_acids <= cutoff[category]["saturated_fatty_acids"][0]: return {"level": "낮음", "class": "GOOD"}
        elif saturated_fatty_acids <= cutoff[category]["saturated_fatty_acids"][1]: return {"level": "적정", "class": "NEUTRAL"}
        else: return {"level": "높음", "class": "BAD"}
    
    if nutrient == "salt":
        salt = sodium_into_salt(getattr(food, "salt", 0))
        if salt <= cutoff[category]["salt"][0]: return {"level": "낮음", "class": "GOOD"}
        elif salt <= cutoff[category]["salt"][1]: return {"level": "적정", "class": "NEUTRAL"}
        else: return {"level": "높음", "class": "BAD"}

    #단백질은 음료와 고형식 기준이 동일함
    if nutrient == "protein":
        protein = getattr(food, "protein", 0)
        calorie = getattr(food, "calorie") #칼로리는 0이 아님이 보장됨
        ratio = protein*4/getattr(food, "calorie") * 100
        if ratio < 12: return {"level": "낮음", "class": "BAD"}
        elif ratio < 20: return {"level": "적정", "class": "NEUTRAL"}
        else: return {"level": "높음", "class": "GOOD"}

    return {"level": "판정불가", "class": None}